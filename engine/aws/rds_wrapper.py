from engine.aws.aws_services import AWSServices
from engine.models import RdsInstances, Ec2DbInfo, ClusterInfo, RDS, AllRdsInstanceTypes, DbCredentials
from engine.postgres_wrapper import PostgresData
from django.conf import settings
from engine.singleton import Singleton
import logging
log = logging.getLogger("db")


class RDSService(AWSServices, metaclass=Singleton):
    rds_client_region_dict = dict()
    SERVICE_TYPE = RDS

    def __init__(self):
        super(RDSService, self).__init__()

    def get_all_regions(self):
        regions = self.ec2_client.describe_regions()

    def create_connection(self, db):
        credentials = DbCredentials.objects.get(name="rds")
        host = db.instance_object.dbEndpoint["Address"]
        username = db.instance_object.masterUsername
        db_name = db.instance_object.dbName
        password = credentials.password #"postgres123"
        return PostgresData(host, username, password, db_name)

    def check_instance_status(self, instance):
        response = self.rds_client.describe_db_instances(DBInstanceIdentifier=instance.dbInstanceIdentifier)
        self.save_data(response.get("DBInstances")[0])
        return response

    def check_instance_running(self, data):
        if data.get("DBInstances"):
            status = data.get("DBInstances")[0]["DBInstanceStatus"]
            instance = data.get("DBInstances")[0]
            # print(instance)
            if status == "available":
                return dict({
                    "PubliclyAccessible": instance.get("PubliclyAccessible"),
                    "StatusInfo": instance.get("StatusInfo"),
                    "Endpoint": instance.get("Endpoint")
                })
        return None

    def start_instance(self, instance):
        self.rds_client.start_db_instance(DBInstanceIdentifier=instance.dbInstanceIdentifier)
        return self.wait_till_status_up(instance)

    def get_instances(self):
        all_instances = dict()
        filters = [{
            'Name': 'engine',
            'Values': [
                'postgres',
            ]},
        ]

        for region in AWSServices.get_enabled_regions():
            # First describe instance
            all_pg_instances = self.rds_client_region_dict[region].describe_db_instances(
                Filters=filters,
                MaxRecords=100
            )

            while True:
                for instance in all_pg_instances.get("DBInstances", []):
                    slave_identifier = instance.get("ReadReplicaSourceDBInstanceIdentifier", None)
                    rds = self.save_data(instance, region)
                    db_info, created = Ec2DbInfo.objects.get_or_create(instance_id=rds.dbInstanceIdentifier, type=RDS)
                    db_info.instance_object = rds
                    if slave_identifier is None:
                        db_info.isPrimary = True
                        db_info.cluster = self.get_or_create_cluster(instance, rds.dbInstanceIdentifier, databaseName=rds.dbName)
                    else:
                        cluster, created = ClusterInfo.objects.get_or_create(primaryNodeIp=slave_identifier, type=RDS)
                        db_info.cluster = cluster
                        db_info.isPrimary = False
                    db_info.isConnected = True
                    db_info.last_instance_type = rds.dbInstanceClass
                    db_info.save()

                if all_pg_instances.get("NextToken", None) is None:
                    break

                all_pg_instances = self.rds_client.describe_db_instances(
                    Filters=filters,
                    MaxResults=100,
                    NextToken=all_pg_instances.get("NextToken")
                )

        self.update_last_sync_time()
        return all_instances

    def get_instance_types(self):
        all_instance_types = []
        describe_instance_type_resp = self.rds_client.describe_orderable_db_instance_options(
            Engine='postgres',
            MaxRecords=100
        )

        while True:
            all_instance_types.extend(describe_instance_type_resp.get("OrderableDBInstanceOptions"))

            # For handling pagination
            if describe_instance_type_resp.get("Marker", None) is None:
                break

            describe_instance_type_resp = self.rds_client.describe_orderable_db_instance_options(
                Engine='postgres',
                MaxRecords=100,
                Marker=describe_instance_type_resp.get("Marker")
            )

        return all_instance_types

    @classmethod
    def get_tag_map(cls, instance):
        return dict((tag['Key'], tag['Value'].lower()) for tag in instance.get("TagList"))

    def save_data(self, instance, region=settings.DEFAULT_REGION):
        rds = RdsInstances()
        rds.dbInstanceIdentifier = instance["DBInstanceIdentifier"]
        rds.region = region
        rds.dbInstanceClass = instance["DBInstanceClass"]
        rds.dbName = instance["DBName"]
        rds.engine = instance["Engine"]
        rds.dbInstanceStatus = instance["DBInstanceStatus"]
        rds.dbEndpoint = instance["Endpoint"]
        rds.dbStorage = instance["AllocatedStorage"]
        rds.dbVpcSecurityGroups = instance["VpcSecurityGroups"]
        rds.masterUsername = instance["MasterUsername"]
        rds.preferredBackupWindow = instance["PreferredBackupWindow"]
        rds.availabilityZone = instance.get("AvailabilityZone", "")
        rds.dBParameterGroups = instance["DBParameterGroups"]
        rds.engineVersion = instance["EngineVersion"]
        rds.licenseModel = instance["LicenseModel"]
        rds.publiclyAccessible = instance["PubliclyAccessible"]
        rds.tagList = instance["TagList"]
        rds.save()
        return rds

    def scale_instance(self, instance, new_instance_type, fallback_instances=None):
        """
            scale up and down the rds instance
        """
        db_instance_id = instance.dbInstanceIdentifier
        db_instance_type = new_instance_type
        db_parameter_group = instance.dBParameterGroups[0]['DBParameterGroupName']

        try:
            self.__scale_instance(db_instance_id, db_instance_type, db_parameter_group)
            return True
        except Exception as e:
            print(str(e))
            for fallback_instance in fallback_instances:
                try:
                    self.__scale_instance(db_instance_id, fallback_instance, db_parameter_group)
                    return True
                except Exception as e:
                    log.error("Failed update instance type ", fallback_instance)
        return False

    def __scale_instance(self, db_instance_id, db_instance_type, db_parameter_group):
        self.rds_client.modify_db_instance(
            DBInstanceIdentifier=db_instance_id,
            DBInstanceClass=db_instance_type,
            DBParameterGroupName=db_parameter_group,
            ApplyImmediately=True
        )
        waiter = self.rds_client.get_waiter("db_instance_available")
        waiter.wait(DBInstanceIdentifier=db_instance_id)

    def copy_pygmy_parameter_group(self, source_parameter_group_name):
        """
        copy source db parameter group name and create new parameter group
        """
        try:
            # if pygmy parameter already created!
            response = self.rds_client.describe_db_parameter_groups(
                DBParameterGroupName="{0}-pygmy".format(source_parameter_group_name)
            )
            return True
        except self.rds_client.exceptions.DBParameterGroupNotFoundFault:
            # create if not present
            self.rds_client.copy_db_parameter_group(
                SourceDBParameterGroupIdentifier=source_parameter_group_name,
                TargetDBParameterGroupIdentifier="{0}-pygmy".format(source_parameter_group_name),
                TargetDBParameterGroupDescription='Parameter group by pygmy'
            )

            response = self.rds_client.modify_db_parameter_group(
                DBParameterGroupName="{0}-pygmy".format(source_parameter_group_name),
                Parameters=[
                    {
                        'ApplyMethod': 'immediate',
                        'ParameterName': 'shared_buffers',
                        'ParameterValue': '{DBInstanceClassMemory/32768}',
                    },
                    {
                        'ApplyMethod': 'immediate',
                        'ParameterName': 'max_connections',
                        'ParameterValue': 'LEAST({DBInstanceClassMemory/9531392},5000)',
                    }
                ]
            )
            print(response)
            return True
        except Exception as e:
            print(str(e))
            return False

    def save_instance_types(self):
        try:
            all_instances = self.get_instance_types()
            if AllRdsInstanceTypes.objects.count() != len(all_instances):
                for instance in all_instances:
                    try:
                        inst = AllRdsInstanceTypes.objects.get(instance_type=instance["DBInstanceClass"],
                                                               engine=instance["Engine"],
                                                               engine_version=instance["EngineVersion"])
                    except AllRdsInstanceTypes.DoesNotExist:
                        arit = AllRdsInstanceTypes()
                        arit.save_instance_types(instance)
        except Exception as e:
            print(str(e))
            return
