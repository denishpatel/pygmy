import json
from django.shortcuts import render
from django.views import View
from engine.models import EC2, RDS, Rules, SCALE_UP, SCALE_DOWN
from engine.utils import get_instance_types, create_cron


class CreateRulesView(View):
    template = "rule/create.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ec2 = get_instance_types(EC2)
        self.rds = get_instance_types(RDS)

    def get(self, request, **kwargs):
        return render(request, self.template, {
            "ec2_types": self.ec2,
            "rds_types": self.rds
        })

    def post(self, request, **kwargs):
        result = dict()
        try:
            scale_up_time = request.POST.get("scale_up_time", None)
            scale_down_time = request.POST.get("scale_down_time", None)
            scale_up_ec2 = request.POST.get("scale_up_ec2", None)
            scale_down_ec2 = request.POST.get("scale_down_ec2", None)
            scale_up_rds = request.POST.get("scale_up_rds", None)
            scale_down_rds = request.POST.get("scale_down_rds", None)
            if scale_up_time and scale_down_time and scale_down_ec2 and scale_down_rds and scale_up_ec2 and scale_up_rds:
                # Scale down Rule
                self.create_rule(SCALE_DOWN, scale_down_time, scale_down_ec2, scale_down_rds)
                # Scale UP Rule
                self.create_rule(SCALE_UP, scale_up_time, scale_up_ec2, scale_up_rds)
                result.update({"success": True})
            else:
                raise Exception
        except Exception as e:
            result.update({"error": "missing parameter"})
        return render(request, self.template, result)

    def dispatch(self, *args, **kwargs):
        return super(CreateRulesView, self).dispatch(*args, **kwargs)

    def create_rule(self, rule_type, time, ec2_type, rds_type):
        rules = json.dumps({
            "ec2_type": ec2_type,
            "rds_type": rds_type
        })
        rule_db, created = Rules.objects.get_or_create(action=rule_type, rule=rules, run_at=time)
        create_cron(rule_db)


class RulesView(View):
    template = "rule/rules.html"

    def get(self,request, **kwargs):
        rules = Rules.objects.all()
        return render(request, self.template, {
            "rules": rules
        })

    def dispatch(self, *args, **kwargs):
        return super(RulesView, self).dispatch(*args, **kwargs)
