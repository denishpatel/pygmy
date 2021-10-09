from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from engine.models import Rules
from engine.rules.cluster_helper import ClusterHelper
from engine.rules.db_helper import EC2DBHelper, RDSDBHelper
from engine.rules.rules_helper import RuleHelper
from engine.rules.cronutils import CronUtil


class CreateRulesView(LoginRequiredMixin, View):
    template = "rule/create.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ec2 = EC2DBHelper.get_instances_types()
        self.rds = RDSDBHelper.get_instances_types()

    def get(self, request, **kwargs):
        return render(request, self.template, {
            "ec2_types": self.ec2,
            "rds_types": self.rds,
            "clusters": ClusterHelper.get_cluster_list()
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
        RuleHelper.add_rule_db(data)


class EditRuleView(LoginRequiredMixin, View):
    template = "rule/edit.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ec2 = EC2DBHelper.get_instances_types()
        self.rds = RDSDBHelper.get_instances_types()

    def get(self, request, id, **kwargs):
        try:
            rule = Rules.objects.get(id=id)
            ctx = {
                "ec2_types": self.ec2,
                "rds_types": self.rds,
                "clusters": ClusterHelper.get_cluster_list(),
                "data": rule,
                "reverse_rule": rule.child_rule.get() if rule.child_rule.all().count() > 0 else None,
            }
        except Rules.DoesNotExist:
            ctx = {
                "not_found": "not found"
            }
        return render(request, self.template, ctx)

    def delete(self, request, id, **kwargs):
        rule = Rules.objects.get(id=id)
        CronUtil.delete_cron(rule)
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
        RuleHelper.add_rule_db(data, rule_db)


class RulesView(LoginRequiredMixin, View):
    template = "rule/rules.html"

    def get(self, request, **kwargs):
        rules = Rules.objects.all()
        return render(request, self.template, {
            "rules": rules
        })

    def dispatch(self, *args, **kwargs):
        return super(RulesView, self).dispatch(*args, **kwargs)
