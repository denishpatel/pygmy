from datetime import datetime

from engine.aws_wrapper import AWSData
from webapp.models import Settings


class AwsSync:
    aws = AWSData()

    def sync_ec2_cluster(self):
        db_instances = self.aws.describe_rds_instances()
        for db in db_instances:
            all_instances = self.aws.describe_ec2_instances(db)
            for instance in all_instances:
                self.aws.process_ec2_cluster_info(instance)
        self.update_setting_db("ec2")

    def sync_rds_cluster(self):
        self.update_setting_db("rds")

    def update_setting_db(self, s_type):
        # Settings update
        setting = Settings.objects.get(name=s_type)
        setting.last_sync = datetime.now()
        setting.save()
