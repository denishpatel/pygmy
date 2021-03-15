from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from engine.aws_wrapper import AWSData
from webapp.models import Settings


class SettingsView(LoginRequiredMixin, View):
    template = "settings/list.html"

    def get(self, request, *args, **kwargs):
        settings = Settings.objects.all().order_by("id")
        return render(request, self.template, {
            "settings": settings
        })

    def post(self, request, *args, **kwargs):
        return render(request, self.template, {
            "test": "test"
        })

    def dispatch(self, *args, **kwargs):
        return super(SettingsView, self).dispatch(*args, **kwargs)


class SettingsRefreshView(LoginRequiredMixin, View):
    template = "settings/list.html"

    def get(self, request, *args, **kwargs):
        settingId = request.GET.get("settingId", None)
        try:
            if settingId:
                aws = AWSData()
                if settingId == "ec2":
                    aws.describe_ec2_instances()
                elif settingId == "rds":
                    aws.describe_rds_instances()
                elif settingId == "logs":
                    pass
                elif settingId == "all":
                    aws.describe_ec2_instances()
                    aws.describe_rds_instances()
            return JsonResponse({})
        except Exception as e:
            return JsonResponse({}, status=500)

    def post(self, request, *args, **kwargs):
        return JsonResponse({})

    def dispatch(self, *args, **kwargs):
        return super(SettingsRefreshView, self).dispatch(*args, **kwargs)
