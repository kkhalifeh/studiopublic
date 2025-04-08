from django.db import models

# Create your models here.


class LeadType(models.TextChoices):
    HOT_LEAD = 'Hot Lead', 'Hot Lead'
    WARM_LEAD = 'Warm Lead', 'Warm Lead'
    INFORMATION_SEEKER = 'Information Seeker', 'Information Seeker'
    COLD_LEAD = 'Cold Lead', 'Cold Lead'
    UNCERTAIN = 'Uncertain', 'Uncertain'


class ReasonOfApproach(models.TextChoices):
    AdultMembership = 'Adult Membership', 'Adult Membership'
    JuniorMembership = 'Junior Membership', 'Junior Membership'


class ConversationType(models.TextChoices):
    Human = 'Human', 'Human'
    AI = 'AI', 'AI'
    ToolCall = 'ToolCall', 'ToolCall'
    Agent = 'Agent', 'Agent',
    AUDIO_MSG_ERROR = 'AUDIO_MSG_ERROR', 'AUDIO_MSG_ERROR'
    Skip_Message = 'Skip_Message', 'Skip_Message'
    APC_FACE_CARD = 'APC_FACE_CARD', 'APC_FACE_CARD'


class CacheResponse(models.Model):
    message = models.TextField()
    type = models.CharField(max_length=255)


class Contact(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    phone = models.CharField(max_length=255, unique=True)
    test_number = models.BooleanField(default=False)
    lead_type = models.CharField(
        max_length=20,
        choices=LeadType.choices,
        default=LeadType.UNCERTAIN
    )
    reason_of_approach = models.CharField(
        max_length=40,
        choices=ReasonOfApproach.choices,
        null=True
    )
    lead_reason = models.TextField(null=True)
    full_name = models.CharField(max_length=255)


class ChatRequest(models.Model):
    message = models.TextField(null=True)
    image_url = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    status = models.CharField(max_length=20)
    error_message = models.TextField()


class Conversation(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    conversation_type = models.CharField(
        max_length=20,
        choices=ConversationType.choices,
        null=True
    )


class ToolCall(models.Model):
    name = models.CharField(max_length=50)
    tool_id = models.CharField(max_length=50)
    args = models.TextField()
    type = models.CharField(max_length=50)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)


class Content(models.Model):
    type = models.CharField(max_length=50)
    content = models.TextField()
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)


class Request(models.Model):
    params = models.TextField()


class OAuth(models.Model):
    type = models.CharField(max_length=25)
    refresh_token = models.TextField()
    access_token = models.TextField()


class SkipMessage(models.Model):
    text = models.TextField()
