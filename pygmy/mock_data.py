import botocore as botocore
from moto import mock_rds, mock_rds2, mock_ec2
import boto3

from engine.models import AllEc2InstancesData, Ec2DbInfo, ClusterInfo


class MockData:
    orig = botocore.client.BaseClient._make_api_call

    @staticmethod
    def mock_api_calls(self, operation_name, kwarg):
        if operation_name == 'DescribeOrderableDBInstanceOptions':
            return MockRdsData.mock_describe_instance_types
        return self.orig(self, operation_name, kwarg)


class MockEc2Data:
    mock_describe_instance_types = {
        "InstanceTypes": [
            {
                "InstanceType": "t2.small",
                "CurrentGeneration": True,
                "FreeTierEligible": False,
                "SupportedUsageClasses": [
                    "on-demand",
                    "spot"
                ],
                "SupportedRootDeviceTypes": [
                    "ebs"
                ],
                "SupportedVirtualizationTypes": [
                    "hvm"
                ],
                "BareMetal": False,
                "Hypervisor": "xen",
                "ProcessorInfo": {
                    "SupportedArchitectures": [
                        "i386",
                        "x86_64"
                    ],
                    "SustainedClockSpeedInGhz": 2.5
                },
                "VCpuInfo": {
                    "DefaultVCpus": 1
                },
                "MemoryInfo": {
                    "SizeInMiB": 2048
                },
                "InstanceStorageSupported": False,
                "EbsInfo": {
                    "EbsOptimizedSupport": "unsupported",
                    "EncryptionSupport": "supported",
                    "NvmeSupport": "unsupported"
                },
                "NetworkInfo": {
                    "NetworkPerformance": "Low to Moderate",
                    "MaximumNetworkInterfaces": 3,
                    "MaximumNetworkCards": 1,
                    "DefaultNetworkCardIndex": 0,
                    "NetworkCards": [
                        {
                            "NetworkCardIndex": 0,
                            "NetworkPerformance": "Low to Moderate",
                            "MaximumNetworkInterfaces": 3
                        }
                    ],
                    "Ipv4AddressesPerInterface": 4,
                    "Ipv6AddressesPerInterface": 4,
                    "Ipv6Supported": True,
                    "EnaSupport": "unsupported",
                    "EfaSupported": False
                },
                "PlacementGroupInfo": {
                    "SupportedStrategies": [
                        "partition",
                        "spread"
                    ]
                },
                "HibernationSupported": True,
                "BurstablePerformanceSupported": True,
                "DedicatedHostsSupported": False,
                "AutoRecoverySupported": True
            },
            {
                "InstanceType": "t2.xlarge",
                "CurrentGeneration": True,
                "FreeTierEligible": False,
                "SupportedUsageClasses": [
                    "on-demand",
                    "spot"
                ],
                "SupportedRootDeviceTypes": [
                    "ebs"
                ],
                "SupportedVirtualizationTypes": [
                    "hvm"
                ],
                "BareMetal": False,
                "Hypervisor": "xen",
                "ProcessorInfo": {
                    "SupportedArchitectures": [
                        "x86_64"
                    ],
                    "SustainedClockSpeedInGhz": 2.3
                },
                "VCpuInfo": {
                    "DefaultVCpus": 4
                },
                "MemoryInfo": {
                    "SizeInMiB": 16384
                },
                "InstanceStorageSupported": False,
                "EbsInfo": {
                    "EbsOptimizedSupport": "unsupported",
                    "EncryptionSupport": "supported",
                    "NvmeSupport": "unsupported"
                },
                "NetworkInfo": {
                    "NetworkPerformance": "Moderate",
                    "MaximumNetworkInterfaces": 3,
                    "MaximumNetworkCards": 1,
                    "DefaultNetworkCardIndex": 0,
                    "NetworkCards": [
                        {
                            "NetworkCardIndex": 0,
                            "NetworkPerformance": "Moderate",
                            "MaximumNetworkInterfaces": 3
                        }
                    ],
                    "Ipv4AddressesPerInterface": 15,
                    "Ipv6AddressesPerInterface": 15,
                    "Ipv6Supported": True,
                    "EnaSupport": "unsupported",
                    "EfaSupported": False
                },
                "PlacementGroupInfo": {
                    "SupportedStrategies": [
                        "partition",
                        "spread"
                    ]
                },
                "HibernationSupported": True,
                "BurstablePerformanceSupported": True,
                "DedicatedHostsSupported": False,
                "AutoRecoverySupported": True
            }
        ],
        "ResponseMetadata": {
            "RequestId": "116c28af-3273-48e0-857e-2cbc8a5b90f9",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "x-amzn-requestid": "116c28af-3273-48e0-857e-2cbc8a5b90f9",
                "cache-control": "no-cache, no-store",
                "strict-transport-security": "max-age=31536000; includeSubDomains",
                "content-type": "text/xml;charset=UTF-8",
                "transfer-encoding": "chunked",
                "vary": "accept-encoding",
                "date": "Fri, 09 Apr 2021 11:54:34 GMT",
                "server": "AmazonEC2"
            },
            "RetryAttempts": 0
        }
    }

    @staticmethod
    def get_tags(name):
        return [
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': name
                    },
                    {
                        'Key': 'Role',
                        'Value': 'postgresql'
                    },
                    {
                        'Key': 'Project',
                        'Value': 'EC2'
                    },
                    {
                        'Key': 'Environment',
                        'Value': 'Testing'
                    },
                    {
                        'Key': 'Cluster',
                        'Value': 'dummy'
                    },
                ]
            },
        ]

    @staticmethod
    def create_ec2_instances():
        with mock_ec2():
            ec2_client = boto3.resource("ec2", "us-east-1")
            ec2_client.create_instances(ImageId='i-12345', MinCount=1, MaxCount=5,
                                        InstanceType="t3.small",
                                        TagSpecifications=MockEc2Data.get_tags("primary"))
            ec2_client.create_instances(ImageId='i-12345', MinCount=1, MaxCount=5,
                                        InstanceType="t3.small",
                                        TagSpecifications=MockEc2Data.get_tags("secondry"))


class MockPostgresData:

    def define_value(self, DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT=5432):
        self.host = DB_HOST

    def is_ec2_postgres_instance_primary(self):
        db = AllEc2InstancesData.objects.get(privateIpAddress=self.host)
        if db.name == "primary":
            return True
        else:
            return False

    def get_all_slave_servers(self):
        db = list(db.privateIpAddress for db in AllEc2InstancesData.objects.filter(name="secondry"))
        return db

    def get_system_load_avg_20(self):
        return 20

    def get_system_load_avg_40(self):
        return 40


class MockRdsData:
    mock_describe_instance_types = {
        "OrderableDBInstanceOptions": [
            {
                "Engine": "postgres",
                "EngineVersion": "9.6.1",
                "DBInstanceClass": "db.t2.small",
                "LicenseModel": "postgresql-license",
                "AvailabilityZones": [
                    {
                        "Name": "us-east-1a"
                    },
                    {
                        "Name": "us-east-1b"
                    },
                    {
                        "Name": "us-east-1c"
                    },
                    {
                        "Name": "us-east-1d"
                    },
                    {
                        "Name": "us-east-1e"
                    },
                    {
                        "Name": "us-east-1f"
                    }
                ],
                "MultiAZCapable": True,
                "ReadReplicaCapable": True,
                "Vpc": True,
                "SupportsStorageEncryption": True,
                "StorageType": "gp2",
                "SupportsIops": False,
                "SupportsEnhancedMonitoring": True,
                "SupportsIAMDatabaseAuthentication": False,
                "SupportsPerformanceInsights": False,
                "MinStorageSize": 5,
                "MaxStorageSize": 16384,
                "AvailableProcessorFeatures": [],
                "SupportsStorageAutoscaling": True,
                "SupportsKerberosAuthentication": False,
                "OutpostCapable": False,
                "SupportsGlobalDatabases": False
            }, {
                "Engine": "postgres",
                "EngineVersion": "9.6.1",
                "DBInstanceClass": "db.t2.xlarge",
                "LicenseModel": "postgresql-license",
                "AvailabilityZones": [
                    {
                        "Name": "us-east-1a"
                    },
                    {
                        "Name": "us-east-1b"
                    },
                    {
                        "Name": "us-east-1c"
                    },
                    {
                        "Name": "us-east-1d"
                    },
                    {
                        "Name": "us-east-1e"
                    },
                    {
                        "Name": "us-east-1f"
                    }
                ],
                "MultiAZCapable": True,
                "ReadReplicaCapable": True,
                "Vpc": True,
                "SupportsStorageEncryption": True,
                "StorageType": "gp2",
                "SupportsIops": False,
                "SupportsEnhancedMonitoring": True,
                "SupportsIAMDatabaseAuthentication": False,
                "SupportsPerformanceInsights": False,
                "MinStorageSize": 5,
                "MaxStorageSize": 16384,
                "AvailableProcessorFeatures": [],
                "SupportsStorageAutoscaling": True,
                "SupportsKerberosAuthentication": False,
                "OutpostCapable": False,
                "SupportsGlobalDatabases": False
            }
        ]
    }

    @staticmethod
    def create_data_bases():
        with mock_rds2():
            conn = boto3.client("rds", region_name="us-east-1")
            database = conn.create_db_instance(
                DBInstanceIdentifier="db-master-1",
                AllocatedStorage=10,
                Engine="postgres",
                DBName="staging-postgres",
                DBInstanceClass="db.m1.small",
                LicenseModel="license-included",
                MasterUsername="root",
                MasterUserPassword="hunter2",
                Port=1234,
                DBSecurityGroups=["my_sg"],
            )

            replica = conn.create_db_instance_read_replica(
                DBInstanceIdentifier="db-replica-1",
                SourceDBInstanceIdentifier="db-master-1",
                DBInstanceClass="db.m1.small",
            )


class MockRuleData:
    rule1 = {
        "name": "Test RDS Cluster Rule CRON",
        "typeTime": "CRON",
        "cronTime": "* */21 * * *",

        "cluster_id": 2,
        "action": "SCALE_DOWN",
        "rds_type": "db.t2.small",

        "enableReplicationLag": "on",
        "selectReplicationLagOp": "equal",
        "replicationLag": "12",

        "enableCheckConnection": "on",
        "selectCheckConnectionOp": "greater",
        "checkConnection": "12",

        "enableAverageLoad": "on",
        "selectAverageLoadOp": "less",
        "averageLoad": "32",

        "enableRetry": "on",
        "retryAfter": 15,
        "retryMax": 3,

        "enableReverse": "on",
        "reverse_action": "SCALE_UP",
        "reverseCronTime": "* */21 * * *"
    }

    @staticmethod
    def create_ec2_scale_down_rule():
        ec2_cluster = ClusterInfo.objects.filter(type="EC2")[0]
        return {
            "name": "Test RDS Cluster Rule CRON",
            "typeTime": "CRON",
            "cronTime": "* */21 * * *",
            "cluster_id": ec2_cluster.id,
            "action": "SCALE_DOWN",
            "ec2_type": "t2.small",
        }

    @staticmethod
    def create_rds_scale_down_rule():
        ec2_cluster = ClusterInfo.objects.filter(type="RDS")[0]
        return {
            "name": "Test RDS Cluster Rule CRON",
            "typeTime": "CRON",
            "cronTime": "* */21 * * *",
            "cluster_id": ec2_cluster.id,
            "action": "SCALE_DOWN",
            "rds_type": "db.t2.small",
        }

    @staticmethod
    def create_ec2_reverse_rule():
        ec2_cluster = ClusterInfo.objects.filter(type="EC2")[0]
        return {
            "name": "Test EC2 Cluster Rule CRON",
            "typeTime": "CRON",
            "cronTime": "* */21 * * *",
            "cluster_id": ec2_cluster.id,
            "action": "SCALE_DOWN",
            "ec2_type": "t2.small",

            "enableReverse": "on",
            "reverse_action": "SCALE_UP",
            "reverseCronTime": "* */6 * * *"
        }

    @staticmethod
    def create_rds_reverse_rule():
        ec2_cluster = ClusterInfo.objects.filter(type="RDS")[0]
        return {
            "name": "Test RDS Cluster Rule CRON",
            "typeTime": "CRON",
            "cronTime": "* */21 * * *",
            "cluster_id": ec2_cluster.id,
            "action": "SCALE_DOWN",
            "rds_type": "t2.small",

            "enableReverse": "on",
            "reverse_action": "SCALE_UP",
            "reverseCronTime": "* */6 * * *"
        }

    @staticmethod
    def create_ec2_scale_down_check_load_avg_rule():
        ec2_cluster = ClusterInfo.objects.filter(type="EC2")[0]
        return {
            "name": "Test RDS Cluster Rule CRON",
            "typeTime": "CRON",
            "cronTime": "* */21 * * *",
            "cluster_id": ec2_cluster.id,
            "action": "SCALE_DOWN",
            "ec2_type": "t2.small",

            "enableAverageLoad": "on",
            "selectAverageLoadOp": "less",
            "averageLoad": "30",
        }
