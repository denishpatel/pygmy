"""
ASGI config for pygmy project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

from django.core.asgi import get_asgi_application
from engine.management.commands.populate_settings_data import Command

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pygmy.settings')

application = get_asgi_application()

# Populate settings
Command.populate_settings()
