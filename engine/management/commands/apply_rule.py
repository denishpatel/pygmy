from django.utils import timezone
from django.core.management import BaseCommand

from engine.rules.LoggerUtils import ActionLogger
from engine.rules.RulesHelper import RuleHelper
from engine.models import Rules, ActionLogs


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('rule_id', nargs='+', type=int, help="Rule id to run. You can provide multiple "
                            "rule ids to run multiple rule")

    def handle(self, *args, **kwargs):

        msg = ""
        for rid in kwargs['rule_id']:
            try:
                rule_db = Rules.objects.get(id=rid)
                ActionLogger.add_log(rule_db, "rule execution is started")
                helper = RuleHelper.from_id(rid)
                helper.check_exception_date()
                helper.apply_rule()
                rule_db.status = True
                rule_db.err_msg = ""
                msg = "Successfully Executed Rule"
                print("Rule has completed successfully")
            except Exception as e:
                rule_db.status = False
                rule_db.err_msg = e
                msg = e
                print(str(e))
                print("No rule found")
                # msg = "Rule not matched"
            finally:
                rule_db.last_run = timezone.now()
                rule_db.save()
                self.add_log_entry(rule_db, msg)

    def add_log_entry(self, rule, msg, extra_info=None):
        # Add Log entry
        log = ActionLogs()
        log.rule = rule
        log.msg = msg
        log.status = rule.status
        log.save()
