from webapp.models import Settings, SYNC


def reset_sync_process_on_restart():
    sync_settings = Settings.objects.filter(type=SYNC)
    for setting in sync_settings:
        setting.in_progress = False
        setting.save()
