from django.utils import timezone
from django.db import transaction
from django.core.management import BaseCommand
from django.contrib.humanize.templatetags.humanize import ordinal
from engine.rules.logger_utils import ActionLogger
from engine.rules.rules_helper import RuleHelper
from engine.models import Rules, ActionLogs, ClusterInfo, Ec2DbInfo, AllEc2InstancesData
from engine.aws.ec_wrapper import EC2Service
from engine.rules.cronutils import CronUtil
import os
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('rule_id', nargs='+', type=int, help="Rule id to run. You can provide multiple "
                            "rule ids to run multiple rule")

    def handle(self, *args, **kwargs):
        logger.debug(os.environ)
        msg = ""
        for rid in kwargs['rule_id']:
            self.try_rule(rid)

    @transaction.atomic()
    def try_rule(self, rid):
        too_many_cooks = False
        aborted = False

        # Make a dummy helper variable in case we error out for some reason.
        helper = None
        msg = None
        try:
            try:
                rule_db = Rules.objects.select_for_update(skip_locked=True).get(id=rid)
            except Exception as e:
                # The rule might not exist, or might be merely locked.
                # If this get fails it's because it doesn't exist for real, and we can let our normal exception handling below have its way.
                unlocked_rule_db = Rules.objects.get(id=rid)
                # If we get here, though, we know it's merely locked and currently being worked on.
                # Sadly we don't know much other than that, because nothing has been committed yet
                logger.error(f"Refusing to run locked rule because it is currently being worked")
                too_many_cooks = True
                return

            if rule_db.working_pid is not None:
                # Probably started a while ago, so try to be helpful and report the delta in minutes, not seconds
                logger.error(f"Refusing to run stale rule because pid {rule_db.working_pid} started this rule at {rule_db.last_started} ({int((timezone.now().timestamp()-rule_db.last_started.timestamp())/60)} minutes ago)")
                too_many_cooks = True
                return
            else:
                ActionLogger.add_log(rule_db, f"Rule {rid} execution is started by pid {os.getpid()}")

            logger.debug(f"Successfully locked rule {rid} ({rule_db.name})")
            rule_db.attempts += 1
            rule_db.working_pid = os.getpid()
            rule_db.last_started = timezone.now()
            rule_db.save()

            # Now that we have our rule row locked, also lock the cluster, and the nodes of the cluster
            # By locking the cluster we make sure no other rule that affects the same cluster can run concurrently,
            # and by locking the nodes we do the same thing for get_all_db_data.
            try:
                cluster = ClusterInfo.objects.select_for_update(skip_locked=True).get(id=rule_db.cluster_id)
            except ClusterInfo.DoesNotExist:
                # We know the cluster *exists* (thanks foreign keys!) so it must be locked by something else.
                # This rule run was not meant to be.
                # Queue it up for retry if we can.
                logger.error(f"Refusing to run because cluster {rule_db.cluster_id} is currently locked by something else.")
                CronUtil.set_retry_cron(rule_db, rule_db.attempts)
                return
            except Exception as e:
                logger.error(f"Refusing to run because cluster of an unexpected error trying to lock ClusterInfo {rule_db.cluster_id}: {e}")
                return

            logger.debug(f"Successfully locked cluster {cluster.id} ({cluster.name})")
            if cluster.enabled is False:
                logger.error(f"Not going to work on cluster {cluster.name} because it has been disabled.")
                aborted = True
                return

            try:
                # TODO: Make sure rows are locked by id order, so that we don't get some kind of deadlock
                # We intentionally don't skip locked rows, because we don't know how many we should have and we want to make sure we lock them all.
                nodes = Ec2DbInfo.objects.select_for_update().filter(cluster_id=rule_db.cluster_id)
            except Exception as e:
                logger.error(f"Refusing to run because we failed to lock our ec2dbinfo rows for cluster {rule_db.cluster_id}: {e}")
                aborted = True
                return

            nodeData = dict()
            for node in nodes:
                logger.debug(f"Successfully locked ec2dbinfo {node.id} ({node.instance_id})")
                try:
                    # Now lock the cached info about this node
                    # TODO: Make this work for RDS
                    nodeData[node.instance_id] = AllEc2InstancesData.objects.select_for_update().get(instanceId=node.instance_id)
                    logger.debug(f"Successfully locked AllEc2InstancesData row for instance {node.instance_id}")
                except AllEc2InstancesData.DoesNotExist:
                    logger.debug(f"We couldn't lock {node.instance_id} because it doesn't exist. That shouldn't be a problem.")
                except Exception as e:
                    logger.error(f"Refusing to run because we failed to lock our ec2 instance data row for instance {node.instance_id}: {e}")
                    aborted = True
                    return

            # Now that we have all the rows locked that we're going to need, update our instances related to the cluster and their types
            tag_project = cluster.name.split('-')[0].capitalize()
            tag_environment = cluster.name.split('-')[1].capitalize()
            tag_cluster = cluster.name.split('-')[2]  # yay snowflakes! We don't want this capitalized.
            logger.debug(f"refreshing ec2 data for {tag_project} {tag_environment} {tag_cluster}")
            tag_filters = [
                {
                    'Name': 'tag:Project',
                    'Values': [tag_project]
                },
                {
                    'Name': 'tag:Environment',
                    'Values': [tag_environment]
                },
                {
                    'Name': 'tag:Cluster',
                    'Values': [tag_cluster]
                }]

            # we probably want to wrap this all in a function, and not cut-n-paste from get_all_db_data.py
            try:
                logger.debug("Starting refresh of EC2 instances")
                ec2_service = EC2Service()
                new_instances = ec2_service.get_instances(extra_filters=tag_filters, update_sync_time=False)
                logger.debug(f"Our new instances are {new_instances}")
                for node in nodes:
                    if node.instance_id in new_instances:
                        logger.debug(f"instance {node.instance_id} (currently {new_instances[node.instance_id]['instance_type']}) remains part of this cluster.")
                        resizedNode = Ec2DbInfo.objects.get(instance_id=node.instance_id)
                        if resizedNode.last_instance_type != new_instances[node.instance_id]['instance_type']:
                            logger.warn(f"Was {resizedNode.last_instance_type}; is now {new_instances[node.instance_id]['instance_type']}")
                            resizedNode.last_instance_type = new_instances[node.instance_id]['instance_type']
                            resizedNode.save()
                    else:
                        logger.debug(f"instance {node.instance_id} no longer seems to be part of the cluster. Killing it.")
                        try:
                            Ec2DbInfo.objects.get(instance_id=node.instance_id).delete()
                        except Exception as e:
                            logger.error(f"Couldn't delete stale node {node.instance_id} from Ec2DbInfo becase {e}")
                        try:
                            AllEc2InstancesData.objects.get(instanceId=node.instance_id).delete()
                        except Exception as e:
                            logger.error(f"Couldn't delete stale node {node.instance_id} from AllEc2InstancesData becase {e}")
                logger.debug("EC2 instances successfully refreshed")

                # TODO: also support RDS
            except Exception as e:
                logger.exception(f"Failed to refresh db nodes: {e}")
                aborted = True
                return

            # Now that we have updated any data we might want, finally instantiate a RuleHelper (which will go pull our recently-refreshed DB instance type data)
            helper = RuleHelper.from_id(rid)
            helper.check_exception_date()

            helper.apply_rule(rule_db.attempts)
            rule_db.status = True
            rule_db.err_msg = ""
            msg = "Successfully Executed Rule"
            logger.info("Rule has completed successfully")
        except Exception as e:
            rule_db.status = False
            rule_db.err_msg = e
            msg = f"Exception caused rule failure: {e}"
            logger.error(f"Got an exception when running the rule: {e}")
        finally:
            logger.debug("Wrapping up rule run")

            if helper is None:
                # Make a RuleHelper. It might not have the most recent EC2 information,
                # because if we've gotten here and still don't have a RuleHelper we clearly skipped over the EC2 refresh,
                # but all we need it for is to check if more retries are allowed.
                helper = RuleHelper.from_id(rid)

            if too_many_cooks is False:
                # Given that we were able to lock the rule, then regardless of success, we have some cleanup to do
                previous_attempts = rule_db.attempts

                # ..but maybe we did have a successful run?
                if aborted is False and rule_db.status:
                    logger.debug("cleaning up rule upon successful completion")
                    CronUtil.delete_retry_cron(rid)
                    rule_db.attempts = 0
                else:
                    if helper.more_retries_allowed(rule_db.attempts) is False:
                        rule_db.attempts = 0
                        logger.warn(f"Refusing to retry again after {previous_attempts} attempts")
                    else:
                        logger.debug(f"Rule didn't complete successfully; will the {ordinal(rule_db.attempts)} retry be the charm?")

                # Now that the retry count has been tweaked, pretend that we. were. never. here.
                logger.debug("cleaning out rule pid")
                rule_db.working_pid = None
                rule_db.last_run = timezone.now()
                rule_db.save()
                if msg is not None:
                    self.add_log_entry(rule_db, msg)

    def add_log_entry(self, rule, msg, extra_info=None):
        # Add Log entry
        log = ActionLogs()
        log.rule = rule
        log.msg = msg
        log.status = rule.status
        log.save()
