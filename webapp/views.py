from django.shortcuts import render
from django.views import View


# Create your views here.
from engine.aws_wrapper import AWSData
from engine.models import DbCredentials


class LandingView(View):
    template = "home.html"

    def get(self, request, **kwargs):
        ad = AWSData()
        rds_instances = ad.describe_rds_instances()
        ec2_instances = ad.describe_ec2_instances()
        print(rds_instances)
        return render(request, self.template, {
            "rds": rds_instances,
            "ec2": ec2_instances
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

