import logging
from django.core.management import BaseCommand
from engine.aws_wrapper import AWSData
from engine.models import AllEc2InstancesData, Ec2DbInfo, ClusterInfo, EC2
from engine.postgres_wrapper import PostgresData

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        try:
            AWSData().describe_ec2_instances()

            # update ec2 instances data
            all_instances = AllEc2InstancesData.objects.all()
            for db in all_instances:
                self.get_ec2_info(db)

            # update rds data
            AWSData().describe_rds_instances()
        except Exception as e:
            logger.exception(e)
            return

    def get_ec2_info(self, instance):
        db_info, created = Ec2DbInfo.objects.get_or_create(instance_id=instance.instanceId)
        db_info.instance_object = instance
        db_info.type = EC2
        try:
            db_conn = PostgresData(instance.publicDnsName, "pygmy", "pygmy", "postgres")
            db_info.isPrimary = db_conn.is_ec2_postgres_instance_primary()
            db_info.isConnected = True
            print("publicIp: ", instance.publicDnsName, " isPrimary: ", db_conn.is_ec2_postgres_instance_primary())
            # db_info.save()

            # Handle primary node case
            if db_info.isPrimary:
                db_info.cluster = AWSData.get_or_create_cluster(instance, instance.privateIpAddress, cluster_type=EC2)
                # db_info.save()
                replicas = db_conn.get_all_slave_servers()
                self.update_cluster_info(instance.privateIpAddress, replicas)
        except Exception as e:
            print("Fail to connect Server {}".format(instance.publicDnsName))
            db_info.isPrimary = False
            db_info.isConnected = False
        finally:
            db_info.save()

    @staticmethod
    def update_cluster_info(privateIpAddress, replicas):
        for node in replicas:
            instance = AllEc2InstancesData.objects.get(privateIpAddress=node)
            db_info, created = Ec2DbInfo.objects.get_or_create(instance_id=instance.instanceId)
            # db_info.cluster = ClusterInfo.objects.get(primaryNodeIp=privateDnsName, type=EC2)
            db_info.cluster = AWSData.get_or_create_cluster(instance, privateIpAddress, cluster_type=EC2)
            db_info.content_object = instance
            db_info.save()
