import botocore
from engine.aws.aws_services import AWSServices
from engine.models import AllEc2InstancesData, EC2, Ec2DbInfo, ClusterInfo, DbCredentials, AllEc2InstanceTypes
from engine.postgres_wrapper import PostgresData
from django.conf import settings
from engine.singleton import Singleton
from webapp.models import Settings as SettingsModal
import logging
logger = logging.getLogger(__name__)


class EC2Service(AWSServices, metaclass=Singleton):
    ec2_client_region_dict = dict()
    SERVICE_TYPE = EC2

    def __init__(self):
        super(EC2Service, self).__init__()

    def __repr__(self):
        return "<EC2Service type:%s>" % (self.SERVICE_TYPE)

    def create_connection(self, db, expect_errors=False):
        host = db.instance_object.privateIpAddress
        db_name = db.cluster.databaseName if db.cluster else "postgres"
        try:
            credentials = DbCredentials.objects.get(name="ec2")
            username = credentials.user_name
            password = credentials.password
        except Exception as e:
            logger.debug("Failed to find ec2 credentials, so we're going to hope libpq finds a way to auth")
            username = None
            password = None
        return PostgresData(host, username, password, db_name, expect_errors=expect_errors)

    def get_all_regions(self):
        regions = self.ec2_client.describe_regions()
        print("all regions ", regions)
        return regions["Regions"]

    def check_instance_status(self, instance):
        response = self.ec2_client.describe_instances(InstanceIds=[instance.instanceId])
        self.save_data(response.get("Reservations")[0]["Instances"][0])
        return response

    def check_instance_running(self, data):
        if data.get("Reservations"):
            instance = data.get("Reservations")[0]["Instances"][0]
            state = instance["State"]
            if state.get("Code") == 16:
                return dict({
                    "PublicDnsName": instance.get("PublicDnsName"),
                    "PublicIpAddress": instance.get("PublicIpAddress"),
                    "PrivateDnsName": instance.get("PrivateDnsName"),
                    "PrivateIpAddress": instance.get("PrivateIpAddress"),
                    "State": state
                })
        return None

    def start_instance(self, instance):
        self.ec2_client.start_instances(InstanceIds=[instance])
        waiter = self.ec2_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance])
        logger.info(f"started {instance}")

    def get_instance_types(self, **kwargs):
        all_instance_types = []
        describe_instance_type_resp = self.ec2_client.describe_instance_types(MaxResults=100, **kwargs)
        while True:
            all_instance_types.extend(describe_instance_type_resp.get("InstanceTypes"))

            # For handling pagination
            if describe_instance_type_resp.get("NextToken", None) is None:
                break

            describe_instance_type_resp = self.ec2_client.describe_instance_types(
                MaxResults=100,
                NextToken=describe_instance_type_resp.get("NextToken")
            )

        return all_instance_types

    def scale_instance(self, instance, new_instance_type, fallback_instances=None):
        """
            scale up and down the ec2 instances
        """
        ec2_instance_id = instance.instanceId
        previous_instance_type = instance.instanceType
        logger.info(f"scaling instance {ec2_instance_id} from {previous_instance_type} to {new_instance_type}")
        try:
            self.__scale_instance(ec2_instance_id, new_instance_type)
        except botocore.exceptions.WaiterError:
            logger.debug(f"Oh noes! It's botocore error exception handler time!")
            # Fall backing instances
            for fallback_instance in fallback_instances:
                try:
                    logger.info("Setting fallback instance type {}.", fallback_instance)
                    self.__scale_instance(ec2_instance_id, fallback_instance)
                    return True
                except botocore.exceptions.WaiterError:
                    logger.error("Failed to set fallback instance type {}.", fallback_instance)
        except Exception as e:
            # Change the instance type to previous
            logger.error(f"failed in scaling ec2 instance because {str(e)}; reverting instance type")
            self.__scale_instance(ec2_instance_id, previous_instance_type)
            return False

    def __scale_instance(self, ec2_instance_id, new_instance_type):
        """
           scale up and down the ec2 instances
       """
        # stop the instance
        logger.info(f"stopping {ec2_instance_id}")
        self.ec2_client.stop_instances(InstanceIds=[ec2_instance_id])
        logger.debug(f"waiting for {ec2_instance_id} to stop")
        waiter = self.ec2_client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=[ec2_instance_id])

        logger.debug(f"{ec2_instance_id} has stopped")

        # Change the instance type
        self.ec2_client.modify_instance_attribute(InstanceId=ec2_instance_id, Attribute='instanceType',
                                                  Value=new_instance_type)

        logger.info(f"modified {ec2_instance_id} to be {new_instance_type}")

        # Record the new instance size.
        # Not _technically_ necessary, as it will refresh on the next run anyway,
        # but if anybody looks at the db in the meantime, it know it no longer represents reality.
        try:
            logger.debug(f"Recording new instance size of {new_instance_type}.")
            resizedNode = Ec2DbInfo.objects.get(instance_id=ec2_instance_id)
            resizedNode.last_instance_type = new_instance_type
            resizedNode.save()
        except Exception as e:
            logger.warning(f"Failed to record new instance size, so we'll just keep going and pick it up when the next run starts.")


        # Start the instance
        self.start_instance(ec2_instance_id)
        return True

    def get_instances(self, extra_filters=None):
        all_instances = dict()
        TAG_KEY_NAME = SettingsModal.objects.get(name="EC2_INSTANCE_POSTGRES_TAG_KEY_NAME")
        TAG_KEY_VALUE = SettingsModal.objects.get(name="EC2_INSTANCE_POSTGRES_TAG_KEY_VALUE")
        filters = [
            {
                'Name': 'tag:{}'.format(TAG_KEY_NAME.value),
                'Values': [TAG_KEY_VALUE.value, ]
            },
            {
                'Name': 'instance-state-name',
                'Values': ['running']
            }]
        if len(settings.EC2_INSTANCE_VPC_MENU) > 0:
            filters.extend([{'Name': 'vpc-id', 'Values': settings.EC2_INSTANCE_VPC_MENU}])
        if extra_filters is not None:
            filters.extend(extra_filters)

        logger.debug(f"Looking to get instances to match the filters {filters}")

        # First describe instances
        for region in AWSServices.get_enabled_regions():
            all_pg_ec2_instances = self.ec2_client_region_dict[region].describe_instances(
                Filters=filters
            )

            while True:
                # For handling pagination
                for reservation in all_pg_ec2_instances.get("Reservations", []):
                    for instance in reservation.get("Instances", []):
                        logger.debug(f"found instance {instance['InstanceId']} ({instance['InstanceType']})")
                        all_instances[instance["InstanceId"]] = dict({
                            "instance_id": instance["InstanceId"],
                            "region": region,
                            "instance_type": instance["InstanceType"],
                            "image_id": instance["ImageId"],
                            "state": instance["State"],
                            "vpc_id": instance["VpcId"],
                            "availability_zone": instance["Placement"]["AvailabilityZone"],
                            "ip": dict({
                                "private_ip": instance["PrivateIpAddress"],
                                "public_ip": instance.get("PublicIpAddress", "")
                            }),
                            "tags": instance["Tags"],
                            "launch_time": instance["LaunchTime"]
                        })
                        self.save_data(instance, region=region)

                if all_pg_ec2_instances.get("NextToken", None) is None:
                    break

                all_pg_ec2_instances = self.ec2_client.describe_instances(
                    Filters=filters,
                    NextToken=all_pg_ec2_instances.get("NextToken")
                )

        self.update_last_sync_time()

        # Update Cluster Info for the instances we've selected
        for instance in AllEc2InstancesData.objects.filter(instanceId__in=all_instances.keys()):
            self.check_cluster_info(instance)
        return all_instances

    def check_cluster_info(self, instance):
        logger.debug(f"Checking cluster info for instance {instance.instanceId} ({instance.instanceType})")
        try:
            db = Ec2DbInfo.objects.get(instance_id=instance.instanceId)
            logger.debug(f"Found Ec2DbInfo record with cluster_id {db.cluster_id}")
        except Ec2DbInfo.DoesNotExist:
            logger.info(f"Instance {instance.instanceId} appears new to us")
            # Because we don't have this yet, go ahead and create it. In the unlikely event that it fails,
            # we'll just fail to run for now.
            db, created = Ec2DbInfo.objects.get_or_create(instance_id=instance.instanceId, type=EC2, last_instance_type=instance.instanceType)
        except Exception as e:
            logger.warn(f"Failed to get ec2dbinfo for {instance.instanceId} because {e}")
            return
        db.instance_object = instance
        logger.debug(f"Found Ec2DbInfo record with cluster_id {db.cluster_id}")
        try:
            if len(settings.EC2_INSTANCE_VPC_MENU) > 0:
                if instance.vpcId not in settings.EC2_INSTANCE_VPC_MENU:
                    logger.info(f"Ignoring {instance.instanceId} because we don't care about VPC {instance.vpcId}")
                    return
            conn = self.create_connection(db)
            db.isPrimary = conn.is_ec2_postgres_instance_primary()
            db.isConnected = True

            if db.isPrimary:
                logger.debug(f"This cluster's primary node is currently {instance.instanceId}")
                db.cluster = self.get_or_create_cluster(instance, instance.privateIpAddress)
                replicas = conn.get_all_slave_servers()
                self.update_replica_cluster_info(instance.privateIpAddress, replicas)
            else:
                logger.debug(f"Instance {instance.instanceId} isn't a primary node")
        except Exception as e:
            logger.error(f"Ruh oh, looks like we found an exception checking out {instance.instanceId}: {e}")
            db.isPrimary = False
            db.isConnected = False
        finally:
            db.save()

    def get_tag_map(self, instance):
        return dict((tag['Key'], tag['Value']) for tag in instance.tags)

    def update_replica_cluster_info(self, private_dns_name, replicas):
        for node in replicas:
            logger.debug(f"updating replica info for node {node}")
            try:
                instance = AllEc2InstancesData.objects.get(privateIpAddress=node)
            except AllEc2InstancesData.DoesNotExist:
                logger.info(f"{node} doesn't seem to be an instance we know about; skipping")
                return
            try:
                db_info = Ec2DbInfo.objects.get(instance_id=instance.instanceId)
            except Ec2DbInfo.DoesNotExist:
                logger.info(f"Instance {instance.instanceId} appears new to us")
                # Because we don't have this yet, go ahead and create it. In the unlikely event that it fails,
                # we'll just fail to run for now.
                db_info, created = Ec2DbInfo.objects.get_or_create(instance_id=instance.instanceId, type=EC2, last_instance_type=instance.instanceType)
            except Exception as e:
                logger.warn(f"Failed to retrieve ec2dbinfo for {instance.instanceId} because {e}")
                return
            db_info.cluster = ClusterInfo.objects.get(primaryNodeIp=private_dns_name, type=EC2)
            db_info.content_object = instance
            db_info.save()

    def save_data(self, instance, region=settings.DEFAULT_REGION):
        try:
            db = AllEc2InstancesData.objects.get(instanceId=instance["InstanceId"], region=region)
        except AllEc2InstancesData.DoesNotExist:
            db = AllEc2InstancesData()
            db.instanceId = instance["InstanceId"]
            db.region = region
        db.name = next((tag["Value"] for tag in instance["Tags"] if tag["Key"] == "Name"), None)
        db.instanceType = instance["InstanceType"]
        db.keyName = instance["KeyName"]
        db.launchTime = instance["LaunchTime"]
        db.availabilityZone = instance["Placement"]["AvailabilityZone"]
        db.privateDnsName = instance["PrivateDnsName"]
        db.privateIpAddress = instance["PrivateIpAddress"]
        db.publicDnsName = instance["PublicDnsName"]
        db.publicIpAddress = instance.get("PublicIpAddress", "")
        db.state = instance["State"]
        db.vpcId = instance["VpcId"]
        db.subnetId = instance["SubnetId"]
        db.architecture = instance["Architecture"]
        db.blockDeviceMapping = instance["BlockDeviceMappings"]
        db.ebsOptimized = instance["EbsOptimized"]
        db.securityGroups = instance["SecurityGroups"]
        db.tags = instance["Tags"]
        db.virtualizationType = instance["VirtualizationType"]
        db.cpuOptions = instance.get("CpuOptions", {})
        db.save()

    def save_instance_types(self):
        try:
            all_instances = self.get_instance_types()
            if AllEc2InstanceTypes.objects.count() != len(all_instances):
                for instance in all_instances:
                    try:
                        inst = AllEc2InstanceTypes.objects.get(instance_type=instance["InstanceType"])
                    except AllEc2InstanceTypes.DoesNotExist:
                        aeit = AllEc2InstanceTypes()
                        aeit.save_instance_types(instance)
        except Exception as e:
            print(str(e))
            print(instance)

    def clear_db(self):
        try:
            Ec2DbInfo.objects.filter(types="EC2").delete()
            AllEc2InstancesData.objects.all().delete()
        except Exception as e:
            pass
