import logging
import re
import os
import json
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from chatbot.models import ChatRequest, Conversation, Contact, CacheResponse, \
    Content, ToolCall
from chatbot.crms.DoubleTick import DoubleTick
from chatbot.crms.ZohoBooking import ZohoBooking
from chatbot.OpenAIResponse import OpenAIResponse
from chatbot.SystemPrompt import get_model_instruction, lang_chain_tools
from chatbot.helper import fetch_history, convert_lead_to_DT
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from datetime import timedelta, date
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore
from django.conf import settings
from django.db import transaction
from django.db.models import Subquery
from django.utils import timezone
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, \
    ToolMessage


logger = logging.getLogger(__name__)

# Initialize embeddings and vector DB
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
module_dir = os.path.dirname(__file__)  # get current directory
vectordb = Chroma(
    persist_directory=module_dir + "/../../studio_db",
    embedding_function=embeddings
)
retriever = vectordb.as_retriever(search_kwargs={"k": 5})

# Initialize LLM
llm = ChatOpenAI(model="gpt-4o", temperature=0.7).bind_tools(lang_chain_tools)


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def split_into_messages(text, max_messages=3):
    # Remove any extra spaces or newlines
    text = text.strip()

    # First try to split by double newlines (paragraphs)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    if len(paragraphs) >= 2 and len(paragraphs) <= max_messages:
        return paragraphs

    # Next try to split by single newlines
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    if len(lines) >= 2 and len(lines) <= max_messages:
        return lines

    # Finally, split by sentences and group them
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # If we have very few sentences, just return them
    if len(sentences) <= max_messages:
        return sentences

    # Group sentences into 2-3 messages
    messages = []
    message_count = min(max_messages, 3)  # Max 3 messages
    sentences_per_message = len(sentences) // message_count

    for i in range(message_count):
        start_idx = i * sentences_per_message
        end_idx = start_idx + sentences_per_message if i < message_count - 1 \
            else len(sentences)
        message = " ".join(sentences[start_idx:end_idx])
        message = re.sub(r"\[.*?\]", "", message)
        messages.append(message)

    return messages


def save_to_db(contact, content, conversation_type):
    """Saves message to DB"""
    conversation = Conversation.objects.create(
        contact=contact,
        message=json.dumps(content),
        conversation_type=conversation_type
    )
    if conversation.conversation_type == "AI":
        for tool_call in content["tool_calls"]:
            ToolCall.objects.create(
                name=tool_call["name"],
                args=tool_call["args"],
                type=tool_call["type"],
                tool_id=tool_call["id"],
                conversation=conversation
            )
        if '"assigned": true' in conversation.message:
            ToolCall.objects.create(
                name="assign_agent",
                args="{}",
                type="ToolCall",
                tool_id="manual_call",
                conversation=conversation
            )
        Content.objects.create(
            type="AI",
            content=content["content"],
            conversation=conversation
        )
    elif conversation.conversation_type == "ToolCall":
        Content.objects.create(
            type="ToolCall",
            content=content["content"],
            conversation=conversation
        )
    else:
        for sub_content in content:
            Content.objects.create(
                type=sub_content["type"],
                content=sub_content["image_url"] if sub_content["type"]
                == "image_url" else sub_content["text"],
                conversation=conversation
            )


def send_to_phone(content, double_tick, phone):
    """Sends message to the provided phone number"""
    if content:
        for message in split_into_messages(content):
            double_tick.send_text_to_phone(message, phone)


def analyze_image(url):
    """For analyzing an image using the url provided"""
    return "Uploaded an image"


def get_relevant_docs(user_message):
    '''For getting relevant docs using user_message'''
    text_parts = [msg["text"] for msg in user_message if msg["type"] == "text"]
    image_urls = [msg["image_url"] for msg in user_message
                  if msg["type"] == "image_url"]

    user_message_text = " ".join(text_parts) if text_parts else ""
    docs = retriever.invoke(user_message_text) if user_message_text else []

    if image_urls:
        image_descriptions = [analyze_image(url) for url in image_urls]
        docs.extend(retriever.invoke(" ".join(image_descriptions)))
    return docs


def chat_request_prepare(chat_request, openAIResponse):
    """Prepares the chat request and creates a run."""
    try:
        # Prepare content (images + message)
        content = [
            {"type": "image_url", "image_url": {"url": url}}
            for url in chat_request["image_url"]
        ] + [{
            "type": "text",
            "text": "\n".join(chat_request["message"])
        }]
        model_conversations = fetch_history(
            chat_request["contact"],
            SystemMessage(
                content=get_model_instruction(
                    chat_request["contact"].full_name,
                    str(date.today())
                ) + format_docs(
                    retriever.invoke("")
                )
            )
        )
        save_to_db(chat_request["contact"], content, "Human")
        model_conversations.append(HumanMessage(content=content))

        double_tick = DoubleTick()

        # Get relevant documents
        docs = get_relevant_docs(content)
        context = format_docs(docs)
        # Inform the model about the context
        context_message = "Here's relevant information for the current" + \
            f"question: {context}"

        # Process with LLM
        model_conversations.append(SystemMessage(content=context_message))

        response = llm.invoke(model_conversations)
        model_conversations.pop()

        send_to_phone(
            response.content,
            double_tick,
            chat_request["contact"].phone
        )
        aIContent = {
            "content": response.content,
            "tool_calls": response.tool_calls
        }

        if "Let me pass you to the team" in aIContent["content"] and \
                len(response.tool_calls) == 0:
            model_conversations.append(SystemMessage(
                content="Need to call assign agent with appropriate params"
            ))
            response = llm.invoke(model_conversations)
            model_conversations.pop()
            aIContent = {
                "content": response.content,
                "tool_calls": response.tool_calls
            }

        # Append AI response to the conversation
        save_to_db(chat_request["contact"], aIContent, "AI")
        model_conversations.append(AIMessage(**(aIContent)))

        while response.tool_calls:
            tool_results = openAIResponse.handle_tool_calls(
                response.tool_calls, chat_request["request_object"]
            )
            model_conversations.extend([
                ToolMessage(**(tr))
                for tr in tool_results
            ])

            for tr in tool_results:
                save_to_db(chat_request["contact"], tr, "ToolCall")

            response = llm.invoke(model_conversations)
            send_to_phone(
                response.content,
                double_tick,
                chat_request["contact"].phone
            )
            aIContent = {
                "content": response.content,
                "tool_calls": response.tool_calls
            }
            save_to_db(chat_request["contact"], aIContent, "AI")
            model_conversations.append(AIMessage(**(aIContent)))
        # Update request status to completed
        ChatRequest.objects.filter(
            id__in=chat_request["requests"]).update(status="completed")
    except Exception as e:
        logger.error("Error: " + str(e))
        double_tick.send_text_to_phone(
            "I'm having trouble processing your request right now." +
            " Let me get that fixed!",
            chat_request["contact"].phone
        )
        ChatRequest.objects.filter(
            id__in=chat_request["requests"]
        ).update(status="error", error_message=str(e))


def clear_ready_chat_queue():
    '''Clears ready chat queue'''
    openAIResponse = OpenAIResponse()
    chat_requests = defaultdict(lambda: {
        "message": [],
        "image_url": [],
        "contact": None,
        "request_object": None,
        "requests": []
    })
    with transaction.atomic():
        chat_requests_queryset = (
            ChatRequest.objects.select_for_update()
            .filter(status='ready')
        )

        for req in chat_requests_queryset:
            chat = chat_requests[req.contact.id]

            if chat["request_object"] is None:
                chat["request_object"] = req
            if chat["contact"] is None:
                chat["contact"] = req.contact
            if req.message:
                chat["message"].append(req.message)
            if req.image_url:
                chat["image_url"].append(req.image_url)
            chat["requests"].append(req.id)
    with ThreadPoolExecutor(max_workers=4) as executor:
        for chat_data in chat_requests.values():
            executor.submit(
                chat_request_prepare,
                chat_data,
                openAIResponse
            )


def reply_to_user():
    '''Replies to user if they have not already'''
    current_time = timezone.now()
    time_threshold = current_time - timedelta(minutes=10)
    waiting_threshold = current_time - timedelta(minutes=5)
    excluded_contacts = ChatRequest.objects.filter(
        created_at__gt=waiting_threshold
    ).values('contact')
    crm = DoubleTick()
    contacts = Contact.objects.filter(
        chatrequest__created_at__lte=waiting_threshold,
        chatrequest__created_at__gte=time_threshold
    ).exclude(
        id__in=Subquery(excluded_contacts.values('id'))
    ).distinct()

    for contact in contacts:
        # crm_contact = crm.get_contact(contact.phone)
        # if contact.conversation_closed is False:
        # if crm_contact["customer"]["assignedToUser"] is None:
        #     crm.send_text_to_phone(
        #         "Are you still there?",
        #         contact.phone
        #     )
        # contact.conversation_closed = True
        # contact.save()
        convert_lead_to_DT(contact, crm, None, False)


def update_slots():
    crm = ZohoBooking()
    message = crm.get_available_day_slots(None, True)
    if "no slots available" not in message:
        CacheResponse.objects.update_or_create(
            type="get_available_day_slots",
            defaults={"message": message}
        )


class Command(BaseCommand):
    help = "Runs APScheduler."

    def handle(self, *args, **options):
        logger.info("Starting scheduler.")
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        if scheduler.get_job('clear_ready_chat_queue') is None:
            scheduler.add_job(
                clear_ready_chat_queue,
                trigger=CronTrigger(second="*/10"),  # Every 10 seconds
                id="clear_ready_chat_queue",
                max_instances=1,
                replace_existing=True,
            )
            logger.info(
                "Added clear_ready_chat_queue"
            )

        if scheduler.get_job('reply_to_user') is None:
            scheduler.add_job(
                reply_to_user,
                trigger=CronTrigger(minute="*/10"),  # Every 10 minutes
                id="reply_to_user",
                max_instances=1,
                replace_existing=True,
            )
            logger.info(
                "Added reply_to_user."
            )

        if scheduler.get_job('update_slots') is None:
            scheduler.add_job(
                update_slots,
                trigger=CronTrigger(hour="*"),  # Every 10 minutes
                id="update_slots",
                max_instances=1,
                replace_existing=True,
            )
            logger.info(
                "Added update_slots."
            )

        if not scheduler.running:
            try:
                logger.info("Starting scheduler...")
                scheduler.start()
            except KeyboardInterrupt:
                logger.info("Stopping scheduler...")
                scheduler.shutdown()
                logger.info("Scheduler shut down successfully!")
