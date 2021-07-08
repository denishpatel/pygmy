import logging
from django.core.management import BaseCommand
from engine.aws.ec_wrapper import EC2Service
from engine.aws.rds_wrapper import RDSService

logdb = logging.getLogger("db")


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        try:
            logdb.info("Getting EC2 instance from AWS started")
            EC2Service().get_instances()
            logdb.info("EC2 instances successfully")
            logdb.info("Started: Getting RDS info")
            RDSService().get_instances()
            logdb.info("Completed: RDS info")
        except Exception as e:
            logdb.exception(e)
            logdb.error("Failed: DB Info")
            return

    # def get_ec2_info(self, instance):
    #     db_info, created = Ec2DbInfo.objects.get_or_create(instance_id=instance.instanceId)
    #     db_info.instance_object = instance
    #     db_info.type = EC2
    #     try:
    #         db_conn = PostgresData(instance.publicDnsName, "pygmy", "pygmy", "postgres")
    #         db_info.isPrimary = db_conn.is_ec2_postgres_instance_primary()
    #         db_info.isConnected = True
    #         print("publicIp: ", instance.publicDnsName, " isPrimary: ", db_conn.is_ec2_postgres_instance_primary())
    #         # db_info.save()
    #
    #         # Handle primary node case
    #         if db_info.isPrimary:
    #             db_info.cluster = EC2Service().get_or_create_cluster(instance, instance.privateIpAddress)
    #             # db_info.save()
    #             replicas = db_conn.get_all_slave_servers()
    #             self.update_cluster_info(instance.privateIpAddress, replicas)
    #     except Exception as e:
    #         print("Fail to connect Server {}".format(instance.publicDnsName))
    #         db_info.isPrimary = False
    #         db_info.isConnected = False
    #     finally:
    #         db_info.save()
    #
    # @staticmethod
    # def update_cluster_info(privateIpAddress, replicas):
    #     for node in replicas:
    #         instance = AllEc2InstancesData.objects.get(privateIpAddress=node)
    #         db_info, created = Ec2DbInfo.objects.get_or_create(instance_id=instance.instanceId)
    #         # db_info.cluster = ClusterInfo.objects.get(primaryNodeIp=privateDnsName, type=EC2)
    #         db_info.cluster = EC2Service().get_or_create_cluster(instance, privateIpAddress)
    #         db_info.content_object = instance
    #         db_info.save()
