import threading
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from engine.aws.aws_utils import AWSUtil
from webapp.models import Settings, SYNC, CONFIG, AWS_REGION


class SettingsView(LoginRequiredMixin, View):
    template = "settings/list.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {
            "sync": Settings.objects.filter(type=SYNC).order_by("id"),
            "config": Settings.objects.filter(type=CONFIG).order_by("id"),
            "aws_region": Settings.objects.filter(type=AWS_REGION).order_by("id")
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
            "aws_region": Settings.objects.filter(type=AWS_REGION).order_by("id"),
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
                # aws = AWSData()
                sync_setting = Settings.objects.get(name=settingId)
                if not sync_setting.in_progress:
                    start_background_sync(sync_setting)
            return JsonResponse({})
        except Exception as e:
            print(str(e))
            return JsonResponse({}, status=500)

    def post(self, request, *args, **kwargs):
        return JsonResponse({})

    def dispatch(self, *args, **kwargs):
        return super(SettingsRefreshView, self).dispatch(*args, **kwargs)


def start_background_sync(sync_setting):
    sync_setting.in_progress = True
    sync_setting.last_sync = timezone.now()
    sync_setting.save()
    try:
        if sync_setting.name != "logs":
            aws = AWSUtil.get_aws_service(sync_setting.name.upper())
            aws.get_instances()
    except Exception as e:
        pass
    sync_setting.in_progress = False
    sync_setting.last_sync = timezone.now()
    sync_setting.save()
