import json
import logging
from django.db.models import F
from engine.models import EC2, SCALE_DOWN, SCALE_UP, Ec2DbInfo, AllRdsInstanceTypes, AllEc2InstanceTypes
from engine.aws.aws_utils import AWSUtil
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

    def db_conn(self):
        if not self.conn:
            self.conn = self.aws.create_connection(self.db_info)
        return self.conn

    @classmethod
    def from_id(cls, instance_id):
        instance = Ec2DbInfo.objects.get(id=instance_id)
        return cls(instance)

    def check_replication_lag(self, rule_json):
        replication_lag_rule = rule_json.get("replicationLag", None)
        if replication_lag_rule:
            replication_lag = self.db_conn().get_replication_lag()
            logger.info("Replication lag to check {} actual {}".format(replication_lag_rule.get("value"),
                                                                       replication_lag))
            return self._check_value(replication_lag_rule, replication_lag, msg="Replication Lag")

    def check_average_load(self, rule_json):
        rule = rule_json.get("averageLoad", None)
        if rule:
            avg_load = self.db_conn().get_system_load_avg()
            logger.info("Avg load to check {} actual {}".format(rule.get("value"), avg_load))
            return self._check_value(rule, avg_load, msg="Average load")

    def check_connections(self, rule_json):
        rule = rule_json.get("checkConnection", None)
        if rule:
            active_connections = self.db_conn().get_no_of_active_connections()
            logger.info("No of active connections to check {} actual {}".format(rule.get("value"), active_connections))
            return self._check_value(rule, active_connections, msg="Check Connection")

    def _check_value(self, rule, value, msg=None):
        result = False
        if rule.get("op") == "equal":
            result = value == int(rule.get("value"))
        elif rule.get("op") == "greater":
            result = value > int(rule.get("value"))
        elif rule.get("op") == "less":
            result = value < int(rule.get("value"))
        if not result:
            raise Exception("{} check failed".format(msg))

    def scale_down_instance(self, instance_type):
        logger.info(f"scaling down instance {self.id} to {instance_type}")
        self.update_instance_type(instance_type, SCALE_DOWN)

    def scale_up_instance(self, instance_type):
        logger.info(f"scaling up instance {self.id} to {instance_type}")
        self.update_instance_type(instance_type, SCALE_UP)

    def get_supported_types(self):
        return self.table.get_instances_types()

    def get_no_of_connections(self, users):
        return self.db_conn().get_user_open_connections_postgres(users)

    def update_instance_type(self, instance_type, fallback_instances=[]):
        if instance_type == self.db_info.id:
            logger.info(f"Not going to change instance type because {self.db_info.id} == {instance_type}")
            return

        logger.info(f"changing instance {self.db_info.id} to {instance_type}")
        self.aws.scale_instance(self.instance, instance_type, fallback_instances)
        # wait till instance status get up
        logger.info(f"scaling complete. Waiting till instance {self.instance} is up")
        status = self.aws.wait_till_status_up(self.instance)
        if not status:
            status = self.aws.start_instance(self.instance)

    def get_endpoint_address(self):
        return self.table.get_endpoint_address(self.instance)

    def get_system_load_avg(self):
        return self.db_conn().get_system_load_avg()


class EC2DBHelper:
    def __repr__(self):
        return "<EC2DBHelper>"

    @staticmethod
    def get_instances_types():
        return json.dumps(list(AllEc2InstanceTypes.objects.all().values('instance_type').annotate(value=F('instance_type'),
                                                                                        data=F('instance_type'))))

    @staticmethod
    def get_endpoint_address(instance):
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
