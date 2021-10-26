import re
import logging
import os

from engine.rules.cronutils import CronUtil
from django.core.management import BaseCommand
from engine.rules.db_helper import DbHelper
from engine.models import Ec2DbInfo

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('rule_id', nargs=1, type=int, help="Rule id to resume.")
        parser.add_argument('instance_id', nargs=1, help="The instance id to make sure is running before we retry.")

    def sanitize_instance_id(self, instance_id)
        return re.sub('[^0-9\-a-f]', '', instance_id.lower())

    def handle(self, *args, **kwargs):
        logger.debug(os.environ)
        logger.debug(f"My PID is {os.getpid()}")

        sanitized_instance_id = sanitize_instance_id(kwargs['instance_id'])
        rule_id = kwargs['rule_id']

        # Blindly try to start the instance.
        # If it is stopped, retrying the rule before we start the instance will cause it to be ignored.
        # If it is started, no harm will come from telling AWS to start it anyway.
        # If it's been some time that pygmy has been down and an operator has done some things to the cluster while we've been offline,
        # simply starting a replica shouldn't cause any issues.
        instance = Ec2DbInfo.objects.get(instance_id=sanitize_instance_id)
        helper = DbHelper(instance)
        helper.aws.start_instance(sanitize_instance_id)

        # Now that the instance is up, kick off our rule. 
        # If it fails it'll take care of any retries itself, so all we really need to do
        # is wait for it to finish and then remove the intent crontab.
        python_path = os.path.join(settings.BASE_DIR, "venv", "bin", "python")
        manage_path = os.path.join(settings.BASE_DIR, "manage.py")
        try:
            logger.info(f"Re-running our intent for rule {rule_id}")
            test = subprocess.check_output([python_path, manage_path, "apply_rule", rule_id], env=env_var)
            if len(test) > 0:
                logger.info(f"running {python_path} {manage_path} {rule_id} succeeded with non-empty result of {test}")
            else:
                logger.info(f"running {python_path} {manage_path} {rule_id} succeeded")
        except subprocess.CalledProcessError as e:
            logger.info(f"running {python_path} {manage_path} {rule_id} returned: {e.returncode} ({e.output})")
            raise e
        except Exception as e:
            if hasattr(e, 'message'):
                message = e.message
            else:
                message = e
            logger.info(f"running {python_path} {manage_path} {rule_id} returned generic error: {message}")

        # Now that we've completed our intent, remove it from cron
        CronUtil.delete_cron_intent(rule_id)

