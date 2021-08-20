import logging
from webapp.models import Settings
from django.core.management.base import BaseCommand
from engine.aws.ec_wrapper import EC2Service
from engine.aws.rds_wrapper import RDSService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        try:
            ec2_sync = Settings.objects.get(name="ec2")
            if ec2_sync.value == 'True':
                EC2Service().save_instance_types()
                logger.info("EC2 instance types refresh complete")
            else:
                logger.info("Skipping EC2 instance types refresh as it is disabled")

            rds_sync = Settings.objects.get(name="rds")
            if rds_sync.value == 'True':
                RDSService().save_instance_types()
                logger.info("RDS instance types refresh complete!")
            else:
                logger.info("Skipping RDS instance types refresh as it is disabled")

            print("Done")
        except Exception as e:
            logger.exception(e)
            return
