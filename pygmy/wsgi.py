"""
WSGI config for pygmy project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pygmy.settings')

application = get_wsgi_application()

from engine.management.commands.populate_settings_data import Command
# Populate settings
# Command.populate_settings()