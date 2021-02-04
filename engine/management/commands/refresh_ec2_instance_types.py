import logging
from django.core.management.base import BaseCommand
from engine.views import update_all_ec2_instances_types_db, update_all_rds_instance_types_db
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        try:
            update_all_ec2_instances_types_db()
            print("EC2 refresh complete")
            update_all_rds_instance_types_db()
            print("RDS instances refresh complete!")
        except Exception as e:
            logger.exception(e)
            return
