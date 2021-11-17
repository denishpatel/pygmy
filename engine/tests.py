from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from moto import mock_ec2, mock_rds
from engine.aws.ec_wrapper import EC2Service
from engine.aws.rds_wrapper import RDSService
from engine.models import AllEc2InstanceTypes, AllEc2InstancesData, RdsInstances, AllRdsInstanceTypes, ExceptionData, \
    ClusterInfo
from engine.postgres_wrapper import PostgresData
from engine.rules.rules_helper import RuleHelper
from pygmy.mock_data import MockData, MockRdsData, MockEc2Data, MockPostgresData, MockRuleData
from engine.management.commands.populate_settings_data import Command
from webapp.view.exceptions import ExceptionUtils


class AllEc2InstanceTypesTest(TestCase):
    mock_ec2 = mock_ec2()
    mock_rds = mock_rds()

    @classmethod
    def setUpTestData(cls):
        cls.mock_ec2.start()
        cls.mock_rds.start()

        with patch.object(PostgresData, "__init__", new=MockPostgresData.define_value),\
             patch.object(PostgresData, "is_ec2_postgres_instance_primary", new=MockPostgresData.is_ec2_postgres_instance_primary),\
             patch.object(PostgresData, "get_all_slave_servers", new=MockPostgresData.get_all_slave_servers):
            Command.populate_settings(headless=True)
            MockEc2Data.create_ec2_instances()
            EC2Service().get_instances()

        MockRdsData.create_data_bases()
        RDSService().get_instances()

    def test_ec2_instance_types(self):
        """
        test if instance types are stored
        """
        EC2Service().save_instance_types()
        ec2_small_instance = AllEc2InstanceTypes.objects.get(instance_type="t2.small")
        self.assertIsNotNone(ec2_small_instance)
        ec2_small_instance = AllEc2InstanceTypes.objects.get(instance_type="t2.xlarge")
        self.assertIsNotNone(ec2_small_instance)

    @patch("botocore.client.BaseClient._make_api_call", new=MockData.mock_api_calls)
    def test_rds_instance_types_available(self):
        """
        test if rds instance types are stored
        """
        RDSService().save_instance_types()
        rds_small_instance = AllRdsInstanceTypes.objects.get(instance_type="db.t2.small")
        self.assertIsNotNone(rds_small_instance)
        rds_small_instance = AllRdsInstanceTypes.objects.get(instance_type="db.t2.xlarge")
        self.assertIsNotNone(rds_small_instance)

    def test_ec2_instance_data(self):
        """
        Test if ec2 data is stored
        """
        all_data_count = AllEc2InstancesData.objects.count()
        self.assertEqual(all_data_count, 2)

    def test_rds_clusters_are_discoverable(self):
        """
        Check if instances are discoverable

        For this test to pass we will need to
        make sure that there are some instances
        discoverable
        """
        all_rds_instances = RdsInstances.objects.count()
        self.assertGreater(all_rds_instances, 0)

    @patch("engine.rules.cronutils.CronUtil.create_cron")
    def test_rule_creation_works(self, create_cron):
        """
        Test if rule is created successfully
        """
        create_cron.return_value = True
        rule = MockRuleData.rule1
        rule_db = RuleHelper.add_rule_db(rule)
        self.assertIsNotNone(rule_db)

    @patch("engine.rules.cronutils.CronUtil.create_cron")
    @patch("engine.rules.DbHelper.DbHelper.get_system_load_avg")
    @patch("engine.aws.ec_wrapper.EC2Service.create_connection")
    def test_ec2_scale_down_works(self, create_cron, get_system_load_avg, create_connection):
        """
        Check if ec2 instances are scaled down
        """
        create_cron.return_value = True
        get_system_load_avg.return_value = 0
        create_connection.return_value = None
        rule = MockRuleData.create_ec2_scale_down_rule()
        rule_db = RuleHelper.add_rule_db(rule)
        try:
            RuleHelper.from_id(rule_db.id).apply_rule()
            self.assertTrue(True)
        except Exception as e:
            self.assertTrue(False)

    @patch("engine.rules.cronutils.CronUtil.create_cron")
    @patch("engine.rules.DbHelper.DbHelper.get_system_load_avg")
    @patch("engine.aws.rds_wrapper.RDSService.create_connection")
    def test_rds_scale_down_works(self, create_cron, get_system_load_avg, create_connection):
        """
        Check if rds instances are scaled down
        """
        create_cron.return_value = True
        get_system_load_avg.return_value = 0
        create_connection.return_value = None
        rule = MockRuleData.create_rds_scale_down_rule()
        rule_db = RuleHelper.add_rule_db(rule)
        try:
            RuleHelper.from_id(rule_db.id).apply_rule()
            self.assertTrue(True)
        except Exception as e:
            self.assertTrue(False)

    @patch("engine.rules.cronutils.CronUtil.create_cron")
    @patch("engine.aws.ec_wrapper.EC2Service.create_connection")
    def test_ec2_scale_reverse_works(self, create_cron, create_connection):
        """
        Check if ec2 instances are scaled up
        """
        create_cron.return_value = True
        create_connection.return_value = None
        rule = MockRuleData.create_ec2_reverse_rule()
        rule_db = RuleHelper.add_rule_db(rule)
        try:
            RuleHelper.from_id(rule_db.child_rule.get().id).apply_rule()
            self.assertTrue(True)
        except Exception as e:
            self.assertTrue(False)

    @patch("engine.rules.cronutils.CronUtil.create_cron")
    @patch("engine.aws.rds_wrapper.RDSService.create_connection")
    def test_rds_scale_reverse_works(self, create_cron, create_connection):
        """
        Check if rds instances are scaled up
        """
        create_cron.return_value = True
        create_connection.return_value = None
        rule = MockRuleData.create_rds_reverse_rule()
        rule_db = RuleHelper.add_rule_db(rule)
        try:
            RuleHelper.from_id(rule_db.child_rule.get().id).apply_rule()
            self.assertTrue(True)
        except Exception as e:
            self.assertTrue(False)

    @patch("engine.rules.cronutils.CronUtil.create_cron")
    def test_exception_are_managed(self, create_cron):
        """
        Check if instances are not scaled
        up/down when there is an exception
        window
        """
        create_cron.return_value = True
        rule = MockRuleData.create_ec2_scale_down_rule()
        rule_db = RuleHelper.add_rule_db(rule)

        exc, created = ExceptionData.objects.get_or_create(exception_date=timezone.now().date())
        exc.clusters = [{"value": rule_db.cluster.name, "id": rule_db.cluster.id}]
        exc.save()

        try:
            RuleHelper.from_id(rule_db.id).check_exception_date()
            self.assertTrue(False)
        except Exception as e:
            self.assertTrue(True)

    @patch.object(PostgresData, "__init__", new=MockPostgresData.define_value)
    @patch.object(PostgresData, "get_system_load_avg", new=MockPostgresData.get_system_load_avg_20)
    @patch("engine.rules.cronutils.CronUtil.create_cron")
    def test_scale_down_with_minimum_load_avg(self, create_cron):
        """
        Check if instances are scaled down
        when load avg is under threshold 30
        """
        create_cron.return_value = True
        rule = MockRuleData.create_ec2_scale_down_check_load_avg_rule()
        rule_db = RuleHelper.add_rule_db(rule)
        try:
            RuleHelper.from_id(rule_db.id).apply_rule()
            self.assertTrue(True)
        except Exception as e:
            self.assertTrue(False)

    @patch.object(PostgresData, "__init__", new=MockPostgresData.define_value)
    @patch.object(PostgresData, "get_system_load_avg", new=MockPostgresData.get_system_load_avg_40)
    @patch("engine.rules.cronutils.CronUtil.create_cron")
    @patch("engine.rules.cronutils.CronUtil.set_retry_cron")
    def test_scale_down_negative_load_avg(self, set_retry_cron, create_cron):
        """
        check that instance is not scaled down
        and retry mechanism is tried when load
        avg is greater than threshold
        """
        def set_retry_flag(retry_rule):
            if retry_rule.id == rule_db.id:
                raise Exception("retried")
            return None

        create_cron.return_value = True
        rule = MockRuleData.create_ec2_scale_down_check_load_avg_rule()
        rule_db = RuleHelper.add_rule_db(rule)
        set_retry_cron.side_effect = set_retry_flag

        try:
            RuleHelper.from_id(rule_db.id).apply_rule()
            self.assertTrue(False)
        except Exception as e:
            self.assertTrue(e.__str__() == "retried")

    def test_cluster_discoverable(self):
        cluster = ClusterInfo.objects.filter(type="EC2")
        self.assertTrue(cluster.count() > 0)
        cluster = ClusterInfo.objects.filter(type="RDS")
        self.assertTrue(cluster.count() > 0)

    def test_cluster_name(self):
        cluster_name_with_tags = ClusterInfo.objects.filter(type="EC2")
        self.assertTrue(cluster_name_with_tags[0].name == 'ec2-testing-dummy')
        cluster_name_without_tags = ClusterInfo.objects.filter(type="RDS")
        self.assertTrue(cluster_name_without_tags[0].name == "Cluster 2")

    @patch("engine.rules.cronutils.CronUtil.create_cron")
    def test_check_blackout_window(self, create_cron):
        create_cron.return_value = True
        rule = MockRuleData.create_ec2_scale_down_rule()
        rule_db = RuleHelper.add_rule_db(rule)
        exc, created = ExceptionData.objects.get_or_create(exception_date=timezone.now().date())
        exc.clusters = [{"value": rule_db.cluster.name, "id": rule_db.cluster.id}]
        exc.save()
        self.assertTrue(exc.exception_date == timezone.now().date())

    @patch("engine.rules.cronutils.CronUtil.create_cron")
    def test_altered_blackout_window(self, create_cron):
        create_cron.return_value = True
        rule = MockRuleData.create_ec2_scale_down_rule()
        rule_db = RuleHelper.add_rule_db(rule)
        exc, created = ExceptionData.objects.get_or_create(exception_date=timezone.now().date())
        exc.clusters = [{"value": rule_db.cluster.name, "id": rule_db.cluster.id}]
        exc.save()
        exc.exception_date = timezone.now().date() + timezone.timedelta(days=1)
        exc.save()
        self.assertTrue(exc.exception_date == (timezone.now().date() + timezone.timedelta(days=1)))

    @patch("engine.rules.cronutils.CronUtil.create_cron")
    def test_delete_exception_date(self, create_cron):
        create_cron.return_value = True
        rule = MockRuleData.create_ec2_scale_down_rule()
        rule_db = RuleHelper.add_rule_db(rule)
        exc, created = ExceptionData.objects.get_or_create(exception_date=timezone.now().date())
        exc.clusters = [{"value": rule_db.cluster.name, "id": rule_db.cluster.id}]
        exc.save()
        ExceptionUtils.delete(exc.id)
        try:
            ExceptionData.objects.get(id=exc.id)
            self.assertTrue(False)
        except ExceptionData.DoesNotExist:
            self.assertTrue(True)
