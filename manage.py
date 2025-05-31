#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # --- AUTO-CREATE SUPERUSER BLOCK ---
    if os.environ.get('CREATE_SUPERUSER') == 'true':
        try:
            import django
            django.setup()
            from django.contrib.auth import get_user_model
            User = get_user_model()

            email = 'admin@admin.com'
            password = 'admin123'

            if not User.objects.filter(email=email).exists():
                print("🛠️ Creating superuser...")
                User.objects.create_superuser(email=email, password=password)
                print("✅ Superuser created.")
            else:
                print("ℹ️ Superuser already exists.")
        except Exception as e:
            print(f"⚠️ Error creating superuser: {e}")
    # -------------------------------------------------------

    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
