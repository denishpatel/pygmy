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
        all_instances = dict()
        filters = [{
            'Name': 'engine',
            'Values': [
                'postgres',
            ]},
        ]

        # First describe instance
        all_pg_instances = self.rds_client.describe_db_instances(
            Filters=filters,
            MaxResults=100
        )

        while True:
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
            if all_pg_instances.get("NextToken", None) is None:
                break

            all_pg_instances = self.rds_client.describe_db_instances(
                Filters=filters,
                MaxResults=100,
                NextToken=all_pg_instances.get("NextToken")
            )
        return all_instances

    def describe_ec2_instances(self):
        all_instances = dict()
        filters = [{
            'Name': 'tag:{}'.format(os.getenv("EC2-INSTANCE-POSTGRES-TAG-KEY-NAME", "Name")),
            'Values': [
                os.getenv("EC2-INSTANCE-POSTGRES-TAG-KEY-VALUE", "pg-instance"),
            ]
        }]

        # First describe instance
        all_pg_ec2_instances = self.ec2_client.describe_instances(
            Filters=filters,
            MaxResults=200
        )

        while True:
            # For handling pagination
            for reservation in all_pg_ec2_instances.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    all_instances[instance["InstanceId"]] = dict({
                        "instance_id": instance["InstanceId"],
                        "instance_type": instance["InstanceType"],
                        "image_id": instance["ImageId"],
                        "state": instance["State"],
                        "vpc_id": instance["VpcId"],
                        "ip": dict({
                            "private_ip": instance["PrivateIpAddress"],
                            "public_ip": instance["PublicIpAddress"]
                        }),
                        "launch_time": instance["LaunchTime"]
                    })

            if all_pg_ec2_instances.get("NextToken", None) is None:
                break

            all_pg_ec2_instances = self.ec2_client.describe_instances(
                Filters=filters,
                MaxResults=200,
                NextToken=all_pg_ec2_instances.get("NextToken")
            )

        return all_instances

    def describe_ec2_instance_types(self):
        all_instance_types = []
        describe_instance_type_resp = self.ec2_client.describe_instance_types(MaxResults=100)
        while True:
            all_instance_types.extend(describe_instance_type_resp.get("InstanceTypes"))

            # For handling pagination
            if describe_instance_type_resp.get("NextToken", None) is None:
                break

            describe_instance_type_resp = self.ec2_client.describe_instance_types(
                MaxResults=100,
                NextToken=describe_instance_type_resp.get("NextToken")
            )

        return all_instance_types
