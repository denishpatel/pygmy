from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from engine.models import ActionLogs


class ActionsView(LoginRequiredMixin, View):
    template = "actions/list.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {
            "actions": ActionLogs.objects.all().order_by("-time")
        })

    def dispatch(self, *args, **kwargs):
        return super(ActionsView, self).dispatch(*args, **kwargs)
