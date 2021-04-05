import logging
from django.core.management import BaseCommand
from users.models import User
from engine.models import DbCredentials
from webapp.models import Settings, SYNC, CONFIG

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
                Settings.objects.get(name=key)
            except Settings.DoesNotExist:
                setting = Settings()
                setting.name = key
                setting.last_sync = None
                setting.description = value
                setting.type = SYNC
                setting.save()

        config = dict({
            "EC2_INSTANCE_POSTGRES_TAG_KEY_NAME": ("Tag Name to identify postgres EC2 instance", "Role"),
            "EC2_INSTANCE_POSTGRES_TAG_KEY_VALUE": ("Tag Value to identify postgres EC2 instance", "pg-instance"),
            "EC2_INSTANCE_PROJECT_TAG_KEY_NAME": ("Project Tag NAME for Cluster Name", "Project"),
            "EC2_INSTANCE_ENV_TAG_KEY_NAME": ("Environment Tag NAME for Cluster Name", "Environment"),
            "EC2_INSTANCE_CLUSTER_TAG_KEY_NAME": ("Cluster Tag NAME for Cluster Name", "Cluster"),
        })

        for key, value in config.items():
            print(value[0], value[1])
            config_set, created = Settings.objects.get_or_create(name=key)
            if created:
                config_set.description = value[0]
                config_set.value = value[1]
                config_set.last_sync = None
                config_set.type = CONFIG
                config_set.save()

        # Secrets
        secrets = dict({
            "postgres": ("Postgres Secrets", "postgres", "postgres"),
            "aws": ("AWS Secrets", "AWS", "AWS")
        })

        for key, value in secrets.items():
            print(value[0], value[1])
            secret, created = DbCredentials.objects.get_or_create(name=key)
            if created:
                secret.description = value[0]
                secret.user_name = value[1]
                secret.password = value[2]
                secret.save()

        # Create user
        Command.create_default_user()

    @staticmethod
    def create_default_user():
        try:
            user = User.objects.get(email='admin')
        except User.DoesNotExist:
            user = User.objects.create_user('admin', password='admin')
            user.is_superuser = False
            user.is_staff = True
            user.save()

