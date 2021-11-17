import re
import logging


class DBHandler(logging.Handler):
    backup_logger = "test"

    def emit(self, record: logging.LogRecord) -> None:
        from pygmy.models import Log
        try:
            message = self.format(record)
            try:
                last_line = message.rsplit("\n", 1)[-1]
            except Exception as e:
                last_line = None
            try:
                # Log = apps.get_model("pygmy.models", "Log")
                new_log = Log(
                    level_name=record.levelname,
                    module=record.module,
                    message=message,
                    last_line=last_line)

                if last_line:
                    new_log.object = self.check_rule_id(last_line)

                new_log.save()
            except Exception as e:
                if self.backup_logger:
                    try:
                        getattr(self.backup_logger, record.levelname.lower())(record.message)
                    except Exception as e:
                        print(e)
                else:
                    print(e)
        except Exception as e:
            print(e)

    def check_rule_id(self, last_line):
        from engine.models import Rules
        check_rule_id = re.match(r"#Rule[\s](\d+)", last_line)
        if check_rule_id:
            rule_id = (check_rule_id.group())
            try:
                return Rules.objects.get(id=rule_id)
            except Rules.DoesNotExits:
                pass
        return None
