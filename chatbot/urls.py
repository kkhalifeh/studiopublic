from django.urls import path
from .views import AIChatView, MetricsView, ConversationListView, \
    ContactListView
# chatbot, reset, login, logout

urlpatterns = [
    path(
        'chat',
        AIChatView.as_view(),
        name="AIChat"
    ),
    # path('', chatbot, name='chatbot'),
    # path('reset', reset, name='reset'),
    # path('login', login, name='login'),
    # path('logout', logout, name='logout'),
    path('conversations/', ConversationListView.as_view(),
         name='conversation-list'),
    path('contacts/', ContactListView.as_view(),
         name='contact-list'),
    path('metrics', MetricsView.as_view(), name='metrics')
]
