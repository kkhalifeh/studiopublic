from rest_framework import serializers
from chatbot.models import ToolCall, Content, Conversation, Contact


# Contacts Serializer
class NameSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_null=True)
    last_name = serializers.CharField(required=False, allow_null=True)
    formatted_name = serializers.CharField()


# Phone Serializer
class PhoneSerializer(serializers.Serializer):
    phone = serializers.CharField()
    type = serializers.CharField()
    waId = serializers.CharField()


# Contact Serializer
class ContactSerializer(serializers.Serializer):
    name = serializers.CharField()


# Contacts Serializer
class ContactsSerializer(serializers.Serializer):
    name = NameSerializer(required=False, allow_null=True)
    phones = PhoneSerializer(many=True, required=False, allow_null=True)


# Context Serializer
class ContextSerializer(serializers.Serializer):
    id = serializers.CharField(required=False, allow_null=True)
    from_ = serializers.CharField(source="from",
                                  required=False,
                                  allow_null=True)


# TemplateMessageHeader Serializer
class TemplateMessageHeaderSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['text', 'image',
                                            'video', 'document'])
    text = serializers.CharField(required=False)
    url = serializers.CharField(required=False)
    fileName = serializers.CharField(required=False, allow_null=True)


# TemplateMessageText Serializer
class TemplateMessageTextSerializer(serializers.Serializer):
    type = serializers.CharField()
    text = serializers.CharField()


# TemplateMessageButton Serializer
class TemplateMessageButtonSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['QUICK_REPLY', 'URL',
                                            'PHONE_NUMBER'])
    text = serializers.CharField()
    payload = serializers.CharField(required=False, allow_null=True)
    url = serializers.CharField(required=False)
    phoneNumber = serializers.CharField(required=False)


# TemplateMessage Serializer
class TemplateMessageSerializer(serializers.Serializer):
    header = TemplateMessageHeaderSerializer(required=False)
    body = TemplateMessageTextSerializer()
    footer = TemplateMessageTextSerializer(required=False)
    button = TemplateMessageButtonSerializer(many=True, required=False)
    templateName = serializers.CharField()
    templateLanguage = serializers.CharField()


# InteractiveMessage Serializer
class InteractiveTextSerializer(serializers.Serializer):
    text = serializers.CharField()


# InteractiveMessageHeaderText Serializer
class InteractiveMessageHeaderTextSerializer(serializers.Serializer):
    type = serializers.CharField()
    text = serializers.CharField()


# InteractiveMessageHeaderMedia Serializer
class InteractiveMessageHeaderMediaSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['image', 'video', 'document'])
    fileType = serializers.CharField()
    url = serializers.CharField()
    size = serializers.IntegerField()
    fileName = serializers.CharField(required=False, allow_null=True)


# InteractiveMessageListSectionRow Serializer
class InteractiveMessageListSectionRowSerializer(serializers.Serializer):
    title = serializers.CharField()
    id = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True)


# InteractiveMessageListSection Serializer
class InteractiveMessageListSectionSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_null=True)
    rows = InteractiveMessageListSectionRowSerializer(many=True)


# InteractiveMessageButton Serializer
class InteractiveMessageButtonSerializer(serializers.Serializer):
    title = serializers.CharField()
    id = serializers.CharField()


# InteractiveMessage Serializer
class InteractiveMessageSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['list', 'button'])
    header = serializers.DictField(required=False, allow_null=True)
    body = InteractiveTextSerializer()
    footer = InteractiveTextSerializer(required=False, allow_null=True)
    sections = InteractiveMessageListSectionSerializer(many=True,
                                                       required=False)
    buttons = InteractiveMessageButtonSerializer(many=True, required=False)
    button = serializers.CharField(required=False, allow_null=True)


# Message
class MessageSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[
        'TEXT', 'IMAGE', 'VIDEO', 'AUDIO', 'DOCUMENT', 'LOCATION', 'CONTACTS',
        'BUTTON', 'TEMPLATE', 'INTERACTIVE'
    ])
    text = serializers.CharField(required=False)
    url = serializers.CharField(required=False)
    caption = serializers.CharField(required=False, allow_null=True)
    payload = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    address = serializers.CharField(required=False)
    latitude = serializers.CharField(required=False)
    longitude = serializers.CharField(required=False)
    templateMessage = TemplateMessageSerializer(required=False)
    interactiveMessage = InteractiveMessageSerializer(required=False)
    contacts = ContactsSerializer(many=True, required=False)
    context = ContextSerializer(required=False, allow_null=True)


# Main Payload
class AIChat(serializers.Serializer):
    to = serializers.CharField()
    from_ = serializers.CharField(source="from",
                                  allow_null=True,
                                  required=False)
    messageId = serializers.CharField()
    dtMessageId = serializers.CharField()
    pairedMessageId = serializers.CharField(required=False, allow_null=True)
    dtPairedMessageId = serializers.CharField(required=False, allow_null=True)
    receivedAt = serializers.DateTimeField(allow_null=True)
    integrationType = serializers.ChoiceField(choices=['WHATSAPP'],
                                              allow_null=True)
    status = serializers.CharField(required=False, allow_null=True)
    message = MessageSerializer()
    contact = ContactSerializer()


class ToolCallSerializer(serializers.ModelSerializer):
    class Meta:
        model = ToolCall
        fields = ['name', 'tool_id', 'args', 'type']


class ContactModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['full_name', 'lead_type', 'reason_of_approach',
                  'phone', 'lead_reason']

    def to_representation(self, instance):
        """
        Override to dynamically filter fields based on request query params.
        """
        request = self.context.get('request')
        data = super().to_representation(instance)

        if request:
            requested_fields = request.query_params.get('fields')
            if requested_fields:
                requested_fields = requested_fields.split(',')
                data = {
                    field: data[field] for field in requested_fields
                    if field in data
                }

        return data


class ContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = ['type', 'content']


class ConversationSerializer(serializers.ModelSerializer):
    tool_calls = ToolCallSerializer(
        many=True, read_only=True, source="toolcall_set")
    contents = ContentSerializer(
        many=True, read_only=True, source="content_set")
    contact = ContactModelSerializer(read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'contact', 'created_at',
                  'conversation_type', 'tool_calls', 'contents']

    def to_representation(self, instance):
        """
        Override to dynamically filter fields based on request query params.
        """
        request = self.context.get('request')
        data = super().to_representation(instance)

        if request:
            requested_fields = request.query_params.get('fields')
            if requested_fields:
                requested_fields = requested_fields.split(',')
                data = {
                    field: data[field] for field in requested_fields
                    if field in data
                }

            contact_fields = request.query_params.get('contact_fields')
            if contact_fields and "contact" in data:
                contact_fields = contact_fields.split(',')
                data['contact'] = {
                    field: data['contact'][field] for field in contact_fields
                    if field in data['contact']
                }

            tool_calls_fields = request.query_params.get('tool_calls_fields')
            if tool_calls_fields and "tool_calls" in data:
                tool_calls_fields = tool_calls_fields.split(',')
                data['tool_calls'] = [
                    {
                        field: tool[field] for field in tool_calls_fields
                        if field in tool
                    }
                    for tool in data['tool_calls']
                ]

            contents_fields = request.query_params.get('contents_fields')
            if contents_fields and "contents" in data:
                contents_fields = contents_fields.split(',')
                data['contents'] = [
                    {
                        field: tool[field] for field in contents_fields
                        if field in tool
                    }
                    for tool in data['contents']
                ]

        return data
