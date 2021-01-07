import os
import boto3


class AWSData:
    """
    Environment Variables to be set
        - AWS_ACCESS_KEY_ID
        - AWS_SECRET_ACCESS_KEY
        - AWS_REGION
    """
    def __init__(self):
        self.aws_session = boto3.Session(region_name=os.getenv("AWS_REGION", ""))
        self.rds_client = self.aws_session.client('rds')
        self.ec2_client = self.aws_session.client('ec2')

    def describe_rds_instances(self):
        # Todo take care of pagination
        # Todo make sure we track which slave into
        all_pg_instances = self.rds_client.describe_db_instances(
            Filters=[
                {
                    'Name': 'engine',
                    'Values': [
                        'postgres',
                    ]
                },
            ],
            MaxRecords=100
        )

        all_instances = dict()
        for instance in all_pg_instances.get("DBInstances", []):
            slave_identifier = instance.get("ReadReplicaSourceDBInstanceIdentifier", None)
            if slave_identifier is None:
                # its master
                all_instances[instance["DBInstanceIdentifier"]].append(dict({
                    "db_id": instance["DBInstanceIdentifier"],
                    "db_name": instance["DBName"],
                    "db_username": instance["MasterUsername"],
                    "db_class": instance["DBInstanceClass"],
                    "db_engine": instance["Engine"],
                    "db_instance_status": instance["DBInstanceStatus"],
                    "db_endpoint": dict({
                        "address": instance["Endpoint"].get("Address", ""),
                        "port": instance["Endpoint"].get("Port", "")
                    }),
                    "db_storage": instance["AllocatedStorage"],
                    "db_vpc_security_groups": instance["VpcSecurityGroups"],
                    "db_postgres_engine_version": instance["EngineVersion"],
                    "db_availability_zone": instance["AvailabilityZone"],
                    "is_master": True
                }))
            else:
                # its a slave node of one of the masters
                all_instances[slave_identifier].append(dict({
                    "db_id": instance["DBInstanceIdentifier"],
                    "db_name": instance["DBName"],
                    "db_username": instance["MasterUsername"],
                    "db_class": instance["DBInstanceClass"],
                    "db_engine": instance["Engine"],
                    "db_instance_status": instance["DBInstanceStatus"],
                    "db_endpoint": dict({
                        "address": instance["Endpoint"].get("Address", ""),
                        "port": instance["Endpoint"].get("Port", "")
                    }),
                    "db_storage": instance["AllocatedStorage"],
                    "db_vpc_security_groups": instance["VpcSecurityGroups"],
                    "db_postgres_engine_version": instance["EngineVersion"],
                    "db_availability_zone": instance["AvailabilityZone"],
                    "is_master": False
                }))

        return all_instances

    def describe_ec2_instances(self):
        # Todo check for the pagination
        all_pg_ec2_instances = self.ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:{}'.format(os.getenv("EC2-INSTANCE-POSTGRES-TAG-KEY-NAME", "")),
                    'Values': [
                        os.getenv("EC2-INSTANCE-POSTGRES-TAG-KEY-VALUE", ""),
                    ]
                },
            ]
        )

        all_instances = dict()
        for instance in all_pg_ec2_instances.get("Reservations", []):
            pass
        pass
