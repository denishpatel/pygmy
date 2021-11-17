from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View
from rest_framework import generics
from rest_framework.authentication import SessionAuthentication
from rest_framework_datatables.pagination import DatatablesPageNumberPagination

from pygmy.models import Log
from webapp.serializers import LogSerializer


class LogsView(LoginRequiredMixin, View):
    template = "logs/logs.html"
    size = 20

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {
            "logs": Log.objects.order_by("time")[:10]
        })

    def dispatch(self, *args, **kwargs):
        return super(LogsView, self).dispatch(*args, **kwargs)


class LogsApiView(generics.ListAPIView):
    authentication_classes = [SessionAuthentication]
    serializer_class = LogSerializer
    pagination_class = DatatablesPageNumberPagination

    def get_queryset(self):
        return Log.objects.all()
