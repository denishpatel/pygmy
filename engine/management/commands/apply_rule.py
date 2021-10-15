import logging
from django.utils import timezone
from django.db import transaction
from django.core.management import BaseCommand
from engine.rules.logger_utils import ActionLogger
from engine.rules.rules_helper import RuleHelper
from engine.models import Rules, ActionLogs
logger = logging.getLogger(__name__)

import os

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('rule_id', nargs='+', type=int, help="Rule id to run. You can provide multiple "
                            "rule ids to run multiple rule")

    def handle(self, *args, **kwargs):
        logger.debug(os.environ)
        logger.debug(f"My PID is {os.getpid()}")
        msg = ""
        for rid in kwargs['rule_id']:
            self.try_rule(rid)

    @transaction.atomic()
    def try_rule(self,rid):
        too_many_cooks = False
        try:
            try:
                rule_db = Rules.objects.select_for_update(skip_locked=True).get(id=rid)
            except:
                # The rule might not exist, or might be merely locked.
                # If this get fails it's because it doesn't exist for real, and we can be happen to let our normal exception handling below have its way.
                unlocked_rule_db = Rules.objects.get(id=rid)
                # If we get here, though, we know it's merely locked and currently being worked on.
                # Sadly we don't know much other than that, because nothing has been committed yet
                logger.error(f"Refusing to run locked rule because it is currently being worked")
                too_many_cooks = True
                return

            if rule_db.working_pid is not None:
                # Probably started a while ago, so try to be helpful and report the delta in minutes, not seconds
                logger.error(f"Refusing to run stale rule because pid {rule_db.working_pid} started this rule at {rule_db.last_started} ({int((timezone.now().timestamp()-rule_db.last_started.timestamp())/60)} minutes ago)")
                too_many_cooks = True
                return
            else:
                ActionLogger.add_log(rule_db, f"Rule {rid} execution is started by pid {os.getpid()}")
            helper = RuleHelper.from_id(rid)
            helper.check_exception_date()
            rule_db.working_pid = os.getpid()
            rule_db.last_started = timezone.now()
            rule_db.save()
            helper.apply_rule()
            rule_db.status = True
            rule_db.err_msg = ""
            msg = "Successfully Executed Rule"
            print("Rule has completed successfully")
        except Exception as e:
            rule_db.status = False
            rule_db.err_msg = e
            msg = e
            logger.error(e)
            # msg = "Rule not matched"
        finally:
            if too_many_cooks == False:
                logger.debug("cleaning up rule upon completion")
                rule_db.working_pid = None
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
