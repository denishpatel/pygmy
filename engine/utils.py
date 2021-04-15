import os
import sys
import json
import getpass
import subprocess
from crontab import CronTab
from django.db.models import F
from django.utils import timezone
from engine.aws_wrapper import AWSData
from engine.postgres_wrapper import PostgresData
from engine.models import AllRdsInstanceTypes, AllEc2InstanceTypes, RDS, CRON, Rules, DAILY, Ec2DbInfo, EC2, \
    ExceptionData, DbCredentials
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
                job = cron.new(command="{0}/venv/bin/python {0}/manage.py apply_rule {1}".format(settings.BASE_DIR, rule.id), comment=retry_rule_comment)
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


def run_dns_script(instance, primary_ip):
    """
    Run dns script only when dns entry present
    """
    if sys.platform == "win32":
        return

    zone_name = instance.dns_entry.hosted_zone_name
    dns_name = instance.dns_entry.dns_name

    script_path = os.path.join(settings.BASE_DIR, "route-53-dns-change.sh")
    DB_CRED = DbCredentials.objects.get(description="AWS Secrets")
    env_var = dict({
        "AWS_ACCESS_KEY_ID": DB_CRED.user_name,
        "AWS_SECRET_ACCESS_KEY": DB_CRED.password
    })
    return subprocess.check_output(["sh", script_path, zone_name, dns_name, primary_ip], env=env_var)


class RuleUtils:

    @staticmethod
    def check_exception_date(rule_db):
        exception_date_data = ExceptionData.objects.get(exception_date=timezone.now().date())
        # Check existing cluster is present in exception or not
        for cluster in exception_date_data.clusters:
            if rule_db.cluster.id == cluster["id"]:
                msg = "{} is listed as exception date for this cluster. Hence not applying rule".format(
                    str(timezone.now().date()))
                raise Exception("Rule execution on Cluster: {} is excluded for date: {}".format(rule_db.cluster.name, timezone.now().date()))
        return True

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

        # Set Retry settings
        enableRetry = data.get("enableRetry", None)
        if enableRetry and enableRetry == "on":
            rules.update({
                "retry": dict({
                    "retry_after": data.get("retryAfter", 15),
                    "retry_max": data.get("retryMax", 3)
                })
            })

        rule_db.name = data.get("name", None)
        rule_db.action = data.get("action", None)
        rule_db.cluster_id = data.get("cluster_id", None)
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
        RuleUtils.create_reverse_rule(data, rule_db)
        return rule_db

    @staticmethod
    def create_reverse_rule(data, parent_rule):
        reverse_enable = data.get("enableReverse", None)
        if reverse_enable:
            typeTime = data.get("typeTime", None)
            reverse_action = data.get("reverse_action", None)

            # Create Reverse Rule
            reverse_rule = Rules()
            if parent_rule.child_rule.all().count() > 0:
                reverse_rule = parent_rule.child_rule.get()
            reverse_rule.name = format(parent_rule.name)
            reverse_rule.cluster = parent_rule.cluster
            reverse_rule.rule = dict({})
            reverse_rule.action = reverse_action
            reverse_rule.run_type = typeTime
            reverse_rule.parent_rule = parent_rule
            if typeTime.upper() == DAILY:
                reverse_rule.run_type = DAILY
                reverse_rule.run_at = data.get("reverseDailyTime", None)
            else:
                reverse_rule.run_type = CRON
                reverse_rule.run_at = data.get("reverseCronTime", None)
            reverse_rule.save()

            create_cron(reverse_rule)
        else:
            if parent_rule.child_rule.all().count() > 0:
                for rule in parent_rule.child_rule.all():
                    delete_cron(rule)
                    rule.delete()

    @classmethod
    def reverse_rule(cls, rule_db):
        secondaryNode = Ec2DbInfo.objects.filter(cluster=rule_db.cluster, isPrimary=False)

        # Check no of connection and average load on secondary node
        for db in secondaryNode:
            cls.reverseScale(db)

    @classmethod
    def apply_rule(cls, rule_db):
        rule_json = rule_db.rule
        ec2_type = rule_json.get("ec2_type")
        rds_type = rule_json.get("rds_type")

        secondaryNode = Ec2DbInfo.objects.filter(cluster=rule_db.cluster, isPrimary=False)
        primaryNode = Ec2DbInfo.objects.filter(cluster=rule_db.cluster, isPrimary=True)

        try:
            # Check no of connection and average load on secondary node
            for db in secondaryNode:
                db_conn = RuleUtils.create_connection(db)
                cls.checkReplicationLag(db_conn, rule_json)
                cls.checkConnections(db_conn, rule_json)
                if db.type == EC2:
                    cls.checkAverageLoad(db_conn, rule_json)
                else:
                    # TODO bridge in rds using cloudwatch metrics
                    # check avg load using cloudwatch metrics
                    pass

                # Scale down node
                RuleUtils.scaleDownNode(db, ec2_type, rds_type)

                # update the DNS
                if hasattr(db, "dns_entry"):
                    if primaryNode[0].type == "RDS":
                        run_dns_script(db, primaryNode[0].instance_object.dbEndpoint['Address'])
                    else:
                        run_dns_script(db, primaryNode[0].instance_object.publicDnsName)
        except Exception as e:
            set_retry_cron(rule_db)
            raise e

    @staticmethod
    def create_connection(db):
        if db.type == RDS:
            return PostgresData(db.instance_object.dbEndpoint["Address"], db.instance_object.masterUsername,
                                "postgres123", db.instance_object.dbName)
        else:
            return PostgresData(db.instance_object.publicDnsName, "pygmy", "pygmy", "postgres")

    @staticmethod
    def scaleDownNode(db, ec2_type, rds_type):
        RuleUtils.changeInstanceType(db, ec2_type, rds_type)
        # save last instance type in db after scale down for reverse rule
        if db.type == EC2:
            db.last_instance_type = db.instance_object.instanceType
        else:
            db.last_instance_type = db.instance_object.dbInstanceClass
        db.save()

    @staticmethod
    def reverseScale(db):
        if db.type == EC2:
            RuleUtils.changeInstanceType(db, db.last_instance_type, None)
        elif db.type == RDS:
            RuleUtils.changeInstanceType(db, None, db.last_instance_type)

    @staticmethod
    def changeInstanceType(db, ec2_type, rds_type):
        aws = AWSData()
        if db.type == EC2:
            aws.scale_ec2_instance(db.instance_id, ec2_type)
        elif db.type == RDS:
            db_parameter = db.instance_object.dBParameterGroups[0]['DBParameterGroupName']
            aws.scale_rds_instance(db.instance_id, rds_type, db_parameter)

    @staticmethod
    def checkReplicationLag(db_conn, rule_json):
        replicationLagRule = rule_json.get("replicationLag", None)
        if replicationLagRule:
            replicationLag = db_conn.get_replication_lag()
            print(replicationLag)
            return RuleUtils.checkValue(replicationLagRule, replicationLag, msg="Replication Lag")

    @staticmethod
    def checkConnections(db_conn, rule_json):
        rule = rule_json.get("checkConnection", None)
        if rule:
            activeConnections = db_conn.get_no_of_active_connections()
            print(activeConnections)
            return RuleUtils.checkValue(rule, activeConnections, msg="Check Connection")

    @staticmethod
    def checkAverageLoad(db_conn, rule_json):
        rule = rule_json.get("averageLoad", None)
        if rule:
            avgLoad = db_conn.get_system_load_avg()
            print(avgLoad)
            return RuleUtils.checkValue(rule, avgLoad, msg="Average load")

    @staticmethod
    def checkValue(rule, value, msg=None):
        result = False
        if rule.get("op") == "equal":
            result = value == int(rule.get("value"))
        elif rule.get("op") == "greater":
            result = value > int(rule.get("value"))
        elif rule.get("op") == "less":
            result = value < int(rule.get("value"))
        if not result:
            raise Exception("{} check failed".format(msg))
