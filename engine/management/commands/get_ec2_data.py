import logging

from django.core.management import BaseCommand

from engine.models import AllEc2InstancesData, Ec2DbInfo, ClusterInfo
from engine.postgres_wrapper import PostgresData
from engine.views import update_ec2_data

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        try:
            all_instances = update_ec2_data()
            all_instances = AllEc2InstancesData.objects.all()
            for db in all_instances:
                self.get_info(db)
        except Exception as e:
            logger.exception(e)
            return

    def get_info(self, instance):
        db_info, created = Ec2DbInfo.objects.get_or_create(instance=instance)
        try:
            db_conn = PostgresData(instance.publicDnsName, "pygmy", "pygmy", "postgres")
            db_info.isPrimary = db_conn.is_ec2_postgres_instance_primary()
            if db_info.isPrimary:
                db_info.cluster, created = ClusterInfo.objects.get_or_create(primaryNodeIp=instance.privateDnsName)
            db_info.isConnected = True
        except Exception as e:
            db_info.isPrimary = False
            db_info.isConnected = False
        db_info.save()

        if db_info.isPrimary:
            replicas = db_conn.get_all_slave_servers()
            self.update_cluster_info(instance.privateDnsName, replicas)
        print("publicIp: ", instance.publicDnsName, " isPrimary: ", db_conn.is_ec2_postgres_instance_primary())

    def update_cluster_info(self, privateDnsName, replicas):
        for node in replicas:
            instance = AllEc2InstancesData.objects.get(privateIpAddress=node)
            db_info, created = Ec2DbInfo.objects.get_or_create(instance=instance)
            db_info.cluster = ClusterInfo.objects.get(primaryNodeIp=privateDnsName)
            db_info.save()
