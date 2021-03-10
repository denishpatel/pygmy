from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from engine.models import EC2, RDS, Rules, SCALE_UP, SCALE_DOWN, ClusterInfo, DAILY, CRON
from engine.utils import get_instance_types, create_cron, get_selection_list, delete_cron, RuleUtils


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
            typeTime = request.POST.get("typeTime", "daily")
            cluster = request.POST.get("cluster_id", None)
            action = request.POST.get("action", None)

            if name and cluster and action and typeTime:
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
        RuleUtils.add_rule_db(data)


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
        delete_cron(rule)
        rule.delete()
        return JsonResponse({"success": True})

    def post(self, request, id, **kwargs):
        result = dict()
        try:
            rule = Rules.objects.get(id=id)
            name = request.POST.get("name", None)
            typeTime = request.POST.get("typeTime", "daily")
            cluster = request.POST.get("cluster_id", None)
            action = request.POST.get("action", None)

            if name and cluster and action and typeTime:
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
        RuleUtils.add_rule_db(data, rule_db)


class RulesView(View):
    template = "rule/rules.html"

    def get(self, request, **kwargs):
        rules = Rules.objects.all()
        return render(request, self.template, {
            "rules": rules
        })

    def dispatch(self, *args, **kwargs):
        return super(RulesView, self).dispatch(*args, **kwargs)
