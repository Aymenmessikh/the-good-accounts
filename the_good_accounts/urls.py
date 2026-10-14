from django.contrib import admin
from django.urls import include, path

from .views import HomeView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("accounts.api_urls")),
    path("", HomeView.as_view(), name="home"),
    path("", include("accounts.urls")),
]