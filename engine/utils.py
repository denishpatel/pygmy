import getpass

from crontab import CronTab

from engine.models import AllRdsInstanceTypes, AllEc2InstanceTypes, RDS
from django.db.models import F
import json


def get_instance_types(cluster_type):
    if cluster_type.upper() == RDS:
        types = list(AllRdsInstanceTypes.objects.all().values('instance_type').annotate(value=F('instance_type'),
                                                                                        data=F('instance_type')))
    else:
        types = list(AllEc2InstanceTypes.objects.all().values('instance_type').annotate(value=F('instance_type'),
                                                                                        data=F('instance_type')))
    return json.dumps(types)


def create_cron(rule):
    cron = CronTab(user=getpass.getuser())
    cron.remove_all(comment="rule_{}".format(rule.id))
    job = cron.new(command="python manage.py apply_rule {}".format(rule.id), comment="rule_{}".format(rule.id))

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