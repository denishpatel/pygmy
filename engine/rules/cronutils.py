from crontab import CronTab
import getpass


def create_cron(rule):
    cron = CronTab(user=getpass.getuser())
    cron.remove_all(comment="rule_{}".format(rule.id))
    job = cron.new(command="python manage.py props_update", comment="rule_{}".format(rule.id))

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
