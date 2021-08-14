import sys
from crontab import CronTab
import getpass
from django.conf import settings


class CronUtil:

    @staticmethod
    def create_cron(rule):
        cron = CronTab(user=getpass.getuser())
        cron.remove_all(comment="rule_{}".format(rule.id))
        job = cron.new(command="{0}/venv/bin/python {0}/manage.py apply_rule {1}".format(settings.BASE_DIR, rule.id),
                       comment="rule_{}".format(rule.id))

        # Run at
        time = rule.run_at.split(":")
        hour = time[0]
        minute = time[1]

        # Setup a cron
        if hour:
            job.hour.on(hour)
        if minute:
            job.minute.on(minute)
        cron.write()

    @staticmethod
    def set_retry_cron(rule):
        # Get Rule details
        rule_json = rule.rule
        retry_rule = rule_json.get("retry", None)

        if not retry_rule:
            return

        retry_after = retry_rule.get("retry_after")
        max_retry = retry_rule.get("retry_max")
        no_of_tries = retry_rule.get("no_of_tries", 0)

        if retry_after and max_retry:
            retry_rule_comment = "retry_rule_{}".format(rule.id)
            try:
                # Update Crontab jobs
                cron = CronTab(user=getpass.getuser())
                if no_of_tries == 0:
                    job = cron.new(
                        command="{0}/venv/bin/python {0}/manage.py apply_rule {1}".format(settings.BASE_DIR, rule.id),
                        comment=retry_rule_comment)
                    job.minute.every(retry_after)

                # Increase no of tries
                no_of_tries += 1
                if no_of_tries > int(max_retry):
                    print("remove all cron job")
                    no_of_tries = 0
                    cron.remove_all(comment=retry_rule_comment)
                cron.write()
            except Exception as e:
                print(e)

            # Update Rule json
            rule.rules = rule_json.update({
                "retry": dict({
                    "retry_after": retry_after,
                    "retry_max": max_retry,
                    "no_of_tries": no_of_tries
                })
            })
            rule.save()

    @staticmethod
    def delete_cron(rule):
        if sys.platform == "win32":
            return
        cron = CronTab(user=getpass.getuser())
        cron.remove_all(comment="rule_{}".format(rule.id))
        cron.write()

    @staticmethod
    def delete_all_crons():
        if sys.platform == "win32":
            return
        cron = CronTab(user=getpass.getuser())
        cron.remove_all()
