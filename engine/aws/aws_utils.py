import botocore
import boto3

from engine.aws.ec_wrapper import EC2Service
from engine.aws.rds_wrapper import RDSService
from engine.models import DbCredentials, RDS, EC2
from webapp.models import Settings, AWS_REGION


class AWSUtil:

    @staticmethod
    def get_aws_service(service_type):
        if service_type == EC2:
            return EC2Service()
        elif service_type == RDS:
            return RDSService()

    @staticmethod
    def check_aws_validity(key_id, secret_key):
        session = boto3.Session(aws_access_key_id=key_id, aws_secret_access_key=secret_key)
        sts = session.client('sts')
        try:
            sts.get_caller_identity()
            return True
        except botocore.exceptions.ClientError:
            return False

    @staticmethod
    def check_aws_validity_from_db():
        cred = AWSUtil.get_aws_credentials()
        return AWSUtil.check_aws_validity(cred.user_name, cred.password)

    @staticmethod
    def get_aws_credentials():
        return DbCredentials.objects.get(name="aws")

    @staticmethod
    def update_aws_region_list():
        if AWSUtil.check_aws_validity_from_db():
            ec2_client = AWSUtil.get_aws_service_client()
            for region in ec2_client.describe_regions()["Regions"]:
                region_name = region["RegionName"]
                region_setting, created = Settings.objects.get_or_create(name="AWS_{0}".format(region_name))
                if created:
                    region_setting.description = region_name
                    region_setting.value = False
                    region_setting.last_sync = None
                    region_setting.type = AWS_REGION
                    region_setting.save()

    @staticmethod
    def get_aws_service_client(service_type='ec2', region='us-east-1'):
        cred = AWSUtil.get_aws_credentials()
        session = boto3.Session(aws_access_key_id=cred.user_name, aws_secret_access_key=cred.password)
        return session.client(service_type, region_name=region)


# def sync_ec2_cluster(self):
    #     db_instances = self.aws.describe_rds_instances()
    #     for db in db_instances:
    #         all_instances = self.aws.describe_ec2_instances(db)
    #         for instance in all_instances:
    #             self.aws.process_ec2_cluster_info(instance)
    #     self.update_setting_db("ec2")
    #
    # def sync_rds_cluster(self):
    #     self.update_setting_db("rds")
    #
    # def update_setting_db(self, s_type):
    #     # Settings update
    #     setting = Settings.objects.get(name=s_type)
    #     setting.last_sync = timezone.now()
    #     setting.save()
