from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .serializers import RegisterSerializer, UserSerializer
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView

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
    success_url = reverse_lazy("accounts:register")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Your account has been created.")
        return response