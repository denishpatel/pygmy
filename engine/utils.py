import getpass
import sys
from crontab import CronTab
from engine.models import AllRdsInstanceTypes, AllEc2InstanceTypes, RDS, CRON, Rules, DAILY
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

    if rule.run_type == CRON:
        # Run at
        job.setall(rule.run_at)
    else:
        time = rule.run_at.split(":")
        hour = time[0]
        minute = time[1]

        # Setup a cron
        if hour:
            job.hour.on(hour)
        if minute:
            job.minute.on(minute)
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


class RuleUtils:

    @staticmethod
    def add_rule_db(data, rule_db=None):
        if not rule_db:
            rule_db = Rules()

        # name, rule_type, cluster_id, time, ec2_type, rds_type
        rules = {
            "ec2_type": data.get("ec2_type", None),
            "rds_type": data.get("rds_type", None)
        }

        # Set replication check
        enableReplicationLag = data.get("enableReplicationLag", None)
        if enableReplicationLag and enableReplicationLag == "on":
            rules.update({
                "replicationLag": dict({
                    "op": data.get("selectReplicationLagOp", None),
                    "value": data.get("replicationLag", None)
                })
            })

        # Set Connection check
        enableCheckConnection = data.get("enableCheckConnection", None)
        if enableCheckConnection and enableCheckConnection == "on":
            rules.update({
                "checkConnection": dict({
                    "op": data.get("selectCheckConnectionOp", None),
                    "value": data.get("checkConnection", None)
                })
            })

        # Set Average Load check
        enableAverageLoad = data.get("enableAverageLoad", None)
        if enableAverageLoad and enableAverageLoad == "on":
            rules.update({
                "averageLoad": dict({
                    "op": data.get("selectAverageLoadOp", None),
                    "value": data.get("averageLoad", None)
                })
            })

        rule_db.name = data.get("name", None)
        rule_db.action = data.get("action", None)
        rule_db.cluster_id = data.get("cluster_id", None)
        # enableTime = data.get("enableTime", False)
        typeTime = data.get("typeTime", None)

        # Set time
        if typeTime.upper() == DAILY:
            rule_db.run_type = DAILY
            rule_db.run_at = data.get("dailyTime", None)
        else:
            rule_db.run_type = CRON
            rule_db.run_at = data.get("cronTime", None)

        rule_db.rule = rules
        rule_db.save()
        create_cron(rule_db)