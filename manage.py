import re
import dns.resolver
from .models import Contact
import requests
import threading
import time

# Регулярка для синтаксиса e-mail
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Здесь пока пустое множество, будем заполнять лениво
DISPOSABLE_DOMAINS = set()
_DOMAINS_LOADED = False
_LOCK = threading.Lock()

def _load_disposable_domains():
    """
    Внутренняя функция, один раз скачивает domains.txt и заполняет DISPOSABLE_DOMAINS.
    """
    global DISPOSABLE_DOMAINS, _DOMAINS_LOADED
    url = "https://raw.githubusercontent.com/disposable/disposable-email-domains/master/domains.txt"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            domains = set(
                line.strip().lower()
                for line in response.text.splitlines()
                if line.strip()
            )
            with _LOCK:
                DISPOSABLE_DOMAINS = domains
                _DOMAINS_LOADED = True
            print(f"[email_utils] {len(domains)} доменов загружено.")
        else:
            with _LOCK:
                DISPOSABLE_DOMAINS = set()
                _DOMAINS_LOADED = True
            print("[email_utils] Не удалось загрузить список (status_code != 200).")
    except Exception as e:
        with _LOCK:
            DISPOSABLE_DOMAINS = set()
            _DOMAINS_LOADED = True
        print(f"[email_utils] Ошибка при загрузке списка: {e}")

def get_disposable_domains():
    """
    Возвращает множество DISPOSABLE_DOMAINS. Если ещё не загружали,
    загружает единожды в отдельном потоке (чтобы не блокировать основной поток).
    """
    global _DOMAINS_LOADED
    if not _DOMAINS_LOADED:
        # Запускаем фоновую загрузку один раз
        threading.Thread(target=_load_disposable_domains, daemon=True).start()
        # Можно сразу вернуть пустой набор, а наполнение произойдёт в фоне.
        return set()
    return DISPOSABLE_DOMAINS


def parse_emails(file_stream, filename=None):
    """
    Возвращаем **все** непустые строки из файла.
    Классификация будет уже в classify_email.
    """
    raw = file_stream.read()
    try:
        text = raw.decode('utf-8', errors='ignore')
    except AttributeError:
        text = raw if isinstance(raw, str) else raw.decode('utf-8', errors='ignore')

    lines = text.splitlines()
    # Берём **все** непустые, без фильтра по EMAIL_REGEX
    return [line.strip() for line in lines if line.strip()]


def is_syntax_valid(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email))


def has_mx_record(domain: str) -> bool:
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        return len(answers) > 0
    except Exception:
        return False


def classify_email(email: str) -> str:
    """
    Классифицирует **любой** email:
      1) Синтаксис → INVALID
      2) Временный/дроп-домен → BLACKLIST
      3) Нет MX → INVALID
      4) Иначе → VALID
    """
    # 1) синтаксис (если не проходит — INVALID)
    if not EMAIL_REGEX.match(email):
        return Contact.INVALID

    # 2) disposable домен
    domain = email.split('@', 1)[1].lower()
    disposable = get_disposable_domains()
    # Если ещё не загрузили, можно подождать 1–2 секунды или считать, что домен временный невалиден.
    if domain in disposable:
        return Contact.BLACKLIST

    # 3) MX-запись
    if not has_mx_record(domain):
        return Contact.INVALID

    # 4) ок
    return Contact.VALID
