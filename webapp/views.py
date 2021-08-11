from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from rest_framework.response import Response
from engine.models import DbCredentials, ClusterInfo, Ec2DbInfo
from engine.rules.DbHelper import DbHelper
from engine.aws.aws_utils import AWSUtil


class LandingView(LoginRequiredMixin, View):
    template = "home.html"

    def get(self, request, **kwargs):
        dbInfo = Ec2DbInfo.objects.all()
        return render(request, self.template, {
            "dbs": dbInfo
        })

    def dispatch(self, *args, **kwargs):
        return super(LandingView, self).dispatch(*args, **kwargs)


class SecretsView(LoginRequiredMixin, View):
    template = "credentials.html"

    def get(self, request, **kwargs):
        credentials = DbCredentials.objects.all().order_by("id")
        return render(request, self.template, {
            "secrets": credentials
        })

    def dispatch(self, *args, **kwargs):
        return super(SecretsView, self).dispatch(*args, **kwargs)


class SecretsEditView(LoginRequiredMixin, View):

    def post(self, request, id, **kwargs):
        try:
            secret = DbCredentials.objects.get(id=id)
            username = request.POST.get("username")
            password = request.POST.get("password")
            if username and password:
                secret.user_name = username
                secret.password = password
                secret.save()
                if secret.name in ["aws"]:
                    AWSUtil.update_aws_region_list()
            else:
                return Response(status=400)
        except DbCredentials.DoesNotExist:
            return Response(status=400)
        return JsonResponse(data=dict({"success": True}),status=200)

    def dispatch(self, *args, **kwargs):
        return super(SecretsEditView, self).dispatch(*args, **kwargs)


class ClusterView(LoginRequiredMixin, View):
    template = "cluster/list.html"

    def get(self, request, id, **kwargs):
        try:
            cluster = ClusterInfo.objects.get(id=id)
            instances = Ec2DbInfo.objects.filter(cluster_id=cluster)
            return render(request, self.template, {
                "instances": instances,
                "cluster": cluster,
            })
        except ClusterInfo.DoesNotExist:
            return render(request, self.template, {
                "error": "not found"
            })

    def dispatch(self, *args, **kwargs):
        return super(ClusterView, self).dispatch(*args, **kwargs)


class ClusterEditView(LoginRequiredMixin, View):
    template = "cluster/edit.html"

    def get(self, request, id, **kwargs):
        try:
            cluster = ClusterInfo.objects.get(id=id)
            return render(request, self.template, {
                "cluster": cluster
            })
        except ClusterInfo.DoesNotExist:
            return render(request, self.template, {
                "error": "not found"
            })

    def post(self, request, id, *args, **kwargs):
        try:
            cluster = ClusterInfo.objects.get(id=id)
            name = request.POST.get("name", None)
            databaseName = request.POST.get("databaseName", None)
            if name:
                cluster.name = name
            if databaseName:
                cluster.databaseName = databaseName
            cluster.save()
            return redirect(reverse("clusters", args=[cluster.id]))
        except ClusterInfo.DoesNotExist:
            return render(request, self.template, {"error": "not found"})

    def dispatch(self, *args, **kwargs):
        return super(ClusterEditView, self).dispatch(*args, **kwargs)


class InstanceView(LoginRequiredMixin, View):
    template = "cluster/instance_update.html"

    def get(self, request, cluster_type, id, **kwargs):
        try:
            # instance, db_info = self.get_instance(cluster_type, id)
            db_helper = DbHelper.from_id(id)
            return render(request, self.template, {
                "types": db_helper.get_supported_types(),
                "dbInfo": db_helper.db_info,
                "instance": db_helper.instance
            })
        except Ec2DbInfo.DoesNotExist:
            return render(request, self.template, { "error": "Not found" })

    def post(self, request, cluster_type, id, *args, **kwargs):
        instance_type = request.POST.get("instance_type", None)
        instance = None
        try:
            db_helper = DbHelper.from_id(id)
            instance = db_helper.instance
            db_helper.update_instance_type(instance_type)
            return render(request, self.template, {
                "types": db_helper.get_supported_types(),
                "instance": db_helper.instance,
                "dbInfo": db_helper.db_info,
                "success": True
            })
        except Exception as e:
            return render(request, self.template, {
                "instance": instance,
                "error": "failed to process",
            })
    #
    # def get_instance(self, cluster_type, id):
    #     if cluster_type.upper() == EC2:
    #         instance = AllEc2InstancesData.objects.get(instanceId=id)
    #         db_info = Ec2DbInfo.objects.get(instance_id=instance.instanceId)
    #     else:
    #         instance = RdsInstances.objects.get(dbInstanceIdentifier=id)
    #         db_info = Ec2DbInfo.objects.get(instance_id=instance.dbInstanceIdentifier)
    #     return instance, db_info

    def dispatch(self, *args, **kwargs):
        return super(InstanceView, self).dispatch(*args, **kwargs)
