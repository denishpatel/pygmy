from django.test import TestCase
from engine.aws_wrapper import AWSData
from engine.models import AllEc2InstanceTypes, AllEc2InstancesData, RdsInstances, AllRdsInstanceTypes
from webapp.models import Settings
from engine.views import update_all_ec2_instances_types_db, update_all_rds_instance_types_db


class AllEc2InstanceTypesTest(TestCase):
    def setUp(self):
        ad = AWSData()
        # EC2 instance types refresh
        update_all_ec2_instances_types_db()

        # RDS instance types refresh
        update_all_rds_instance_types_db()

        # populate settings data
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
                setting.save()

        # for testing the ec2 instances data
        ad.describe_ec2_instances()

        ad.describe_rds_instances()

    def test_ec2_instance_types(self):
        """
        test if instance types are stored
        """
        ec2_small_instance = AllEc2InstanceTypes.objects.get(instance_type="t2.small")
        self.assertIsNotNone(ec2_small_instance)
        ec2_small_instance = AllEc2InstanceTypes.objects.get(instance_type="t2.xlarge")
        self.assertIsNotNone(ec2_small_instance)

    def test_rds_instance_types_available(self):
        """
        test if rds instance types are stored
        """
        rds_small_instance = AllRdsInstanceTypes.objects.get(instance_type="db.t2.small")
        self.assertIsNotNone(rds_small_instance)
        rds_small_instance = AllRdsInstanceTypes.objects.get(instance_type="db.t2.xlarge")
        self.assertIsNotNone(rds_small_instance)

    def test_ec2_instance_data(self):
        """
        Test if ec2 data is stored
        """
        all_data_count = AllEc2InstancesData.objects.count()
        self.assertNotEqual(all_data_count, 0)

    def test_rds_clusters_are_discoverable(self):
        """
        Check if instances are discoverable

        For this test to pass we will need to
        make sure that there are some instances
        discoverable
        """
        all_rds_instances = RdsInstances.objects.count()
        self.assertGreater(all_rds_instances, 0)

    def test_rule_creation_works(self):
        """
        Test if rule is created successfully
        """
        pass

    def test_ec2_scale_down_works(self):
        """
        Check if ec2 instances are scaled down
        """
        pass

    def test_rds_scale_down_works(self):
        """
        Check if rds instances are scaled down
        """
        pass

    def test_ec2_scale_up_works(self):
        """
        Check if ec2 instances are scaled up
        """
        pass

    def test_rds_scale_up_works(self):
        """
        Check if rds instances are scaled up
        """
        pass

    def test_exception_are_managed(self):
        """
        Check if instances are not scaled
        up/down when there is an exception
        window
        """
        pass

    def test_scale_down_with_minimum_load_avg(self):
        """
        Check if instances are scaled down
        when load avg is under threshold
        """
        pass

    def test_scale_down_negative_load_avg(self):
        """
        check that instance is not scaled down
        and retry mechanism is tried when load
        avg is greater than threshold
        """
        pass
