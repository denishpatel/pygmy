import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View

from engine.aws_wrapper import AWSData
from engine.models import DbCredentials, ClusterInfo, EC2, AllEc2InstancesData, RdsInstances, Ec2DbInfo, RDS, \
    AllEc2InstanceTypes
from engine.utils import get_instance_types


class LandingView(LoginRequiredMixin, View):
    template = "home.html"

    def get(self, request, **kwargs):
        # ad = AWSData()
        # rds_instances = ad.describe_rds_instances()
        # ec2_instances = ad.describe_ec2_instances()
        # print(rds_instances)
        # clusters = ClusterInfo.objects.all()
        dbInfo = Ec2DbInfo.objects.all()
        return render(request, self.template, {
            "dbs": dbInfo
        })

    def dispatch(self, *args, **kwargs):
        return super(LandingView, self).dispatch(*args, **kwargs)


class SecretsView(LoginRequiredMixin, View):
    template = "credentials.html"

    def get(self, request, **kwargs):
        credentials = DbCredentials.objects.all()
        return render(request, self.template, {
            "secrets": credentials
        })

    def dispatch(self, *args, **kwargs):
        return super(SecretsView, self).dispatch(*args, **kwargs)


class ClusterView(LoginRequiredMixin, View):
    template = "cluster/list.html"

    def get(self, request, id, **kwargs):
        try:
            cluster = ClusterInfo.objects.get(id=id)
            instances = Ec2DbInfo.objects.filter(cluster_id=cluster)
            instances_types = list(AllEc2InstanceTypes.objects.all().values("instance_type").annotate(value=F('instance_type'), data=F('instance_type')))
            return render(request, self.template, {
                "instances": instances,
                "cluster": cluster,
                "instance_types": json.dumps(instances_types)
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
            if name:
                cluster.name = name
                cluster.save()
                return redirect(reverse("clusters", args=[cluster.id]))
                # return render(request, self.template, {
                #     "success": True,
                #     "cluster": cluster
                # })
        except ClusterInfo.DoesNotExist:
            return render(request, self.template, {"error": "not found"})

    def dispatch(self, *args, **kwargs):
        return super(ClusterEditView, self).dispatch(*args, **kwargs)


class InstanceView(LoginRequiredMixin, View):
    template = "cluster/instance_update.html"

    def get(self, request, cluster_type, id, **kwargs):
        try:
            instance, db_info = self.get_instance(cluster_type, id)
            return render(request, self.template, {
                "types": get_instance_types(cluster_type),
                "dbInfo": db_info,
                "instance": instance
            })
        except AllEc2InstancesData.DoesNotExist or RdsInstances.DoesNotExist:
            return render(request, self.template, { "error": "Not found" })

    def post(self, request, cluster_type, id, *args, **kwargs):
        instance_type = request.POST.get("instance_type", None)
        instance = None
        try:
            instance, db_info = self.get_instance(cluster_type, id)
            if cluster_type.upper() == EC2:
                AWSData().scale_ec2_instance(instance.instanceId, instance_type)
            else:
                AWSData().scale_rds_instance(instance.dbInstanceIdentifier, instance_type, instance.dBParameterGroups)
            return render(request, self.template, {
                "types": get_instance_types(cluster_type),
                "instance": instance,
                "dbInfo": db_info,
                "success": True
            })
        except Exception as e:
            return render(request, self.template, {
                "instance": instance,
                "error": "failed to process",
            })

    def get_instance(self, cluster_type, id):
        if cluster_type.upper() == EC2:
            instance = AllEc2InstancesData.objects.get(instanceId=id)
            db_info = Ec2DbInfo.objects.get(instance_id=instance.instanceId)
        else:
            instance = RdsInstances.objects.get(dbInstanceIdentifier=id)
            db_info = Ec2DbInfo.objects.get(instance_id=instance.dbInstanceIdentifier)
        return instance, db_info

    def dispatch(self, *args, **kwargs):
        return super(InstanceView, self).dispatch(*args, **kwargs)


# class LoginView(View):
#     template = "login.html"
#
#     def get(self, request):
#         return render(request, self.template)
#
#     def post(self, request):
#         return render(request, self.template)
#
#     def dispatch(self, *args, **kwargs):
#         return super(LoginView, self).dispatch(*args, **kwargs)