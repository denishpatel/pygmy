from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from engine.models import EC2, RDS, Rules, SCALE_UP, SCALE_DOWN, ClusterInfo, RuleType
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
            "clusters": get_selection_list(ClusterInfo.objects.all(), "type", "name", "id")
        })

    def post(self, request, **kwargs):
        result = dict()
        try:
            name = request.POST.get("name", None)
            r_op = request.POST.get("r_op", None)
            r_threshold = request.POST.get("r_threshold", None)
            cluster = request.POST.get("cluster_id", None)
            action = request.POST.get("action", None)
            time = request.POST.get("time", None)
            ec2_type = request.POST.get("ec2_type", None)
            rds_type = request.POST.get("rds_type", None)

            if cluster and action.upper() in (SCALE_UP, SCALE_DOWN) and time and (ec2_type or rds_type):
                # Scale down Rule
                self.create_rule(request.POST)
                result.update({"success": True})
            else:
                raise Exception
        except Exception as e:
            print(str(e))
            result.update({"error": "missing parameter", "data": request.POST})
        return render(request, self.template, result)

    def dispatch(self, *args, **kwargs):
        return super(CreateRulesView, self).dispatch(*args, **kwargs)

    def create_rule(self, data):
        # name, rule_type, cluster_id, time, ec2_type, rds_type
        rules = {
            "ec2_type": data.get("ec2_type", None),
            "rds_type": data.get("rds_type", None),
            "rl_threshold": data.get("r_threshold", None),
            "rl_op": data.get("r_op", None)
        }
        rule_db = Rules()
        rule_db.name = data.get("name", None)
        rule_db.action = data.get("action", None)
        rule_db.cluster_id = data.get("cluster_id", None)
        rule_db.run_at = data.get("time", None)
        rule_db.rule = rules
        rule_db.save()
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
                "clusters": get_selection_list(ClusterInfo.objects.all(), "type", "name", "id"),
                "data": rule
            }
        except Rules.DoesNotExist:
            ctx = {
                "not_found": "not found"
            }
        return render(request, self.template, ctx)

    def delete(self, request, id, **kwargs):
        rule = Rules.objects.get(id=id)
        rule.delete()
        return JsonResponse({"success": True})

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

            if cluster and action.upper() in (SCALE_UP, SCALE_DOWN) and time and (ec2_type or rds_type):
                self.update_rule(rule, request.POST)
                result.update({"success": True})
            else:
                raise Exception
        except Rules.DoesNotExist:
            result = {"not_found": "not found"}
        except Exception as e:
            print(str(e))
            result = {"error": "missing parameter", "data": rule}
        return render(request, self.template, result)

    def dispatch(self, *args, **kwargs):
        return super(EditRuleView, self).dispatch(*args, **kwargs)

    def update_rule(self, rule_db, data):
        rules = {
            "ec2_type": data.get("ec2_type", None),
            "rds_type": data.get("rds_type", None),
            "rl_threshold": data.get("r_threshold", None),
            "rl_op": data.get("r_op", None)
        }
        rule_db.name = data.get("name", None)
        rule_db.action = data.get("action", None)
        rule_db.cluster_id = data.get("cluster_id", None)
        rule_db.run_at = data.get("time", None)
        rule_db.rule = rules
        rule_db.save()
        create_cron(rule_db)


class RulesView(View):
    template = "rule/rules.html"

    def get(self, request, **kwargs):
        rules = Rules.objects.all()
        return render(request, self.template, {
            "rules": rules
        })

    def dispatch(self, *args, **kwargs):
        return super(RulesView, self).dispatch(*args, **kwargs)
