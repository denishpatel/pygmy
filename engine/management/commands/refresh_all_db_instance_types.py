import logging
from django.core.management.base import BaseCommand
from engine.aws.ec_wrapper import EC2Service
from engine.aws.rds_wrapper import RDSService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        try:
            EC2Service().save_instance_types()
            logger.info("EC2 refresh complete")
            RDSService().save_instance_types()
            logger.info("RDS instances refresh complete!")
            print("Done")
        except Exception as e:
            logger.exception(e)
            return
