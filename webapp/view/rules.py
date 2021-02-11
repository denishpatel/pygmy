import json
from django.shortcuts import render
from django.views import View
from engine.models import EC2, RDS, Rules, SCALE_UP, SCALE_DOWN, ClusterInfo
from engine.utils import get_instance_types, create_cron, get_selection_list


class CreateRulesView(View):
    template = "rule/create.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ec2 = get_instance_types(EC2)
        self.rds = get_instance_types(RDS)

    def get(self, request, **kwargs):
        return render(request, self.template, {
            "ec2_types": self.ec2,
            "rds_types": self.rds,
            "clusters": get_selection_list(ClusterInfo.objects.all(), "name", "id")
        })

    def post(self, request, **kwargs):
        result = dict()
        try:
            name = request.POST.get("name", None)
            cluster = request.POST.get("cluster_id", None)
            action = request.POST.get("action", None)
            time = request.POST.get("time", None)
            ec2_type = request.POST.get("ec2_type", None)
            rds_type = request.POST.get("rds_type", None)

            if cluster and action.upper() in (SCALE_UP, SCALE_DOWN) and time and ec2_type and rds_type:
                # Scale down Rule
                self.create_rule(name, action, cluster, time, ec2_type, rds_type)
                result.update({"success": True})
            else:
                raise Exception
        except Exception as e:
            result.update({"error": "missing parameter",
                           "data": request.POST
                           })
        return render(request, self.template, result)

    def dispatch(self, *args, **kwargs):
        return super(CreateRulesView, self).dispatch(*args, **kwargs)

    def create_rule(self, name, rule_type, cluster_id, time, ec2_type, rds_type):
        rules = {
            "ec2_type": ec2_type,
            "rds_type": rds_type
        }
        rule_db, created = Rules.objects.get_or_create(name=name, cluster_id=cluster_id, action=rule_type, rule=rules, run_at=time)
        create_cron(rule_db)


class EditRuleView(View):
    template = "rule/edit.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ec2 = get_instance_types(EC2)
        self.rds = get_instance_types(RDS)

    def get(self, request, id, **kwargs):
        try:
            rule = Rules.objects.get(id=id)
            ctx = {
                "ec2_types": self.ec2,
                "rds_types": self.rds,
                "clusters": get_selection_list(ClusterInfo.objects.all(), "name", "id"),
                "data": rule
            }
        except Rules.DoesNotExist:
            ctx = {
                "not_found": "not found"
            }
        return render(request, self.template, ctx)

    def post(self, request, id, **kwargs):
        result = dict()
        try:
            rule = Rules.objects.get(id=id)
            name = request.POST.get("name", None)
            cluster = request.POST.get("cluster_id", None)
            action = request.POST.get("action", None)
            time = request.POST.get("time", None)
            ec2_type = request.POST.get("ec2_type", None)
            rds_type = request.POST.get("rds_type", None)

            if cluster and action.upper() in (SCALE_UP, SCALE_DOWN) and time and ec2_type and rds_type:
                # Scale down Rule
                self.update_rule(rule, name, action, cluster, time, ec2_type, rds_type)
                result.update({"success": True})
            else:
                raise Exception
        except Rules.DoesNotExist:
            result = {"not_found": "not found"}
        except Exception as e:
            result = {"error": "missing parameter", "data": rule }
        return render(request, self.template, result)

    def dispatch(self, *args, **kwargs):
        return super(EditRuleView, self).dispatch(*args, **kwargs)

    def update_rule(self, rule_db, name, rule_type, cluster_id, time, ec2_type, rds_type):
        rules = {
            "ec2_type": ec2_type,
            "rds_type": rds_type
        }
        rule_db.name = name
        rule_db.action = rule_type
        rule_db.cluster_id = cluster_id
        rule_db.run_at = time
        rule_db.rule = rules
        rule_db.save()
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
