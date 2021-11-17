import json
import logging
import time
from django.db.models import F
from engine.models import EC2, SCALE_DOWN, SCALE_UP, Ec2DbInfo, AllRdsInstanceTypes, AllEc2InstanceTypes
from engine.aws.aws_utils import AWSUtil
from engine.rules.cronutils import CronUtil
logger = logging.getLogger(__name__)


class DbHelper:
    conn = None

    def __init__(self, db: Ec2DbInfo):
        self.db_info = db
        self.type = db.type
        self.aws = AWSUtil.get_aws_service(db.type)
        self.table = EC2DBHelper if db.type == EC2 else RDSDBHelper
        self.instance = db.instance_object

    def __repr__(self):
        return "<DbHelper db_info:%s type:%s aws:%s table:%s instance:%s>" % (self.db_info, self.type, self.aws, self.table, self.instance)

    def new_db_conn(self, expect_errors=False):
        return self.db_conn(force=True, expect_errors=expect_errors)

    def db_conn(self, force=False, expect_errors=False):
        if force or not self.conn:
            self.conn = self.aws.create_connection(self.db_info, expect_errors)
        return self.conn

    @classmethod
    def from_id(cls, instance_id):
        instance = Ec2DbInfo.objects.get(id=instance_id)
        return cls(instance)

    def wait_till_replica_streaming(self):
        logger.info(f"Waiting for db on instance {self.instance.instanceId} to come alive")
        is_alive = False
        while is_alive is False:
            try:
                logging.debug("Checking if db is alive")
                is_alive = self.new_db_conn(expect_errors=True).is_alive(expect_errors=True)
                time.sleep(5)
            except Exception as e:
                logger.info("Replica not yet accepting connections")
                time.sleep(5)

        logger.info(f"Waiting till db on instance {self.instance.instanceId} has begun streaming")
        while self.db_conn().get_streaming_status() is False:
            logger.info("Replica not yet streaming; sleeping for 5 seconds")
            time.sleep(5)

    def check_replication_lag(self, rule_json, any_conditions):
        replication_lag_rule = rule_json.get("replicationLag", None)
        if replication_lag_rule:
            replication_lag = self.db_conn().get_replication_lag()
            if replication_lag is None:
                raise Exception("Could not get replication lag")
            else:
                logger.info("Replication lag check threshold is {}, actual lag is {}".format(replication_lag_rule.get("value"),
                            replication_lag))
                return self._check_value(replication_lag_rule, replication_lag, msg="Replication Lag")
        else:
            # If we haven't bothered to define a check condition for this metric,
            # then if we are running our checks logically or'd, we should return False,
            # because in that case we care very much if any of the things we *did* define succeeds.
            # If we are running logically and'd, we are instead likely looking for things that fail,
            # so when running that way, return True in the absence of a definition.
            if any_conditions:
                raise Exception("No replication lag clause defined and running checks in ANY mode")
        return True

    def check_average_load(self, rule_json, any_conditions, offset=0):
        rule = rule_json.get("averageLoad", None)
        if rule:
            avg_load = self.db_conn().get_system_load_avg()
            if avg_load is None:
                raise Exception("Could not get system load avg")
            else:
                logger.info(f"Avg load check threshold is {rule.get('value')}, actual is {avg_load}, offset {offset}")
                return self._check_value(rule, avg_load + offset, msg="Average load")
        else:
            # If we haven't bothered to define a check condition for this metric,
            # then if we are running our checks logically or'd, we should return False,
            # because in that case we care very much if any of the things we *did* define succeeds.
            # If we are running logically and'd, we are instead likely looking for things that fail,
            # so when running that way, return True in the absence of a definition.
            if any_conditions:
                raise Exception("No average load clause defined and running checks in ANY mode")
        return True

    def check_connections(self, rule_json, any_conditions, connections=None):
        rule = rule_json.get("checkConnection", None)
        if rule:
            if connections is None:
                active_connections = self.db_conn().count_all_active_connections()
            else:
                active_connections = connections

            if active_connections is None:
                raise Exception("Could not get active connection count")
            else:
                logger.info("Active connection count threshold is {}, actual count is {}".format(rule.get("value"), active_connections))
                return self._check_value(rule, active_connections, msg="Check Connection")
        else:
            # If we haven't bothered to define a check condition for this metric,
            # then if we are running our checks logically or'd, we should return False,
            # because in that case we care very much if any of the things we *did* define succeeds.
            # If we are running logically and'd, we are instead likely looking for things that fail,
            # so when running that way, return True in the absence of a definition.
            if any_conditions:
                raise Exception("No connection check clause defined and running checks in ANY mode")
        return True

    def _check_value(self, rule, value, msg=None):
        result = False
        if rule.get("op") == "equal":
            result = value == int(rule.get("value"))
            logger.debug(f"is {value} == {rule.get('value')}? {result}")
        elif rule.get("op") == "greater":
            result = value > int(rule.get("value"))
            logger.debug(f"is {value} > {rule.get('value')}? {result}")
        elif rule.get("op") == "less":
            result = value < int(rule.get("value"))
            logger.debug(f"is {value} < {rule.get('value')}? {result}")
        if not result:
            raise Exception("{} check failed".format(msg))
        return result

    def get_supported_types(self):
        return self.table.get_instances_types()

    def count_user_connections(self, users):
        return self.db_conn().count_specific_active_connections(users)

    def update_instance_type(self, instance_type, rule_id, fallback_instances=[]):
        if instance_type == self.instance.instanceType:
            logger.info(f"Not going to change instance type because {self.instance.instanceType} == {instance_type}")
            return

        logger.debug(f"changing instance {self.instance.instanceId} from {self.instance.instanceType} to {instance_type}")

        # Mark our intent to resize an cluster member
        CronUtil.create_cron_intent(rule_id, self.instance.instanceId)

        self.aws.scale_instance(self.instance, instance_type, fallback_instances)

        # Remove our intent, now that it is over.
        # (The rule might still be in progress, but if we were to restart at this moment it should be close enough to idempotent.)
        CronUtil.delete_cron_intent(rule_id)

        logger.debug(f"Scaling {self.instance.instanceId} complete.")

    def get_endpoint_address(self):
        return self.table.get_endpoint_address(self.instance)

    def get_system_load_avg(self):
        return self.db_conn().get_system_load_avg()


class EC2DBHelper:
    def __repr__(self):
        return "<EC2DBHelper>"

    @staticmethod
    def get_instances_types():
        return json.dumps(list(AllEc2InstanceTypes.objects.all().values('instance_type').annotate(
            value=F('instance_type'), data=F('instance_type'))))

    @staticmethod
    def get_endpoint_address(instance):
        if instance.publicIpAddress is None or instance.publicIpAddress == '':
            logger.debug(f"returning private address {instance.privateIpAddress}")
            return instance.privateIpAddress
        else:
            logger.debug(f"returning public address {instance.publicIpAddress}")
            return instance.publicIpAddress


class RDSDBHelper:
    def __repr__(self):
        return "<RDSDBHelper>"

    @staticmethod
    def get_instances_types():
        return json.dumps(list(AllRdsInstanceTypes.objects.all().values('instance_type').annotate(
            value=F('instance_type'), data=F('instance_type'))))

    @staticmethod
    def get_endpoint_address(instance):
        return instance.dbEndpoint["Address"]
