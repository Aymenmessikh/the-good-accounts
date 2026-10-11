from django.urls import path

from .views import LoginAPIView, LogoutAPIView, RegisterAPIView

app_name = "accounts_api"

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
]