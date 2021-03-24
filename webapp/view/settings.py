from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from engine.aws_wrapper import AWSData
from webapp.models import Settings, SYNC, CONFIG


class SettingsView(LoginRequiredMixin, View):
    template = "settings/list.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {
            "sync": Settings.objects.filter(type=SYNC).order_by("id"),
            "config": Settings.objects.filter(type=CONFIG).order_by("id")
        })

    def post(self, request, *args, **kwargs):
        for key, value in request.POST.items():
            try:
                if ("password" not in key.lower()) or ("password" in key.lower() and not value == "dummypass"):
                    setting = Settings.objects.get(name=key)
                    if setting.value != value:
                        setting.value = value
                        setting.save()
            except Settings.DoesNotExist:
                pass

        return render(request, self.template, {
            "sync": Settings.objects.filter(type=SYNC).order_by("id"),
            "config": Settings.objects.filter(type=CONFIG).order_by("id"),
            "success": True
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
