import logging
from django.core.management.base import BaseCommand
# from engine.views import update_all_ec2_instances_types_db, update_all_rds_instance_types_db
from engine.aws.ec_wrapper import EC2Service
from engine.aws.rds_wrapper import RDSService

log = logging.getLogger("db")


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        try:
            EC2Service().save_instance_types()
            log.info("EC2 refresh complete")
            RDSService().save_instance_types()
            log.info("RDS instances refresh complete!")
        except Exception as e:
            log.exception(e)
            return
