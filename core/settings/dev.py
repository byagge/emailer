from .base import *
import os

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-u*57za2ej94u5*k+eji8#od7bi-*-8qiqif4(j#(58_0=lt1-a"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

try:
    from .local import *
except ImportError:
    pass
