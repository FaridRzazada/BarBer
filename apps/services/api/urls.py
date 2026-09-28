from django.urls import path

from .views import ServiceCategoryListView

app_name = "services_api"

urlpatterns = [
    path("", ServiceCategoryListView.as_view(), name="categories"),
]
