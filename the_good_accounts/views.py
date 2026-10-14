from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class HomeView(LoginRequiredMixin, TemplateView):
    """Landing page after login. Anonymous users are sent to the login page."""

    template_name = "home.html"