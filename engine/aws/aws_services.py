import time
import boto3
import datetime
from django.conf import settings
from django.utils import timezone
from webapp.models import Settings, AWS_REGION
from webapp.models import Settings as SettingsModal
from engine.models import AllEc2InstancesData, RdsInstances, ClusterInfo, EC2, RDS, Ec2DbInfo, DbCredentials


class AWSServices:
    ec2_client_region_dict = dict()
    rds_client_region_dict = dict()
    cloudwatch_client_region_dict = dict()
    SERVICE_TYPE = ""
    """
    Environment Variables to be set
        - AWS_ACCESS_KEY_ID
        - AWS_SECRET_ACCESS_KEY
        - AWS_REGION
    """
    def __init__(self):
        cred = DbCredentials.objects.get(name="aws")
        self.aws_session = boto3.Session(aws_access_key_id=cred.user_name, aws_secret_access_key=cred.password)
        self.ec2_client = self.aws_session.client('ec2', region_name=settings.DEFAULT_REGION)
        self.rds_client = self.aws_session.client('rds', region_name=settings.DEFAULT_REGION)
        for region in self.ec2_client.describe_regions()["Regions"]:
            region_name = region["RegionName"]
            self.ec2_client_region_dict[region_name] = self.aws_session.client('ec2', region_name=region_name)
            self.rds_client_region_dict[region_name] = self.aws_session.client('rds', region_name=region_name)
            self.cloudwatch_client_region_dict[region_name] = self.aws_session.client('cloudwatch', region_name=region_name)

    @staticmethod
    def get_enabled_regions():
        regions = [setting.description for setting in Settings.objects.filter(type=AWS_REGION, value="True").all() ]
        return regions

    def check_instance_status(self, instance_id):
        pass

    def check_instance_running(self, data):
        pass

    def get_tag_map(self, instance):
        pass

    def wait_till_status_up(self, instance):
        # TODO check streaming status after we confirm that its running.
        # TODO To be run on replica
        try:
            for i in range(0, 6):
                data = self.check_instance_status(instance)
                status = self.check_instance_running(data)
                if status:
                    return status
                time.sleep(20)
        except Exception as e:
            print(str(e))
            pass
        return None

    def update_last_sync_time(self):
        # Settings update
        setting = SettingsModal.objects.get(name__iexact=self.SERVICE_TYPE)
        setting.last_sync = timezone.now()
        setting.save()

    def get_cluster_name(self, tag_map):
        project = tag_map.get(settings.EC2_INSTANCE_PROJECT_TAG_KEY_NAME, None)
        environment = tag_map.get(settings.EC2_INSTANCE_ENV_TAG_KEY_NAME, None)
        cluster = tag_map.get(settings.EC2_INSTANCE_CLUSTER_TAG_KEY_NAME, None)
        print("Tag values project:{} environment:{} cluster:{}".format(project, environment, cluster))
        if project and environment and cluster:
            return "{}-{}-{}".format(project, environment, cluster)
        else:
            return None

    def get_or_create_cluster(self, instance, primary_node_ip):
        cluster, created = ClusterInfo.objects.get_or_create(primaryNodeIp=primary_node_ip, type=self.SERVICE_TYPE)
        if created:
            cluster_name = self.get_cluster_name(self.get_tag_map(instance))
            print("Cluster name ", cluster_name)
            if cluster_name:
                cluster.name = cluster_name
                cluster.save()
        return cluster

    def get_rds_cloudwatch_metrics(self):
        response = self.cloudwatch_client.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='CPUUtilization',
            Dimensions=[
                {
                    'Name': 'DBInstanceIdentifier',
                    'Value': 'postgres-replica'
                },
            ],
            StartTime=timezone.now() - datetime.timedelta(hours=1),
            EndTime=timezone.now(),
            Period=900,
            Statistics=[
                'Average',
            ]
        )
        return response



    # def check_instance_status(self, instance_id, instance_type):
    #     if instance_type == "RDS":
    #         response = self.rds_client.describe_db_instances(DBInstanceIdentifier=instance_id)
    #         self.save_rds_data(response.get("DBInstances")[0])
    #         return response
    #     else:
    #         response = self.ec2_client.describe_instances(InstanceIds=[instance_id])
    #         self.save_ec2_data(response.get("Reservations")[0]["Instances"][0])
    #         return response

    # def check_instance_running(self, data):
    #     # check is it EC2 response data
    #     if data.get("Reservations"):
    #         instance = data.get("Reservations")[0]["Instances"][0]
    #         state = instance["State"]
    #         if state.get("Code") == 16:
    #             return dict({
    #                 "PublicDnsName": instance.get("PublicDnsName"),
    #                 "PublicIpAddress": instance.get("PublicIpAddress"),
    #                 "PrivateDnsName": instance.get("PrivateDnsName"),
    #                 "PrivateIpAddress": instance.get("PrivateIpAddress"),
    #                 "State": state
    #             })
    #     # check status of RDS response data
    #     if data.get("DBInstances"):
    #         status = data.get("DBInstances")[0]["DBInstanceStatus"]
    #         instance = data.get("DBInstances")[0]
    #         # print(instance)
    #         if status == "available":
    #             return dict({
    #                 "PubliclyAccessible": instance.get("PubliclyAccessible"),
    #                 "StatusInfo": instance.get("StatusInfo"),
    #                 "Endpoint": instance.get("Endpoint")
    #             })
    #     return None

    # def wait_till_rds_status_up(self, instance_id):
    #     return self.wait_till_status_up(instance_id, "RDS")


    # def start_instance(self, instance_id, instance_type="EC2"):
    #     if instance_type == "RDS":
    #         self.rds_client.start_db_instance(DBInstanceIdentifier=instance_id)
    #     else:
    #         self.ec2_client.start_instances(InstanceIds=[instance_id])
    #     # fetch instance details after start
    #     return self.wait_till_status_up(instance_id, instance_type)

    # def describe_rds_instances(self):
    #     all_instances = dict()
    #     filters = [{
    #         'Name': 'engine',
    #         'Values': [
    #             'postgres',
    #         ]},
    #     ]
    #
    #     for region in AwsSync.get_enabled_regions():
    #         # First describe instance
    #         all_pg_instances = self.rds_client_region_dict[region].describe_db_instances(
    #             Filters=filters,
    #             MaxRecords=100
    #         )
    #
    #         while True:
    #             for instance in all_pg_instances.get("DBInstances", []):
    #                 slave_identifier = instance.get("ReadReplicaSourceDBInstanceIdentifier", None)
    #                 rds = self.save_rds_data(instance, region)
    #                 db_info, created = Ec2DbInfo.objects.get_or_create(instance_id=rds.dbInstanceIdentifier, type=RDS)
    #                 db_info.instance_object = rds
    #                 if slave_identifier is None:
    #                     db_info.isPrimary = True
    #                     db_info.cluster = self.get_or_create_cluster(instance, rds.dbInstanceIdentifier, cluster_type=RDS)
    #                 else:
    #                     cluster, created = ClusterInfo.objects.get_or_create(primaryNodeIp=slave_identifier, type=RDS)
    #                     db_info.cluster = cluster
    #                     db_info.isPrimary = False
    #                 db_info.isConnected = True
    #                 db_info.last_instance_type = rds.dbInstanceClass
    #                 db_info.save()
    #
    #             if all_pg_instances.get("NextToken", None) is None:
    #                 break
    #
    #             all_pg_instances = self.rds_client.describe_db_instances(
    #                 Filters=filters,
    #                 MaxResults=100,
    #                 NextToken=all_pg_instances.get("NextToken")
    #             )
    #
    #     # Settings update
    #     setting = SettingsModal.objects.get(name="rds")
    #     setting.last_sync = timezone.now()
    #     setting.save()
    #     return all_instances

    # def describe_ec2_instances(self):
    #     all_instances = dict()
    #     TAG_KEY_NAME = SettingsModal.objects.get(name="EC2_INSTANCE_POSTGRES_TAG_KEY_NAME")
    #     TAG_KEY_VALUE = SettingsModal.objects.get(name="EC2_INSTANCE_POSTGRES_TAG_KEY_VALUE")
    #     filters = [{
    #         'Name': 'tag:{}'.format(TAG_KEY_NAME.value),
    #         'Values': [TAG_KEY_VALUE.value,]
    #     }]
    #
    #     # First describe instance
    #     for region in AwsSync.get_enabled_regions():
    #         all_pg_ec2_instances = self.ec2_client_region_dict[region].describe_instances(
    #             #Filters=filters,
    #             MaxResults=200
    #         )
    #
    #         while True:
    #             # For handling pagination
    #             for reservation in all_pg_ec2_instances.get("Reservations", []):
    #                 for instance in reservation.get("Instances", []):
    #                     all_instances[instance["InstanceId"]] = dict({
    #                         "instance_id": instance["InstanceId"],
    #                         "region": region,
    #                         "instance_type": instance["InstanceType"],
    #                         "image_id": instance["ImageId"],
    #                         "state": instance["State"],
    #                         "vpc_id": instance["VpcId"],
    #                         "availability_zone": instance["Placement"]["AvailabilityZone"],
    #                         "ip": dict({
    #                             "private_ip": instance["PrivateIpAddress"],
    #                             "public_ip": instance.get("PublicIpAddress", "")
    #                         }),
    #                         "tags": instance["Tags"],
    #                         "launch_time": instance["LaunchTime"]
    #                     })
    #                     self.save_ec2_data(instance, region=region)
    #
    #             if all_pg_ec2_instances.get("NextToken", None) is None:
    #                 break
    #
    #             all_pg_ec2_instances = self.ec2_client.describe_instances(
    #                 Filters=filters,
    #                 MaxResults=200,
    #                 NextToken=all_pg_ec2_instances.get("NextToken")
    #             )
    #
    #     # Settings update
    #     setting = SettingsModal.objects.get(name="ec2")
    #     setting.last_sync = timezone.now()
    #     setting.save()
    #
    #     # Update Cluster Info
    #     for instance in AllEc2InstancesData.objects.all():
    #         self.process_ec2_cluster_info(instance)
    #     return all_instances

    # def describe_ec2_instance_types(self, **kwargs):
    #     all_instance_types = []
    #     describe_instance_type_resp = self.ec2_client.describe_instance_types(MaxResults=100, **kwargs)
    #     while True:
    #         all_instance_types.extend(describe_instance_type_resp.get("InstanceTypes"))
    #
    #         # For handling pagination
    #         if describe_instance_type_resp.get("NextToken", None) is None:
    #             break
    #
    #         describe_instance_type_resp = self.ec2_client.describe_instance_types(
    #             MaxResults=100,
    #             NextToken=describe_instance_type_resp.get("NextToken")
    #         )
    #
    #     return all_instance_types

    # def describe_rds_instance_types(self):
    #     all_instance_types = []
    #     describe_instance_type_resp = self.rds_client.describe_orderable_db_instance_options(
    #         Engine='postgres',
    #         MaxRecords=100
    #     )
    #
    #     while True:
    #         all_instance_types.extend(describe_instance_type_resp.get("OrderableDBInstanceOptions"))
    #
    #         # For handling pagination
    #         if describe_instance_type_resp.get("Marker", None) is None:
    #             break
    #
    #         describe_instance_type_resp = self.rds_client.describe_orderable_db_instance_options(
    #             Engine='postgres',
    #             MaxRecords=100,
    #             Marker=describe_instance_type_resp.get("Marker")
    #         )
    #
    #     return all_instance_types

    # def save_ec2_data(self, instance, region=settings.DEFAULT_REGION):
    #     try:
    #         db = AllEc2InstancesData.objects.get(instanceId=instance["InstanceId"], region=region)
    #     except AllEc2InstancesData.DoesNotExist:
    #         db = AllEc2InstancesData()
    #         db.instanceId = instance["InstanceId"]
    #         db.region = region
    #     db.name = next((tag["Value"] for tag in instance["Tags"] if tag["Key"] == "Name"), None)
    #     db.instanceType = instance["InstanceType"]
    #     db.keyName = instance["KeyName"]
    #     db.launchTime = instance["LaunchTime"]
    #     db.availabilityZone = instance["Placement"]["AvailabilityZone"]
    #     db.privateDnsName = instance["PrivateDnsName"]
    #     db.privateIpAddress = instance["PrivateIpAddress"]
    #     db.publicDnsName = instance["PublicDnsName"]
    #     db.publicIpAddress = instance.get("PublicIpAddress", "")
    #     db.state = instance["State"]
    #     db.vpcId = instance["VpcId"]
    #     db.subnetId = instance["SubnetId"]
    #     db.architecture = instance["Architecture"]
    #     db.blockDeviceMapping = instance["BlockDeviceMappings"]
    #     db.ebsOptimized = instance["EbsOptimized"]
    #     db.securityGroups = instance["SecurityGroups"]
    #     db.tags = instance["Tags"]
    #     db.virtualizationType = instance["VirtualizationType"]
    #     db.cpuOptions = instance.get("CpuOptions", {})
    #     db.save()

    # @staticmethod
    # def save_rds_data(instance, region=settings.DEFAULT_REGION):
    #     rds = RdsInstances()
    #     rds.dbInstanceIdentifier = instance["DBInstanceIdentifier"]
    #     rds.region = region
    #     rds.dbInstanceClass = instance["DBInstanceClass"]
    #     rds.dbName = instance["DBName"]
    #     rds.engine = instance["Engine"]
    #     rds.dbInstanceStatus = instance["DBInstanceStatus"]
    #     rds.dbEndpoint = instance["Endpoint"]
    #     rds.dbStorage = instance["AllocatedStorage"]
    #     rds.dbVpcSecurityGroups = instance["VpcSecurityGroups"]
    #     rds.masterUsername = instance["MasterUsername"]
    #     rds.preferredBackupWindow = instance["PreferredBackupWindow"]
    #     rds.availabilityZone = instance.get("AvailabilityZone", "")
    #     rds.dBParameterGroups = instance["DBParameterGroups"]
    #     rds.engineVersion = instance["EngineVersion"]
    #     rds.licenseModel = instance["LicenseModel"]
    #     rds.publiclyAccessible = instance["PubliclyAccessible"]
    #     rds.tagList = instance["TagList"]
    #     rds.save()
    #     return rds

    # def get_ec2_db_info(self, ipAddress):
    #     pass

    # def scale_rds_instance(self, db_instance_id, db_instance_type, db_parameter_group, apply_immediately=True):
        # """
        # scale up and down the rds instance
        # """
        # try:
        #     self.rds_client.modify_db_instance(
        #         DBInstanceIdentifier=db_instance_id,
        #         DBInstanceClass=db_instance_type,
        #         DBParameterGroupName=db_parameter_group,
        #         ApplyImmediately=apply_immediately
        #     )
        #     return True
        # except Exception as e:
        #     print(str(e))
        #     return False

    # def scale_ec2_instance(self, ec2_instance_id, ec2_instance_type, previous_instance_type):
    #     """
    #     scale up and down the ec2 instances
    #     """
    #     try:
    #         # stop the instance
    #         self.ec2_client.stop_instances(InstanceIds=[ec2_instance_id])
    #         waiter = self.ec2_client.get_waiter('instance_stopped')
    #         waiter.wait(InstanceIds=[ec2_instance_id])
    #
    #         # Change the instance type
    #         self.ec2_client.modify_instance_attribute(InstanceId=ec2_instance_id, Attribute='instanceType',
    #                                                   Value=ec2_instance_type)
    #
    #         # Start the instance
    #         self.ec2_client.start_instances(InstanceIds=[ec2_instance_id])
    #         waiter = self.ec2_client.get_waiter('instance_running')
    #         waiter.wait(InstanceIds=[ec2_instance_id])
    #         return True
    #     except botocore.exceptions.WaiterError:
    #         # instance not stopped or not running again
    #         # Change the instance type to previous
    #         self.ec2_client.modify_instance_attribute(InstanceId=ec2_instance_id, Attribute='instanceType',
    #                                                   Value=previous_instance_type)
    #
    #         # Start the instance
    #         self.ec2_client.start_instances(InstanceIds=[ec2_instance_id])
    #         waiter = self.ec2_client.get_waiter('instance_running')
    #         waiter.wait(InstanceIds=[ec2_instance_id])
    #     except Exception as e:
    #         print(str(e))
    #         print("failed in scaling ec2 instance")
    #         return False

    # def copy_pygmy_parameter_group(self, source_parameter_group_name):
    #     """
    #     copy source db parameter group name and create new parameter group
    #     """
    #     try:
    #         # if pygmy parameter already created!
    #         response = self.rds_client.describe_db_parameter_groups(
    #             DBParameterGroupName="{0}-pygmy".format(source_parameter_group_name)
    #         )
    #         return True
    #     except self.rds_client.exceptions.DBParameterGroupNotFoundFault:
    #         # create if not present
    #         self.rds_client.copy_db_parameter_group(
    #             SourceDBParameterGroupIdentifier=source_parameter_group_name,
    #             TargetDBParameterGroupIdentifier="{0}-pygmy".format(source_parameter_group_name),
    #             TargetDBParameterGroupDescription='Parameter group by pygmy'
    #         )
    #
    #         response = self.rds_client.modify_db_parameter_group(
    #             DBParameterGroupName="{0}-pygmy".format(source_parameter_group_name),
    #             Parameters=[
    #                 {
    #                     'ApplyMethod': 'immediate',
    #                     'ParameterName': 'shared_buffers',
    #                     'ParameterValue': '{DBInstanceClassMemory/32768}',
    #                 },
    #                 {
    #                     'ApplyMethod': 'immediate',
    #                     'ParameterName': 'max_connections',
    #                     'ParameterValue': 'LEAST({DBInstanceClassMemory/9531392},5000)',
    #                 }
    #             ]
    #         )
    #         print(response)
    #         return True
    #     except Exception as e:
    #         print(str(e))
    #         return False


    # def process_ec2_cluster_info(self, instance):
    #     db_info, created = Ec2DbInfo.objects.get_or_create(instance_id=instance.instanceId)
    #     db_info.instance_object = instance
    #     db_info.type = EC2
    #     db_info.last_instance_type = instance.instanceType
    #     try:
    #         db_conn = PostgresData(instance.publicDnsName, "pygmy", "pygmy", "postgres")
    #         db_info.isPrimary = db_conn.is_ec2_postgres_instance_primary()
    #         db_info.isConnected = True
    #         print("publicIp: ", instance.publicDnsName, " isPrimary: ", db_conn.is_ec2_postgres_instance_primary())
    #
    #         # Handle primary node case
    #         if db_info.isPrimary:
    #             db_info.cluster = AWSData.get_or_create_cluster(instance, instance.privateIpAddress, cluster_type=EC2)
    #             replicas = db_conn.get_all_slave_servers()
    #             AWSData.update_cluster_info(instance.privateIpAddress, replicas)
    #     except Exception as e:
    #         print("Fail to connect Server {}".format(instance.publicDnsName))
    #         db_info.isPrimary = False
    #         db_info.isConnected = False
    #     finally:
    #         db_info.save()

    # @staticmethod
    # def update_cluster_info(privateDnsName, replicas):
    #     for node in replicas:
    #         instance = AllEc2InstancesData.objects.get(privateIpAddress=node)
    #         db_info, created = Ec2DbInfo.objects.get_or_create(instance_id=instance.instanceId)
    #         db_info.cluster = ClusterInfo.objects.get(primaryNodeIp=privateDnsName, type=EC2)
    #         db_info.content_object = instance
    #         db_info.save()

    # @staticmethod
    # def get_tag_map(instance, cluster_type=EC2):
    #     if cluster_type == EC2:
    #         return dict((tag['Key'], tag['Value'].lower()) for tag in instance.tags)
    #     else:
    #         return dict((tag['Key'], tag['Value'].lower()) for tag in instance.get("TagList"))
