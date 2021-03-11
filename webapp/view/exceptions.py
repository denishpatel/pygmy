import json

from django.http import JsonResponse
from django.shortcuts import render, redirect
from datetime import datetime
from django.views import View

from engine.models import ExceptionData, ClusterInfo


class ExceptionsView(View):
    template = "exception/list.html"

    def get(self, request, **kwargs):
        exceptionList = ExceptionData.objects.filter(exception_date__gte=datetime.now().date()).order_by("exception_date")
        return render(request, self.template, {
            "exceptions": exceptionList
        })

    def dispatch(self, *args, **kwargs):
        return super(ExceptionsView, self).dispatch(*args, **kwargs)


class ExceptionsCreateView(View):
    template = "exception/create.html"

    def get(self, request, **kwargs):
        clusterName = self.getClusterName()
        return render(request, self.template, {
            # "exceptions": exceptionList,
            "clusterName": clusterName
        })

    def post(self, request, **kwargs):
        dates = request.POST.get("dates", None)
        clusters = request.POST.get("clusterNames", None)
        try:
            if dates:
                clustersList = json.loads(clusters)
                datesList = dates.split(",")
                for date in datesList:
                    exc, created = ExceptionData.objects.get_or_create(exception_date=date.strip(' '))
                    if created:
                        exc.clusters = clustersList
                    else:
                        exc.clusters = list({v['id']:v for v in exc.clusters + clustersList}.values())
                    exc.save()
                return render(request, self.template, {"success": True})
        except Exception as e:
            print(e)
        clusterName = self.getClusterName
        return render(request, self.template, {
            "clusterName": clusterName
        })

    @staticmethod
    def getClusterName():
        return list({"value": "{}-({})".format(cluster.name, cluster.id), "id": cluster.id} for cluster in ClusterInfo.objects.all())

    @staticmethod
    def getClusterTagName(clusters):
        return ",".join(list(c["value"] for c in clusters))

    def dispatch(self, *args, **kwargs):
        return super(ExceptionsCreateView, self).dispatch(*args, **kwargs)


class ExceptionsEditView(View):
    template = "exception/edit.html"

    def get(self, request, id, **kwargs):
        try:
            exception = ExceptionData.objects.get(id=id)
            clusterName = ExceptionsCreateView.getClusterName()
            return render(request, self.template, {
                "clusterName": clusterName,
                "exception": exception
            })
        except ExceptionData.DoesNotExist as e:
            return render(request, self.template, {
                "not_found": True,
            })

    def post(self, request, **kwargs):
        dates = request.POST.get("dates", None)
        clusters = request.POST.get("clusterNames", None)
        try:
            if dates:
                clustersList = json.loads(clusters)
                datesList = dates.split(",")
                for date in datesList:
                    exc, created = ExceptionData.objects.get_or_create(exception_date=date.strip(' '))
                    exc.clusters = clustersList
                    exc.save()
                return render(request, self.template, {"success": True})
        except Exception as e:
            print(e)
        clusterName = ExceptionsCreateView.getClusterName()
        return render(request, self.template, {
            "clusterName": clusterName
        })

    def delete(self, request, id, **kwargs):
        exc_date = ExceptionData.objects.get(id=id)
        exc_date.delete()
        return JsonResponse({"success": True})

    def dispatch(self, *args, **kwargs):
        return super(ExceptionsEditView, self).dispatch(*args, **kwargs)

