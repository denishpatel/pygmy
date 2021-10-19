import logging
import os
import subprocess
import sys
from django.conf import settings
from django.utils import timezone
from engine.rules.db_helper import DbHelper
from engine.models import Rules, RDS, Ec2DbInfo, ExceptionData, SCALE_DOWN, EC2, DbCredentials, DAILY, CRON, SCALE_UP
from engine.rules.cronutils import CronUtil
logger = logging.getLogger(__name__)


class RuleHelper:

    def __init__(self, rule):
        self.rule = rule
        self.rule_json = rule.rule
        self.action = rule.action  # SCALE_DOWN or SCALE_UP
        self.cluster = rule.cluster
        self.cluster_type = rule.cluster.type
        self.new_instance_type = self.rule_json.get("rds_type") if self.rule.cluster.type == RDS else self.rule_json.get("ec2_type")
        self.secondary_dbs = Ec2DbInfo.objects.filter(cluster=self.rule.cluster, isPrimary=False)
        self.primary_dbs = Ec2DbInfo.objects.filter(cluster=self.rule.cluster, isPrimary=True)
        self._is_cluster_managed = hasattr(self.rule.cluster, "load_management")
        self.cluster_mgmt = self.rule.cluster.load_management if self._is_cluster_managed else None
        self.is_reverse = True if self.rule.parent_rule else False
        self.fallback_instances = list()
        self._db_avg_load = dict()
        if self.cluster_mgmt:
            self.fallback_instances = self.cluster_mgmt.fallback_instances_scale_up if self.action == SCALE_UP else self.cluster_mgmt.fallback_instances_scale_down

    @classmethod
    def from_id(cls, rule_id):
        rule = Rules.objects.get(id=rule_id)
        return cls(rule)

    @classmethod
    def add_rule_db(cls, data, rule_db=None):
        if not rule_db:
            rule_db = Rules()

        # name, rule_type, cluster_id, time, ec2_type, rds_type
        rules = {
            "ec2_type": data.get("ec2_type", None),
            "rds_type": data.get("rds_type", None)
        }

        # Set replication check
        enableReplicationLag = data.get("enableReplicationLag", None)
        if enableReplicationLag and enableReplicationLag == "on":
            rules.update({
                "replicationLag": dict({
                    "op": data.get("selectReplicationLagOp", None),
                    "value": data.get("replicationLag", None)
                })
            })

        # Set Connection check
        enableCheckConnection = data.get("enableCheckConnection", None)
        if enableCheckConnection and enableCheckConnection == "on":
            rules.update({
                "checkConnection": dict({
                    "op": data.get("selectCheckConnectionOp", None),
                    "value": data.get("checkConnection", None)
                })
            })

        # Set Average Load check
        enableAverageLoad = data.get("enableAverageLoad", None)
        if enableAverageLoad and enableAverageLoad == "on":
            rules.update({
                "averageLoad": dict({
                    "op": data.get("selectAverageLoadOp", None),
                    "value": data.get("averageLoad", None)
                })
            })

        # Set Retry settings
        enableRetry = data.get("enableRetry", None)
        if enableRetry and enableRetry == "on":
            rules.update({
                "retry": dict({
                    "retry_after": data.get("retryAfter", 15),
                    "retry_max": data.get("retryMax", 3)
                })
            })

        rule_db.name = data.get("name", None)
        rule_db.action = data.get("action", None)
        rule_db.cluster_id = data.get("cluster_id", None)
        typeTime = data.get("typeTime", None)

        # Set time
        if typeTime.upper() == DAILY:
            rule_db.run_type = DAILY
            rule_db.run_at = data.get("dailyTime", None)
        else:
            rule_db.run_type = CRON
            rule_db.run_at = data.get("cronTime", None)

        rule_db.rule = rules
        rule_db.save()
        CronUtil.create_cron(rule_db)
        cls.create_reverse_rule(data, rule_db)
        return rule_db

    @classmethod
    def create_reverse_rule(cls, data, parent_rule):
        reverse_enable = data.get("enableReverse", None)
        if reverse_enable:
            typeTime = data.get("typeTime", None)
            reverse_action = data.get("reverse_action", None)

            # Create Reverse Rule
            reverse_rule = Rules()
            if parent_rule.child_rule.all().count() > 0:
                reverse_rule = parent_rule.child_rule.get()
            reverse_rule.name = format(parent_rule.name)
            reverse_rule.cluster = parent_rule.cluster
            reverse_rule.rule = dict({})
            reverse_rule.action = reverse_action
            reverse_rule.run_type = typeTime
            reverse_rule.parent_rule = parent_rule
            if typeTime.upper() == DAILY:
                reverse_rule.run_type = DAILY
                reverse_rule.run_at = data.get("reverseDailyTime", None)
            else:
                reverse_rule.run_type = CRON
                reverse_rule.run_at = data.get("reverseCronTime", None)
            reverse_rule.save()
            CronUtil.create_cron(reverse_rule)
        else:
            if parent_rule.child_rule.all().count() > 0:
                for rule in parent_rule.child_rule.all():
                    CronUtil.delete_cron(rule)
                    rule.delete()

    def more_retries_allowed(self,attempts):
        retry = self.rule_json.get("retry", None)
        if retry is not None:
            # attempts includes the first attempt, which isn't technically a "retry",
            # so use >= to take that into account (i.e. if we allow one retry, we only
            # return false when attempts > 2)
            if int(retry.get("retry_max")) >= attempts:
                return True
            else:
                logger.debug(f"Looks like our threshold of {retry.get('retry_max')} retries was hit on attempt {attempts}")
        return False

    def check_exception_date(self):
        try:
            exception_date_data = ExceptionData.objects.get(exception_date=timezone.now().date())
            # Check existing cluster is present in exception or not
            for cluster in exception_date_data.clusters:
                if self.cluster.id == cluster["id"]:
                    msg = "{} is listed as exception date for this cluster. Hence not applying rule".format(
                        str(timezone.now().date()))
                    logger.error(msg)
                    raise Exception("Rule execution on Cluster: {} is excluded for date: {}".format(
                        self.cluster.name, timezone.now().date()))
            return True
        except ExceptionData.DoesNotExist:
            pass

    def apply_rule(self, attempt):
        # Check rule is Reverse Rule or not
        if self.is_reverse:
            self.reverse_rule(attempt)
        else:
            self.__apply_rule(attempt)

    def __apply_rule(self, attempt):
        db_instances = dict()
        db_avg_load = dict()
        all_good = False
        try:
            for db in self.secondary_dbs:
                helper = DbHelper(db)
                logger.debug(f"Adding instance {db.instance_id} ({helper.instance.instanceType}) to secondaries")
                try:
                    helper.check_replication_lag(self.rule_json)
                except:
                    logger.warn(f"skipping {db.instance_id} because it failed a replication lag check")
                    next
                try:
                    helper.check_connections(self.rule_json)
                except:
                    logger.warn(f"skipping {db.instance_id} because it failed an active connection count check")
                    next
                # helper.check_active_user_connections()
                db_instances[db.id] = helper
                db_avg_load[db.id] = helper.get_system_load_avg()
            if len(db_instances) == 0:
                raise Exception("No secondaries passed replication and active connection count checks.")

            logger.debug(f"Primary DB is {self.primary_dbs[0].instance_id}")
            # Check cluster load
            if self._is_cluster_managed and self.cluster_mgmt.avg_load:
                logger.debug(f"Dealing with managed cluster")
                primary_helper = DbHelper(self.primary_dbs[0])
                aggregated_avg_load = primary_helper.get_system_load_avg()
                logger.info(f"Discovered primary to have load average of {aggregated_avg_load}")

                changed_replicas = 0
                for id, replica_avg_load in db_avg_load.items():
                    logger.info(f"Working on {db_instances[id].instance.instanceId} with a load of {replica_avg_load} using aggregated primary load of {aggregated_avg_load}")
                    try:
                        if db_instances[id].check_average_load(self.rule_json, aggregated_avg_load):
                            logger.info(f"combined load of {str(round(aggregated_avg_load + replica_avg_load,2))} compares with a managed target load of {str(self.cluster_mgmt.avg_load)}")
                            self.__check_open_connections(db_instances[id])
                            # We are good to proceed.
                            if self.action == SCALE_DOWN:
                                # If we are going to downsize, update our DNS entries before we downsize,
                                # so that we can get load off of our replica(s) before resizing.
                                self.update_dns_entries(db_instances[id])
                                self.run_pre_resize_script(db_instances[id].instance.instanceId)
                                db_instances[id].update_instance_type(self.new_instance_type, self.fallback_instances)
                                aggregated_avg_load += replica_avg_load

                                # Because we're scaling down and have moved load off of this node,
                                # we don't need to wait for the client's sake that streaming has resumed before continuing.
                                # But for the post-streaming script, which might get used to re-enable monitoring,
                                # we should wait to make sure the replication is working again before we run it.
                                db_instances[id].wait_till_replica_streaming()
                                self.run_post_streaming_script(db_instances[id].instance.instanceId)
                            else:
                                # If we are going to upsize, update our DNS entry after we upsize,
                                # so that we can make sure the upsized instance is ready to rock before it
                                # sees any new clients.
                                self.run_pre_resize_script(db_instances[id].instance.instanceId)
                                db_instances[id].update_instance_type(self.new_instance_type, self.fallback_instances)

                                # We need to make sure streaming has resumed before we say we are ready for clients
                                db_instances[id].wait_till_replica_streaming()

                                # Now that replication is working, we should be go to run the post-streaming script.
                                self.run_post_streaming_script(db_instances[id].instance.instanceId)

                                self.update_dns_entries(db_instances[id])
                                aggregated_avg_load -= replica_avg_load

                            changed_replicas += 1
                        else:
                            logger.info(f"Not going to resize because combined load of {str(round(aggregated_avg_load + replica_avg_load,2))} compares with a managed target load of {str(self.cluster_mgmt.avg_load)}")
                    except Exception as e:
                        logger.info(f"Not going to resize because {e}")

                if changed_replicas == 0:
                    raise Exception("Failed to resize any replicas.")
            else:
                logger.info(f"Managed cluster is {self._is_cluster_managed} and avg_load is {self.cluster_mgmt.avg_load}")
                for id, helper in db_instances.items():
                    helper.check_average_load(self.rule_json)
                    self.__check_open_connections(helper)
                    helper.update_instance_type(self.new_instance_type, self.fallback_instances)
                    self.update_dns_entries(helper)
            all_good = True
        except Exception as e:
            logger.error(f"#Rule {self.rule.id}: Failed to apply because {e}")
            raise e
        finally:
            if not all_good:
                CronUtil.set_retry_cron(self.rule, attempt)

    def reverse_rule(self):
        try:
            for db in self.secondary_dbs:
                db_helper = DbHelper(db)
                self.__check_open_connections(db_helper)
                db_helper.update_instance_type(db.last_instance_type, self.fallback_instances)
                self.update_dns_entries(db_helper)
        except Exception as e:
            logger.error("Reverse #Rule {}: Failed to apply", self.rule.id)
            CronUtil.set_retry_cron(self.rule, attempt)

    def __check_open_connections(self, db_helper):
        if self.action == SCALE_DOWN:
            if self.cluster_mgmt and self.cluster_mgmt.check_active_users:
                users = self.cluster_mgmt.check_active_users
                active_connections = db_helper.get_no_of_connections(users)
                if active_connections > 0:
                    logger.error("{} active connections are open for users {}".format(active_connections, users))
                    raise Exception("There are active connections from {} users.".format(str(users)))
        return True

    def update_dns_entries(self, helper):
        logger.info(f"updating dns entries for {self.action} of {helper.instance.instanceId}")
        if hasattr(helper.db_info, "dns_entry"):
            if self.action == SCALE_DOWN:
                dns_address = self.get_primary_address()
            else:
                dns_address = helper.get_endpoint_address()
            self.run_dns_script(helper.db_info, dns_address, helper.get_endpoint_address())
        else:
            logger.warn(f"not updating dns because {helper.db_info.id} has no dns_entry attribute")
        return None

    def get_primary_address(self):
        if self.primary_dbs.count() > 0:
            helper = DbHelper(self.primary_dbs[0])
            return helper.get_endpoint_address()
        else:
            logger.error("NO primary db present for cluster {}".format(self.cluster.name))

    def run_dns_script(self, instance, target_address, replica_address):
        """
        Run dns script only when dns entry present
        """
        if sys.platform == "win32":
            return

        if self.cluster_type == EC2:
            RECORD_TYPE = "A"
        else:
            RECORD_TYPE = "CNAME"

        zone_name = instance.dns_entry.hosted_zone_name
        dns_name = instance.dns_entry.dns_name

        script_path = os.path.join(settings.BASE_DIR, "scripts", "dns-change.sh")

        try:
            DB_CRED = DbCredentials.objects.get(description="AWS Secrets")
            env_var = dict({
                "AWS_ACCESS_KEY_ID": DB_CRED.user_name,
                "AWS_SECRET_ACCESS_KEY": DB_CRED.password
            })
        except:
            env_var = dict()

        try:
            logger.info(f"Changing DNS instance {dns_name} ({replica_address}) to point at {target_address}")
            test = subprocess.check_output([script_path, self.action, zone_name, dns_name, target_address, RECORD_TYPE, replica_address], env=env_var)
            if len(test) > 0:
                logger.info(f"running {script_path} {self.action} {zone_name} {dns_name} {target_address} {RECORD_TYPE} {replica_address} succeeded with non-empty result of {test}")
            else:
                logger.debug(f"running {script_path} {self.action} {zone_name} {dns_name} {target_address} {RECORD_TYPE} {replica_address} succeeded")
        except subprocess.CalledProcessError as e:
            logger.info(f"running {script_path} {self.action} {zone_name} {dns_name} {target_address} {RECORD_TYPE} {replica_address} returned: {e.returncode} ({e.output})")
        except Exception as e:
            if hasattr(e, 'message'):
                message = e.message
            else:
                message = e
            logger.info(f"running {script_path} {self.action} {zone_name} {dns_name} {target_address} {RECORD_TYPE} {replica_address} returned generic error: {message}")

    def run_pre_resize_script(self, instance_id):
        script_path = os.path.join(settings.BASE_DIR, "scripts", "pre-resize.sh")

        try:
            DB_CRED = DbCredentials.objects.get(description="AWS Secrets")
            env_var = dict({
                "AWS_ACCESS_KEY_ID": DB_CRED.user_name,
                "AWS_SECRET_ACCESS_KEY": DB_CRED.password
            })
        except:
            env_var = dict()

        try:
            logger.info(f"Running pre-resize hook for {instance_id}")
            test = subprocess.check_output([script_path, instance_id], env=env_var)
            if len(test) > 0:
                logger.info(f"running {script_path} {instance_id} succeeded with non-empty result of {test}")
            else:
                logger.debug(f"running {script_path} {instance_id} succeeded")
        except subprocess.CalledProcessError as e:
            logger.info(f"running {script_path} {instance_id} returned: {e.returncode} ({e.output})")
            raise e
        except Exception as e:
            if hasattr(e, 'message'):
                message = e.message
            else:
                message = e
            logger.info(f"running {script_path} {instance_id} returned generic error: {message}")
            raise e

    def run_post_streaming_script(self, instance_id):
        script_path = os.path.join(settings.BASE_DIR, "scripts", "post-streaming.sh")

        try:
            DB_CRED = DbCredentials.objects.get(description="AWS Secrets")
            env_var = dict({
                "AWS_ACCESS_KEY_ID": DB_CRED.user_name,
                "AWS_SECRET_ACCESS_KEY": DB_CRED.password
            })
        except:
            env_var = dict()

        try:
            logger.info(f"Running post-streaming hook for {instance_id}")
            test = subprocess.check_output([script_path, instance_id], env=env_var)
            if len(test) > 0:
                logger.info(f"running {script_path} {instance_id} succeeded with non-empty result of {test}")
            else:
                logger.debug(f"running {script_path} {instance_id} succeeded")
        except subprocess.CalledProcessError as e:
            logger.info(f"running {script_path} {instance_id} returned: {e.returncode} ({e.output})")
            raise e
        except Exception as e:
            if hasattr(e, 'message'):
                message = e.message
            else:
                message = e
            logger.info(f"running {script_path} {instance_id} returned generic error: {message}")
            raise e
