from .base import *
import os

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-u*57za2ej94u5*k+eji8#od7bi-*-8qiqif4(j#(58_0=lt1-a"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

# ----------------------------------------
# Список доверенных Origin-доменов для CSRF
# (Replit может давать динамический URL вида *.sisko.replit.dev)
CSRF_TRUSTED_ORIGINS = [
    "https://c4af3c84-edef-48f6-83e7-1bc44d1738a9-00-3iztoy5c6sb7n.sisko.replit.dev",
    # Если у вас есть стабильный .repl.co-адрес, можно добавить его тоже:
    # "https://<имя-вашего-Repl>.<ваш-username>.repl.co",
]
# ----------------------------------------


try:
    from .local import *
except ImportError:
    pass
