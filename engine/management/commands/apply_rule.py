import time
from django.utils import timezone
from engine.aws_wrapper import AWSData
from django.core.management import BaseCommand
from engine.utils import RuleUtils, set_retry_cron
from engine.models import Rules, ActionLogs, ExceptionData, EC2, RDS


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('rule_id', nargs='+', type=int, help="Rule id to run. You can provide multiple "
                            "rule ids to run multiple rule")

    def handle(self, *args, **kwargs):
        aws = AWSData()
        msg = ""
        for rid in kwargs['rule_id']:
            try:
                rule_db = Rules.objects.get(id=rid)
                # Update db with latest info()
                if rule_db.cluster.type == EC2:
                    aws.describe_ec2_instances()
                elif rule_db.cluster.type == RDS:
                    aws.describe_rds_instances()
                try:
                    RuleUtils.check_exception_date(rule_db)
                except ExceptionData.DoesNotExist:
                    pass

                # Check rule is Reverse Rule or not
                if rule_db.parent_rule:
                    RuleUtils.reverse_rule(rule_db)
                else:
                    RuleUtils.apply_rule(rule_db)
                rule_db.status = True
                rule_db.err_msg = ""
                msg = "Successfully Executed Rule"

                # auto reload of the instances
                aws.describe_ec2_instances()
                aws.describe_rds_instances()
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
