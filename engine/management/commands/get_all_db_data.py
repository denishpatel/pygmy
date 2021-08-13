import logging
from webapp.models import Settings
from django.core.management import BaseCommand
from engine.aws.ec_wrapper import EC2Service
from engine.aws.rds_wrapper import RDSService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        try:
            ec2_sync = Settings.objects.get(name="ec2")
            if ec2_sync.value:
                logger.info("Getting EC2 instance from AWS started")
                ec2_service = EC2Service()
                ec2_service.clear_db()
                ec2_service.get_instances()
                logger.info("EC2 instances successfully")
            else:
                logger.info("Skipping EC2 sync as it is disabled!")

            rds_sync = Settings.objects.get(name="rds")
            if rds_sync.value:
                logger.info("Started: Getting RDS info")
                rds_service = RDSService()
                rds_service.clear_db()
                rds_service.get_instances()
                logger.info("Completed: RDS info")
            else:
                logger.info("Skipping RDS sync as it is disabled!")
        except Exception as e:
            logger.exception(e)
            logger.error("Failed: DB Info")
            print("Exception: " + str(e))
            return
