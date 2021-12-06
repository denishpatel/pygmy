import sys
from crontab import CronTab, CronSlices
import getpass
from django.conf import settings
from django.contrib.humanize.templatetags.humanize import ordinal
from engine.models import DAILY
from django_pglocks import advisory_lock
import logging
logger = logging.getLogger(__name__)

cron_lock_id = '42'


class CronUtil:

    @staticmethod
    def create_cron(rule):
        with advisory_lock(cron_lock_id) as acquired:
            cron = CronTab(user=getpass.getuser())
            cron.remove_all(comment="rule_{}".format(str(rule.id)))

            # Run at
            if rule.run_type == DAILY:
                job = cron.new(command="{0}/venv/bin/python {0}/manage.py apply_rule {1}".format(settings.BASE_DIR, rule.id),
                               comment="rule_{}".format(rule.id))
                time = rule.run_at[0].split(":")
                hour = time[0]
                minute = time[1]
                # Setup a cron
                if hour:
                    job.hour.on(hour)
                if minute:
                    job.minute.on(minute)
            else:
                # run_type is cron
                for this_time in rule.run_at:
                    job = cron.new(command="{0}/venv/bin/python {0}/manage.py apply_rule {1}".format(settings.BASE_DIR, rule.id),
                                   comment="rule_{}".format(rule.id))
                    job.setall(this_time)

            cron.write()

    def create_cron_intent(rule_id, instance):
        with advisory_lock(cron_lock_id) as acquired:
            cron = CronTab(user=getpass.getuser())
            cron.remove_all(comment="intent_{}".format(str(rule_id)))
            job = cron.new(command="{0}/venv/bin/python {0}/manage.py apply_intent {1} {2}".format(settings.BASE_DIR, rule_id, instance),
                           comment="intent_{}".format(rule_id))

            # Run on reboot, in case we have crashed.
            job.every_reboot()

            cron.write()

    @staticmethod
    def build_retry_rule_comment(rule_id):
        return f"retry_rule_{rule_id}"

    @staticmethod
    def set_retry_cron(rule, attempt):
        # Get Rule details
        rule_json = rule.rule
        retry_rule = rule_json.get("retry", None)

        if not retry_rule:
            return

        retry_after = retry_rule.get("retry_after")
        max_retry = retry_rule.get("retry_max")

        logger.debug(f"retry_after is {retry_after} and max_retry is {max_retry}")
        if retry_after and max_retry:
            retry_rule_comment = CronUtil.build_retry_rule_comment(rule.id)
            try:
                # Update Crontab jobs
                if int(attempt) == 1:
                    with advisory_lock(cron_lock_id) as acquired:
                        cron = CronTab(user=getpass.getuser())
                        logger.debug("making an entry for our first retry")
                        job = cron.new(
                            command=f"{settings.BASE_DIR}/venv/bin/python {settings.BASE_DIR}/manage.py apply_rule {rule.id}",
                            comment=retry_rule_comment)
                        job.minute.every(retry_after)
                        cron.write()
                else:
                    logger.debug(f"This was our {ordinal(attempt)} attempt ({ordinal(attempt-1)} retry)")

                # If this was one attempt too many, give up.
                # Technically "retries" are attempts *after* the first attempt, so use > instead of the >= comparison you might have expected.
                if int(attempt) > int(max_retry):
                    logger.warn(f"{attempt} is one failure too far!")
                    CronUtil.delete_retry_cron(rule.id)
                else:
                    logger.debug(f"attempt {attempt} vs max_retry {max_retry}")
            except Exception as e:
                logger.error(f"Got an exception: {e}")
        else:
            logger.debug("Not going to retry because retry rule is incomplete")

    @staticmethod
    def delete_retry_cron(rule_id):
        with advisory_lock(cron_lock_id) as acquired:
            cron = CronTab(user=getpass.getuser())
            retry_rule_comment = CronUtil.build_retry_rule_comment(rule_id)
            logger.info(f"removing all cronjobs with comment {retry_rule_comment}")
            cron.remove_all(comment=retry_rule_comment)
            cron.write()

    @staticmethod
    def delete_cron(rule):
        if sys.platform == "win32":
            return
        with advisory_lock(cron_lock_id) as acquired:
            cron = CronTab(user=getpass.getuser())
            cron.remove_all(comment="rule_{}".format(rule.id))
            cron.write()

    @staticmethod
    def delete_cron_intent(rule_id):
        if sys.platform == "win32":
            return
        with advisory_lock(cron_lock_id) as acquired:
            cron = CronTab(user=getpass.getuser())
            cron.remove_all(comment="intent_{}".format(rule_id))
            cron.write()

    @staticmethod
    def delete_all_crons():
        if sys.platform == "win32":
            return
        with advisory_lock(cron_lock_id) as acquired:
            cron = CronTab(user=getpass.getuser())
            cron.remove_all()
