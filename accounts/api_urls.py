from django.urls import path

from .views import LoginAPIView, LogoutAPIView, MeAPIView, RegisterAPIView

app_name = "accounts_api"

urlpatterns = [
    path("auth/register/", RegisterAPIView.as_view(), name="register"),
    path("auth/login/", LoginAPIView.as_view(), name="login"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),
    path("me/", MeAPIView.as_view(), name="me"),
]