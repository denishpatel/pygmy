from django.shortcuts import render
from django.views import View
from engine.aws_wrapper import AWSData
from engine.models import DbCredentials, ClusterInfo, EC2, AllEc2InstancesData, RdsInstances


class LandingView(View):
    template = "home.html"

    def get(self, request, **kwargs):
        # ad = AWSData()
        # rds_instances = ad.describe_rds_instances()
        # ec2_instances = ad.describe_ec2_instances()
        # print(rds_instances)
        clusters = ClusterInfo.objects.all()
        return render(request, self.template, {
            "clusters": clusters
        })

    def dispatch(self, *args, **kwargs):
        return super(LandingView, self).dispatch(*args, **kwargs)


class SecretsView(View):
    template = "credentials.html"

    def get(self, request, **kwargs):
        credentials = DbCredentials.objects.all()
        return render(request, self.template, {
            "secrets": credentials
        })

    def dispatch(self, *args, **kwargs):
        return super(SecretsView, self).dispatch(*args, **kwargs)


class ClusterView(View):
    template = "instances.html"

    def get(self, request, id, **kwargs):
        try:
            cluster = ClusterInfo.objects.get(id=id)
            if cluster.type == EC2:
                instances = AllEc2InstancesData.objects.all()
            else:
                instances = RdsInstances.objects.all()
            return render(request, self.template, {
                "instances": instances
            })
        except ClusterInfo.DoesNotExist:
            return render(request, self.template, {
                "error": "not found"
            })

    def dispatch(self, *args, **kwargs):
        return super(ClusterView, self).dispatch(*args, **kwargs)