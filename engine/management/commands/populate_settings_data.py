import logging
from django.core.management import BaseCommand
from engine.aws.ec_wrapper import EC2Service
from engine.aws.aws_utils import AWSUtil
from users.models import User
from engine.models import DbCredentials
from webapp.models import Settings, SYNC, CONFIG, AWS_REGION

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        self.populate_settings()

    @staticmethod
    def populate_settings():
        syncSettings = {
            "ec2": "Sync EC2 Data",
            "rds": "Sync RDS Data",
            "logs": "Sync Log Data"
        }
        for key, value in syncSettings.items():
            try:
                setting = Settings.objects.get(name=key)
            except Settings.DoesNotExist:
                setting = Settings()
                enable_flag = input("Enable {} sync? (y/n): ".format(key))
                if enable_flag.lower() in ["y", "yes", "true"]:
                    setting.value = True
                else:
                    setting.value = False
                setting.name = key
                setting.last_sync = None
                setting.description = value
                setting.type = SYNC
            setting.in_progress = False
            setting.save()

        config = dict({
            "EC2_INSTANCE_POSTGRES_TAG_KEY_NAME": ("Tag Name to identify postgres EC2 instance", "Role"),
            "EC2_INSTANCE_POSTGRES_TAG_KEY_VALUE": ("Tag Value to identify postgres EC2 instance", "PostgreSQL"),
            "EC2_INSTANCE_PROJECT_TAG_KEY_NAME": ("Project Tag NAME for Cluster Name", "Project"),
            "EC2_INSTANCE_ENV_TAG_KEY_NAME": ("Environment Tag NAME for Cluster Name", "Environment"),
            "EC2_INSTANCE_CLUSTER_TAG_KEY_NAME": ("Cluster Tag NAME for Cluster Name", "Cluster"),
        })

        for key, value in config.items():
            print(value[0], "gets initial value of:", value[1])
            config_set, created = Settings.objects.get_or_create(name=key)
            if created:
                config_set.description = value[0]
                config_set.value = value[1]
                config_set.last_sync = None
                config_set.type = CONFIG
                config_set.save()

        # Secrets
        secrets = dict({
            "ec2": ("EC2 Postgres Secrets", "postgres", "postgres_password"),
            "rds": ("RDS Postgres Secrets", "postgres", "postgres_password"),
            "aws": ("AWS Secrets", "aws", "aws_secret")
        })

        for key, value in secrets.items():
            secret, created = DbCredentials.objects.get_or_create(name=key)
            if created:
                secret.description = value[0]
                if key in ["ec2", "rds"]:
                    user_name = input("Enter USERNAME for {} Postgres Instance for pygmy to connect:: ".format(value[0]))
                    password = input("Enter PASSWORD for {} Postgres Instance for pygmy to connect:: ".format(value[1]))
                    secret.user_name = user_name
                    secret.password = password
                else:
                    aws_key = input("Enter AWS key: ".format(value[0]))
                    aws_secret = input("Enter AWS secret: ".format(value[1]))
                    secret.user_name = aws_key
                    secret.password = aws_secret
                secret.save()
            else:
                print("Use set_secrets command to reset the aws/postgres secrets")

        # Create user
        Command.create_default_user()
        Command.populate_aws_regions()

    @staticmethod
    def create_default_user():
        try:
            user = User.objects.get(email='admin')
        except User.DoesNotExist:
            user = User.objects.create_user('admin', password='admin')
            user.is_superuser = True
            user.is_staff = True
            user.save()

    @staticmethod
    def populate_aws_regions():
        valid_regions = []
        if AWSUtil.check_aws_validity_from_db():
            aws = EC2Service()
            ENABLE = input("Do you want to enable sync across regions? (y/n): ")
            if ENABLE.lower() in ["y", "yes", "true"]:
                for region in aws.get_all_regions():
                    region_name = region.get("RegionName")
                    print("region name ", region_name)
                    region_setting, created = Settings.objects.get_or_create(name="AWS_{0}".format(region_name))
                    if created:
                        region_setting.description = region_name
                        region_setting.value = True
                        region_setting.last_sync = None
                        region_setting.type = AWS_REGION
                        region_setting.save()
                    valid_regions.append(region_name)
            else:
                for region in aws.get_all_regions():
                    region_name = region.get("RegionName")
                    print("region name ", region_name)
                    enable_flag = input("Enable sync for {} (y/n): ".format(region_name))
                    if enable_flag.lower() in ["y", "yes", "true"]:
                        REGION_ENABLE = True
                    else:
                        REGION_ENABLE = False

                    region_setting, created = Settings.objects.get_or_create(name="AWS_{0}".format(region_name))
                    if created:
                        region_setting.description = region_name
                        region_setting.value = REGION_ENABLE
                        region_setting.last_sync = None
                        region_setting.type = AWS_REGION
                        region_setting.save()
                    valid_regions.append(region_name)
            print("updated aws regions")
        else:
            print("AWS credentials are not valid")

