from django.shortcuts import render
from django.views import View

from engine.models import ActionLogs


class ActionsView(View):
    template = "actions/list.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {
            "actions": ActionLogs.objects.all()
        })

    def dispatch(self, *args, **kwargs):
        return super(ActionsView, self).dispatch(*args, **kwargs)
