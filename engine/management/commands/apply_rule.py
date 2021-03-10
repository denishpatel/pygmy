import time
from django.utils import timezone
from django.core.management import BaseCommand
from engine.aws_wrapper import AWSData
from engine.models import Rules, Ec2DbInfo, EC2, RDS, ActionLogs
from engine.utils import RuleUtils


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('rule_id', nargs='+', type=int, help="Rule id to run. You can provide multiple "
                            "rule ids to run multiple rule")

    def handle(self, *args, **kwargs):
        for rid in kwargs['rule_id']:
            try:
                aws = AWSData()
                rule_db = Rules.objects.get(id=rid)
                RuleUtils.apply_rule(rule_db)
                rule_db.status = True
                rule_db.err_msg = ""
                msg = "Successfully Executed Rule"
            except Exception as e:
                rule_db.status = False
                rule_db.err_msg = e
                print(str(e))
                print("No rule found")
                msg = "Rule not matched"
            finally:
                rule_db.last_run = timezone.now()
                rule_db.save()
                self.add_log_entry(rule_db, msg)

            # auto reload of the instances
            time.sleep(60)
            aws.describe_ec2_instances()
            aws.describe_rds_instances()
            print("Rule has completed successfully")

    def add_log_entry(self, rule, msg):
        # Add Log entry
        log = ActionLogs()
        log.rule = rule
        log.msg = msg
        log.status = rule.status
        log.save()