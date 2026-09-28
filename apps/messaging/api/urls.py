from django.urls import path

from .views import ConversationDetailView, MessagesRootView

app_name = "messaging_api"

urlpatterns = [
    path("", MessagesRootView.as_view(), name="root"),
    path("<int:pk>/", ConversationDetailView.as_view(), name="conversation"),
]
