import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, \
    ToolMessage
from chatbot.UserLead import UserLead, get_lead_prompt
from chatbot.models import Conversation

DT_CUSTOM_FIELDS = [
    {
        "name": "DT Lead",
        "value": "True"
    },
    {
        "name": "Club",
        "value": "StudioRepublik"
    },
    {
        "name": "Source",
        "value": "Unknown"
    },
    {
        "name": "Media",
        "value": "Organic"
    },
    {
        "name": "Contact method",
        "value": "WhatsApp"
    }
]


def clean_parsed_str(text):
    return re.sub(r"^[a-z]\)\s*", "", text)


def convert_lead_to_DT(recent_contact, crm, crm_contact=None,
                       dt_update=False):
    lead_llm = ChatOpenAI(
        model="gpt-4o",
    ).bind(response_format=UserLead)

    model_conversations = fetch_history(
        recent_contact,
        SystemMessage(
            content=get_lead_prompt()
        )
    )

    if isinstance(model_conversations[-1], AIMessage) and \
            hasattr(model_conversations[-1], "tool_calls"):
        model_conversations.pop()

    response = lead_llm.invoke(model_conversations)

    if hasattr(response, "additional_kwargs") and \
            "parsed" in response.additional_kwargs:
        user_lead = response.additional_kwargs["parsed"]
        recent_contact.lead_type = user_lead.lead_value
        recent_contact.lead_reason = user_lead.reason
        recent_contact.reason_of_approach = user_lead.reason_of_approach

        if dt_update:
            if crm_contact is None:
                crm_contact = crm.get_contact(recent_contact.phone)
            custom_fields = DT_CUSTOM_FIELDS + [
                {"name": "AI Summary", "value": user_lead.lead_value},
                {"name": "AI Analysis", "value": user_lead.reason},
                {
                    "name": "Reason of Approach",
                    "value": user_lead.reason_of_approach
                }
            ]
            if recent_contact.lead_type == "Hot Lead":
                custom_fields.append({
                    "name": "Lead Stages",
                    "value": "New"
                })
            crm.update_contact(
                recent_contact.phone,
                crm_contact["customer"]["name"],
                custom_fields
            )
        recent_contact.save()


def fetch_history(contact, system_message):
    # Fetch conversation history
    conversations = Conversation.objects.filter(
        contact=contact,
        conversation_type__in=["Human", "AI", "ToolCall"]
    )

    # Build conversation history for the LLM
    model_conversations = [system_message]

    for c in conversations:
        msg_content = json.loads(c.message)
        msg_class = {"AI": AIMessage, "ToolCall": ToolMessage}.get(
            c.conversation_type, HumanMessage)
        model_conversations.append(
            msg_class(content=msg_content)
            if msg_class == HumanMessage
            else msg_class(**msg_content)
        )
    return model_conversations
