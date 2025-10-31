from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView
from .models import Feedback


class FeedbackCreateView(LoginRequiredMixin, CreateView):
    model = Feedback
    fields = ["type", "message"]
    success_url = "/"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)
