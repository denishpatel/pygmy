from engine.models import ActionLogs


class ActionLogger:

    def __init__(self):
        pass

    @staticmethod
    def add_log(rule, msg):
        log = ActionLogs()
        log.rule = rule
        log.msg = msg
        log.save()
