import requests
import tempfile
import os
import re
import random
import datetime
import json
from time import sleep
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import authentication, permissions, generics, status
from rest_framework.response import Response
from openai import OpenAI
from .filters import ConversationFilter, ContactFilter
from .serializers import AIChat, ConversationSerializer, ContactModelSerializer
from .models import ChatRequest, Contact, Conversation, ToolCall, SkipMessage
from .crms.DoubleTick import DoubleTick


def download_file_to_temp(url):
    """Makes the request to get the file content and
    save to temporary file"""
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        # Create a temporary file

        temp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=".ogg"
        )
        # Write the content into the temporary file

        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)
        temp_file.close()  # Close the file so we can re-open if needed
        return temp_file.name  # Return the path to the temp file
    else:
        raise Exception(
            "Failed to download file, status code: " + response.status_code
        )


class MetricsView(generics.RetrieveAPIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        created_at_gte = request.GET.get("created_at_gte")
        created_at_lte = request.GET.get("created_at_lte")

        filters = {
            "created_at__gte": datetime.datetime.strptime(
                created_at_gte, "%Y-%m-%d")
            if created_at_gte else datetime.datetime(2021, 1, 1),
            "created_at__lte": datetime.datetime.strptime(
                created_at_lte, "%Y-%m-%d")
            if created_at_lte else datetime.datetime(2999, 1, 1),
        }
        total_chats = Conversation.objects.filter(
            conversation_type="Human",
            **filters
        ).count()

        tours_booked = ToolCall.objects.filter(
            name="create_appointment",
            conversation__created_at__gte=filters.get("created_at__gte", None),
            conversation__created_at__lte=filters.get("created_at__lte", None),
        ).count()

        chats_transferred = ToolCall.objects.filter(
            name__in=[
                "booking_with_agent",
                "assign_agent",
                "handle_junior_assessment"
            ],
            conversation__created_at__gte=filters.get("created_at__gte", None),
            conversation__created_at__lte=filters.get("created_at__lte", None),
        ).count()

        escalation_rate = chats_transferred / total_chats * 100 \
            if total_chats else 0
        resolution_rate = 100 - escalation_rate

        response = {
            "total_chats": total_chats,
            "tours_booked": tours_booked,
            "chats_transferred": chats_transferred,
            "resolution_rate": resolution_rate,
            "escalation_rate": escalation_rate,
        }
        return Response(response, status=status.HTTP_200_OK,)


class ConversationListView(generics.ListAPIView):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ConversationFilter
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['-created_at']


class ContactListView(generics.ListAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactModelSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ContactFilter
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()

        # Apply distinct to get unique contacts
        return queryset.distinct()


class AIChatView(generics.CreateAPIView):
    """Send text to Open AI Assistant to get response"""

    serializer_class = AIChat
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]

    double_tick = DoubleTick()

    def get_authenticators(self):
        # Change authentication class for specific method
        if self.request.method == "POST":
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if self.request.method == "POST":
            return []
        return super().get_permissions()

    def literal_search(self, text, word):
        pattern = r'\b' + re.escape(word) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))

    def save_conversation(self, text, image_url, contact, conversation_type):
        content = [{"type": "image_url", "image_url": {"url": image_url}}] \
            if image_url else []
        if text:
            content.append({"type": "text", "text": text})
        Conversation.objects.create(
            contact=contact,
            message=json.dumps(content),
            conversation_type=conversation_type
        )

    def post(self, request):
        """Creates a new thread if required and gets response of AI"""
        # Request.objects.create(params=str(request.data))
        # if not request.GET.get("dt_secret") == os.getenv("DT_SECRET"):
        #     return Response(
        #         "You are not authorized",
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        serializer = AIChat(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        validated_data = serializer.validated_data
        message, phone = (
            validated_data.get("message"),
            request.data.get("from"),
        )
        contact, _ = Contact.objects.get_or_create(phone=phone)
        double_tick_contact = self.double_tick.get_contact(
            phone=phone,
            delay=5
        )

        message_text = None
        image_url = None

        if message["type"] == "TEXT":
            message_text = message["text"]
        elif message["type"] == "BUTTON":
            message_text = message["text"]
        elif message["type"] == "AUDIO":
            try:
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                temp_file_path = download_file_to_temp(message["url"])
                with open(temp_file_path, "rb") as audio_file:
                    message_text = client.audio.translations.create(
                        model="whisper-1", file=audio_file
                    ).text
            except Exception as e:
                self.save_conversation(
                    "Error received on transcribing audio: " + str(e),
                    image_url,
                    contact,
                    "AUDIO_MSG_ERROR"
                )
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        elif message["type"] == "IMAGE":
            message_text = message["caption"] if "caption" in message else ""
            image_url = message["url"]

        if double_tick_contact and "customer" in double_tick_contact and \
                double_tick_contact["customer"]["assignedToUser"] is not None:
            self.save_conversation(message_text, image_url, contact, "Agent")
            return Response(
                "Already assigned to user",
                status=status.HTTP_200_OK
            )
        if "text" in message:
            skip_message = SkipMessage.objects.filter(text=message["text"])
            if skip_message:
                self.save_conversation(
                    message_text,
                    image_url,
                    contact,
                    "Skip_Message"
                )
                sleep(5)
                return Response(
                    "Skip message received",
                    status=status.HTTP_200_OK
                )
            for word in ["apc", "face card", "facecard"]:
                if self.literal_search(message["text"], word):
                    self.save_conversation(
                        message_text,
                        image_url,
                        contact,
                        "APC_FACE_CARD"
                    )
                    self.double_tick.assign_team_member(
                        contact,
                        random.choice(["971542172356", "971551330783"])
                    )
                    self.double_tick.send_text_to_phone(
                        "Let me pass you to the team",
                        contact.phone
                    )
                    return Response(
                        "APC or Face card received",
                        status=status.HTTP_200_OK
                    )
        customer_name = double_tick_contact["customer"]["name"] if \
            "error" not in double_tick_contact and not str(
            double_tick_contact["customer"]["name"]).isdigit() else None

        # if not contact.test_number:
        #     return Response({
        #         "msg": "Your are not allowed to send messages"
        #     }, status=status.HTTP_200_OK)

        if customer_name is not None and customer_name != contact.full_name:
            contact.full_name = customer_name
            contact.save()

        chat_request = ChatRequest.objects.create(
            message=message_text,
            image_url=image_url,
            contact=contact,
            status="ready"
        )
        chat_request.save()
        response_data = {"id": chat_request.id, "status": chat_request.status}
        return Response(response_data, status=status.HTTP_200_OK)
