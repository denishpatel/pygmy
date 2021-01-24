import os
import boto3
from engine.models import AllEc2InstancesData, RdsInstances, ClusterInfo, EC2, RDS, Ec2DbInfo


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
            MaxRecords=100
        )

        while True:
            for instance in all_pg_instances.get("DBInstances", []):
                slave_identifier = instance.get("ReadReplicaSourceDBInstanceIdentifier", None)
                if slave_identifier is None:
                    rds = self.save_rds_data(instance)
                    db_info, created = Ec2DbInfo.objects.get_or_create(instance=rds.dbInstanceIdentifier, type=RDS)
                    cluster, created = ClusterInfo.objects.get_or_create(primaryNodeIp=rds.dbInstanceIdentifier, type=RDS)
                    db_info.isPrimary = True
                    db_info.cluster = cluster
                    db_info.isConnected = True
                    db_info.save()
                    # its master
                    # if not instance["DBInstanceIdentifier"] in all_instances.keys():
                    #     all_instances[instance["DBInstanceIdentifier"]] = list()
                    # all_instances[instance["DBInstanceIdentifier"]].append(dict({
                    #     "db_id": instance["DBInstanceIdentifier"],
                    #     "db_name": instance["DBName"],
                    #     "db_username": instance["MasterUsername"],
                    #     "db_class": instance["DBInstanceClass"],
                    #     "db_engine": instance["Engine"],
                    #     "db_instance_status": instance["DBInstanceStatus"],
                    #     "db_endpoint": dict({
                    #         "address": instance["Endpoint"].get("Address", ""),
                    #         "port": instance["Endpoint"].get("Port", "")
                    #     }),
                    #     "db_storage": instance["AllocatedStorage"],
                    #     "db_vpc_security_groups": instance["VpcSecurityGroups"],
                    #     "db_postgres_engine_version": instance["EngineVersion"],
                    #     "db_parameter_groups": instance["DBParameterGroups"],
                    #     "db_availability_zone": instance["AvailabilityZone"],
                    #     "is_master": True
                    # }))
                else:
                    rds = self.save_rds_data(instance)
                    cluster, created = ClusterInfo.objects.get_or_create(primaryNodeIp=slave_identifier, type=RDS)
                    db_info, created = Ec2DbInfo.objects.get_or_create(instance=rds.dbInstanceIdentifier, type=RDS)
                    db_info.cluster = cluster
                    db_info.isPrimary = False
                    db_info.isConnected = True
                    db_info.save()
                    # its a slave node of one of the masters
                    # all_instances[slave_identifier].append(dict({
                    #     "db_id": instance["DBInstanceIdentifier"],
                    #     "db_name": instance["DBName"],
                    #     "db_username": instance["MasterUsername"],
                    #     "db_class": instance["DBInstanceClass"],
                    #     "db_engine": instance["Engine"],
                    #     "db_instance_status": instance["DBInstanceStatus"],
                    #     "db_endpoint": dict({
                    #         "address": instance["Endpoint"].get("Address", ""),
                    #         "port": instance["Endpoint"].get("Port", "")
                    #     }),
                    #     "db_storage": instance["AllocatedStorage"],
                    #     "db_vpc_security_groups": instance["VpcSecurityGroups"],
                    #     "db_postgres_engine_version": instance["EngineVersion"],
                    #     "db_availability_zone": instance["AvailabilityZone"],
                    #     "is_master": False
                    # }))
            if all_pg_instances.get("NextToken", None) is None:
                break

            all_pg_instances = self.rds_client.describe_db_instances(
                Filters=filters,
                MaxResults=100,
                NextToken=all_pg_instances.get("NextToken")
            )

        # Add Cluster entries
        # for cluster_key in  all_instances:
        #     cluster, created = ClusterInfo.objects.get_or_create(primaryNodeIp=cluster_key, type=RDS)
        #     rdsInstances = all_instances[cluster_key]
        #     for instance in rdsInstances:
        #         rds = self.save_rds_data(instance)
        #         db_info = Ec2DbInfo.objects.get_or_create(instance=rds.dbInstanceIdentifier, type=RDS)
        #         db_info.isPrimary = rds.dbInstanceIdentifier == cluster_key
        #         db_info.cluster = cluster
        #         db_info.dbName = instance.dbName
        #         db_info.isConnected = True
        #         db_info.save()

        return all_instances

    def describe_ec2_instances(self):
        all_instances = dict()
        filters = [{
            'Name': 'tag:{}'.format(os.getenv("EC2-INSTANCE-POSTGRES-TAG-KEY-NAME", "type")),
            'Values': [
                os.getenv("EC2-INSTANCE-POSTGRES-TAG-KEY-VALUE", "pg-instance"),
            ]
        }]

        # First describe instance
        all_pg_ec2_instances = self.ec2_client.describe_instances(
            # Filters=filters,
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
                        "availability_zone": instance["Placement"]["AvailabilityZone"],
                        "ip": dict({
                            "private_ip": instance["PrivateIpAddress"],
                            "public_ip": instance["PublicIpAddress"]
                        }),
                        "tags": instance["Tags"],
                        "launch_time": instance["LaunchTime"]
                    })
                    self.save_ec2_data(instance)

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

    @staticmethod
    def save_ec2_data(instance):
        db = AllEc2InstancesData()
        db.instanceId = instance["InstanceId"]
        db.name = next((tag["Value"] for tag in instance["Tags"] if tag["Key"] == "Name"), None)
        db.instanceType = instance["InstanceType"]
        db.keyName = instance["KeyName"]
        db.launchTime = instance["LaunchTime"]
        db.availabilityZone = instance["Placement"]["AvailabilityZone"]
        db.privateDnsName = instance["PrivateDnsName"]
        db.privateIpAddress = instance["PrivateIpAddress"]
        db.publicDnsName = instance["PublicDnsName"]
        db.publicIpAddress = instance["PublicIpAddress"]
        db.state = instance["State"]
        db.vpcId = instance["VpcId"]
        db.subnetId = instance["SubnetId"]
        db.architecture = instance["Architecture"]
        db.blockDeviceMapping = instance["BlockDeviceMappings"]
        db.ebsOptimized = instance["EbsOptimized"]
        db.securityGroups = instance["SecurityGroups"]
        db.tags = instance["Tags"]
        db.virtualizationType = instance["VirtualizationType"]
        db.cpuOptions = instance["CpuOptions"]
        db.save()

    @staticmethod
    def save_rds_data(instance):
        rds = RdsInstances()
        rds.dbInstanceIdentifier = instance["DBInstanceIdentifier"]
        rds.dbInstanceClass = instance["DBInstanceClass"]
        rds.dbName = instance["DBName"]
        rds.engine = instance["Engine"]
        rds.dbInstanceStatus = instance["DBInstanceStatus"]
        rds.dbEndpoint = instance["Endpoint"]
        rds.dbStorage = instance["AllocatedStorage"]
        rds.dbVpcSecurityGroups = instance["VpcSecurityGroups"]
        rds.masterUsername = instance["MasterUsername"]
        rds.preferredBackupWindow = instance["PreferredBackupWindow"]
        rds.availabilityZone = instance["AvailabilityZone"]
        rds.dBParameterGroups = instance["DBParameterGroups"]
        rds.engineVersion = instance["EngineVersion"]
        rds.licenseModel = instance["LicenseModel"]
        rds.publiclyAccessible = instance["PubliclyAccessible"]
        rds.tagList = instance["TagList"]
        rds.save()
        return rds

    def get_ec2_db_info(self, ipAddress):
        pass

    def scale_rds_instance(self, db_instance_id, db_instance_type, db_parameter_group, apply_immediately=True):
        """
        scale up and down the rds instance
        """
        try:
            self.rds_client.modify_db_instance(
                DBInstanceIdentifier=db_instance_id,
                DBInstanceClass=db_instance_type,
                DBParameterGroupName=db_parameter_group,
                ApplyImmediately=apply_immediately
            )
            return True
        except Exception as e:
            print(str(e))
            return False

    def scale_ec2_instance(self, ec2_instance_id, ec2_instance_type):
        """
        scale up and down the ec2 instances
        """
        try:
            # stop the instance
            self.ec2_client.stop_instances(InstanceIds=[ec2_instance_id])
            waiter = self.ec2_client.get_waiter('instance_stopped')
            waiter.wait(InstanceIds=[ec2_instance_id])

            # Change the instance type
            self.ec2_client.modify_instance_attribute(InstanceId=ec2_instance_id, Attribute='instanceType',
                                                      Value=ec2_instance_type)

            # Start the instance
            self.ec2_client.start_instances(InstanceIds=[ec2_instance_id])
            return True
        except Exception as e:
            print(str(e))
            return False

    def copy_pygmy_parameter_group(self, source_parameter_group_name):
        """
        copy source db parameter group name and create new parameter group
        """
        try:
            # if pygmy parameter already created!
            response = self.rds_client.describe_db_parameter_groups(
                DBParameterGroupName="{0}-pygmy".format(source_parameter_group_name)
            )
            return True
        except self.rds_client.exceptions.DBParameterGroupNotFoundFault:
            # create if not present
            self.rds_client.copy_db_parameter_group(
                SourceDBParameterGroupIdentifier=source_parameter_group_name,
                TargetDBParameterGroupIdentifier="{0}-pygmy".format(source_parameter_group_name),
                TargetDBParameterGroupDescription='Parameter group by pygmy'
            )

            response = self.rds_client.modify_db_parameter_group(
                DBParameterGroupName="{0}-pygmy".format(source_parameter_group_name),
                Parameters=[
                    {
                        'ApplyMethod': 'immediate',
                        'ParameterName': 'shared_buffers',
                        'ParameterValue': '{DBInstanceClassMemory/32768}',
                    },
                    {
                        'ApplyMethod': 'immediate',
                        'ParameterName': 'max_connections',
                        'ParameterValue': 'LEAST({DBInstanceClassMemory/9531392},5000)',
                    }
                ]
            )
            print(response)
            return True
        except Exception as e:
            print(str(e))
            return False
