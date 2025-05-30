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

    # --- AUTO-CREATE SUPERUSER BLOCK (enable via env var) ---
    if os.environ.get('CREATE_SUPERUSER') == 'true':
        try:
            import django
            django.setup()
            from django.contrib.auth import get_user_model
            User = get_user_model()

            # параметры суперпользователя
            username_field = User.USERNAME_FIELD
            email = 'admin@admin.com'
            password = 'admin123'

            # собираем аргументы для create_superuser()
            create_kwargs = {username_field: email, 'password': password}
            for field in getattr(User, 'REQUIRED_FIELDS', []):
                if field != username_field:
                    create_kwargs[field] = 'admin'

            # проверяем, есть ли уже такой пользователь
            lookup = {username_field: create_kwargs[username_field]}
            if not User.objects.filter(**lookup).exists():
                print("🛠️ Creating superuser...")
                User.objects.create_superuser(**create_kwargs)
                print("✅ Superuser created.")
        except Exception as e:
            print(f"⚠️ Error creating superuser: {e}")
    # -------------------------------------------------------

    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
