import getpass
import sys
from crontab import CronTab
from engine.models import AllRdsInstanceTypes, AllEc2InstanceTypes, RDS
from django.db.models import F
import json
from django.conf import settings


def get_instance_types(cluster_type):
    if cluster_type.upper() == RDS:
        types = list(AllRdsInstanceTypes.objects.all().values('instance_type').annotate(value=F('instance_type'),
                                                                                        data=F('instance_type')))
    else:
        types = list(AllEc2InstanceTypes.objects.all().values('instance_type').annotate(value=F('instance_type'),
                                                                                        data=F('instance_type')))
    return json.dumps(types)


def get_selection_list(query, table_col, value_col, data_col):
    data = list(query.values(table_col).annotate(value=F(value_col), data=F(data_col)))
    return json.dumps(data)


def create_cron(rule):
    if sys.platform == "win32":
        return

    cron = CronTab(user=getpass.getuser())
    cron.remove_all(comment="rule_{}".format(rule.id))
    job = cron.new(command="{0}/venv/bin/python {0}/manage.py apply_rule {1}".format(
        settings.BASE_DIR, rule.id), comment="rule_{}".format(rule.id))

    # job_2 = cron.new(command="{0}/venv/bin/python {0}/manage.py get_all_db_data".format(
    #     settings.BASE_DIR, rule.id), comment="rule_{}".format(rule.id))

    # Run at
    job.setall(rule.run_at)
    # time = rule.run_at.split(":")
    # hour = time[0]
    # minute = time[1]
    #
    # # Setup a cron
    # if hour:
    #     job.hour.on(hour)
    # if minute:
    #     job.minute.on(minute)
    cron.write()


def delete_cron(rule):
    if sys.platform == "win32":
        return

    cron = CronTab(user=getpass.getuser())
    cron.remove_all(comment="rule_{}".format(rule.id))

    cron.write()


def delete_all_crons():
    if sys.platform == "win32":
        return

    cron = CronTab(user=getpass.getuser())
    cron.remove_all()
