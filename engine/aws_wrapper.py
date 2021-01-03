import os
import boto3


class AWSData:
    """
    Environment Variables to be set
        - AWS_ACCESS_KEY_ID
        - AWS_SECRET_ACCESS_KEY
        - AWS_REGION_NAME
    """
    def __init__(self):
        self.aws_session = boto3.Session(region_name=os.getenv("AWS_REGION_NAME", ""))
        self.rds_client = self.aws_session.client('rds')
        self.ec2_client = self.aws_session.client('ec2')

    def describe_rds_instances(self):
        # Todo take care of pagination
        all_pg_instances = self.rds_client.describe_db_instances(
            Filters=[
                {
                    'Name': 'engine',
                    'Values': [
                        'postgresql',
                    ]
                },
            ],
            MaxRecords=100
        )
        return all_pg_instances

    def describe_ec2_instances(self):
        pass
