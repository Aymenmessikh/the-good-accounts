from rest_framework import generics, permissions, status
from rest_framework.response import Response

from django.contrib import messages
from django.urls import reverse_lazy
from .forms import AccountPasswordChangeForm, ProfileForm, RegisterForm
from rest_framework.views import APIView
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    ProfileSerializer,
    RegisterSerializer,
    UserSerializer,
)

from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, UpdateView

from django.contrib.auth import login, logout, update_session_auth_hash
from .forms import RegisterForm
class RegisterAPIView(generics.CreateAPIView):
    """Create a new account. Open to anonymous users."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # Answer with the safe representation, not with the input serializer
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class RegisterView(CreateView):
    """HTML page to create an account."""

    form_class = RegisterForm
    template_name = "accounts/register.html"
    # Temporary target: it will point to the login page once F3 is done
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Your account has been created.")
        return response

class LoginAPIView(APIView):
    """Authenticate with email + password and open a session."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)  # creates the session and sets the session cookie
        return Response(UserSerializer(user).data)


class LogoutAPIView(APIView):
    """Close the current session. Requires to be logged in."""

    def post(self, request):
        logout(request)  # flushes the session
        return Response(status=status.HTTP_204_NO_CONTENT)

class MeAPIView(generics.RetrieveUpdateAPIView):
    """Read or partially update the profile of the logged-in user."""

    serializer_class = ProfileSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        # No id in the URL: a user can only ever reach their own profile
        return self.request.user

class ChangePasswordAPIView(APIView):
    """Change the password of the logged-in user."""

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Django ties the session to a hash of the password: without this call the
        # user would be logged out right after changing it.
        update_session_auth_hash(request, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

class ProfileView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Show and edit the names of the logged-in user."""

    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")
    success_message = "Your profile has been updated."

    def get_object(self, queryset=None):
        return self.request.user


class AccountPasswordChangeView(SuccessMessageMixin, auth_views.PasswordChangeView):
    """Change password from the website. The session stays valid afterwards."""

    form_class = AccountPasswordChangeForm
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:profile")
    success_message = "Your password has been changed."