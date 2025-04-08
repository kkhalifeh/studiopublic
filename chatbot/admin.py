from django.contrib import admin
from .models import ChatRequest, Contact, Request, OAuth, Conversation, \
    CacheResponse, ToolCall, Content, SkipMessage
from adminfilters.filters import UnionFieldListFilter, ValueFilter
from adminfilters.mixin import AdminFiltersMixin

# Register your models here.


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('phone', 'lead_type', 'created_at', 'test_number',
                    'reason_of_approach', 'full_name')


@admin.register(ChatRequest)
class ChatRequestAdmin(admin.ModelAdmin):
    list_display = ('status', 'created_at', 'contact_phone', 'error_message')

    def contact_phone(self, obj):
        return obj.contact.phone
    contact_phone.short_description = 'Contact Phone'


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('params', )


@admin.register(OAuth)
class OAuthAdmin(admin.ModelAdmin):
    list_display = ('type', 'refresh_token', 'access_token')


@admin.register(CacheResponse)
class CacheResponseAdmin(admin.ModelAdmin):
    list_display = ('type', 'message')


@admin.register(Conversation)
class ConversationAdmin(AdminFiltersMixin, admin.ModelAdmin):
    list_display = ('contact_phone', 'message', 'conversation_type')
    list_filter = (
        ('conversation_type', UnionFieldListFilter),  # Multi-select filter
        ('contact__phone', ValueFilter)
    )
    ordering = ["-created_at"]

    def contact_phone(self, obj):
        return obj.contact.phone
    contact_phone.short_description = 'Contact Phone'


@admin.register(ToolCall)
class ToolCallAdmin(admin.ModelAdmin):
    list_display = ('name', 'tool_id', 'args', 'type', 'conversation')


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ('type', 'content', 'conversation')


@admin.register(SkipMessage)
class SkipMessageAdmin(admin.ModelAdmin):
    list_display = ('text', )
