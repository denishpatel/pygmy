from engine.models import Rules, RDS, Ec2DbInfo


class RuleHelper:

    def __init__(self, rule):
        self.rule_json = self.rule.rule
        self.action = rule.action  # SCALE_DOWN or SCALE_UP
        self.cluster_type = rule.cluster.type
        self.new_instance_type = self.rule_json.get("rds_type") if self.rule.cluster.type == RDS else self.rule_json.get("ec2_type")
        self.secondary_dbs = Ec2DbInfo.objects.filter(cluster=self.rule.cluster, isPrimary=False)
        self.primary_dbs = Ec2DbInfo.objects.filter(cluster=self.rule.cluster, isPrimary=True)
        self.cluster_mgmt = self.rule.cluster.load_management

    @classmethod
    def from_id(cls, rule_id):
        rule = Rules.objects.get(id=rule_id)
        return cls(rule)

    def demo(self):
        pass