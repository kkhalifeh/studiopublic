from django_filters import rest_framework as filters
from .models import Conversation, Contact


class ContactFilter(filters.FilterSet):
    created_at_gte = filters.DateTimeFilter(
        field_name="conversation__created_at",
        lookup_expr="gte"
    )

    created_at_lte = filters.DateTimeFilter(
        field_name="conversation__created_at",
        lookup_expr="lte"
    )

    lead_type = filters.BaseInFilter(field_name="lead_type",
                                     lookup_expr="in")

    reason_of_approach = filters.BaseInFilter(
        field_name="reason_of_approach",
        lookup_expr="in")

    toolcall_name = filters.BaseInFilter(
        field_name="conversation__toolcall__name",
        lookup_expr="in"
    )

    class Meta:
        model = Contact
        fields = ['phone', 'lead_type', 'reason_of_approach', 'toolcall_name']


class ConversationFilter(filters.FilterSet):
    created_at_gte = filters.DateTimeFilter(field_name="created_at",
                                            lookup_expr="gte")

    created_at_lte = filters.DateTimeFilter(field_name="created_at",
                                            lookup_expr="lte")

    contact_phone = filters.CharFilter(field_name="contact__phone",
                                       lookup_expr="exact")

    contact_lead_type = filters.BaseInFilter(field_name="contact__lead_type",
                                             lookup_expr="in")

    contact_reason_of_approach = filters.BaseInFilter(
        field_name="contact__reason_of_approach",
        lookup_expr="in")

    toolcall_name = filters.BaseInFilter(field_name="toolcall__name",
                                         lookup_expr="in")

    toolcall_tool_id = filters.CharFilter(field_name="toolcall__tool_id",
                                          lookup_expr="exact")

    tool_type = filters.CharFilter(field_name="toolcall__type",
                                   lookup_expr="exact")

    content_type = filters.CharFilter(field_name="content__type",
                                      lookup_expr="exact")

    conversation_type_in = filters.BaseInFilter(
        field_name="conversation_type",
        lookup_expr="in")

    class Meta:
        model = Conversation
        fields = ['created_at', 'contact_phone', 'contact_lead_type',
                  'contact_reason_of_approach', 'toolcall_name',
                  'toolcall_tool_id', 'conversation_type', 'tool_type',
                  'content_type', 'conversation_type_in']
