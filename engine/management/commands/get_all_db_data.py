import logging
from django.core.management import BaseCommand
from engine.aws.ec_wrapper import EC2Service
from engine.aws.rds_wrapper import RDSService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        try:
            logger.info("Getting EC2 instance from AWS started")
            EC2Service().get_instances()
            logger.info("EC2 instances successfully")
            logger.info("Started: Getting RDS info")
            RDSService().get_instances()
            logger.info("Completed: RDS info")
        except Exception as e:
            logger.exception(e)
            logger.error("Failed: DB Info")
            print("Exception: " + str(e))
            return
