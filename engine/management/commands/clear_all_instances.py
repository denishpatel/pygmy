import logging
from django.core.management import BaseCommand
from engine.models import AllEc2InstancesData, Ec2DbInfo, ClusterInfo, DbCredentials, Rules, RdsInstances

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        try:
            # Delete all instances saved
            Rules.objects.all().delete()
            Ec2DbInfo.objects.all().delete()
            ClusterInfo.objects.all().delete()
            DbCredentials.objects.all().delete()
            RdsInstances.objects.all().delete()
            AllEc2InstancesData.objects.all().delete()
            print("All cluster data deleted!")
        except Exception as e:
            logger.exception(e)
            return
