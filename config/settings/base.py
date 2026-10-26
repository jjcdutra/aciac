"""
Configurações base do projeto.
Sobrescritas por dev.py ou prod.py conforme DJANGO_SETTINGS_MODULE.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-only-key")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Apps locais
    "apps.core",
    "apps.associados",
    "apps.consultas",
    "apps.solicitacoes",
    "apps.pagamentos",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.identidade",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Banco: SQLite por padrão (dev local). Prod/docker usa POSTGRES_* do .env.
if env("POSTGRES_HOST", default=""):
    DATABASES = {
        "default": env.db(
            "DATABASE_URL",
            default=f"postgresql://{env('POSTGRES_USER')}:{env('POSTGRES_PASSWORD')}"
            f"@{env('POSTGRES_HOST')}:{env('POSTGRES_PORT', default='5432')}/{env('POSTGRES_DB')}",
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "associados.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "associados:login"
LOGIN_REDIRECT_URL = "associados:painel"
LOGOUT_REDIRECT_URL = "core:home"

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# === E-mail ===
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@associacao.com.br")

# === Identidade da associação (configurável via .env) ===
ASSOCIACAO = {
    "NOME": env("ASSOCIACAO_NOME", default="Associação Comercial"),
    "CIDADE": env("ASSOCIACAO_CIDADE", default="SAO PAULO"),
    "UF": env("ASSOCIACAO_UF", default="SP"),
    "TELEFONE": env("ASSOCIACAO_TELEFONE", default="(11) 3000-0000"),
    "EMAIL": env("ASSOCIACAO_EMAIL", default="contato@associacao.com.br"),
    "PIX_CHAVE": env("ASSOCIACAO_PIX_CHAVE", default=""),
}

# === Valores dos serviços (BRL, configuráveis via .env) ===
VALORES = {
    "TAXA_ASSOCIACAO": env.float("TAXA_ASSOCIACAO_VALOR", default=120.00),
    "CERTIFICADO_DIGITAL": env.float("CERTIFICADO_DIGITAL_VALOR", default=350.00),
}

# === Consulta CPF/CNPJ ===
CONSULTA = {
    "RATE_LIMIT": env.int("CONSULTA_RATE_LIMIT", default=10),  # por minuto, por IP
    "CACHE_HORAS": env.int("CONSULTA_CACHE_HORAS", default=24),
    "SERPRO_API_TOKEN": env("SERPRO_API_TOKEN", default=""),
    "SERPRO_API_URL": env("SERPRO_API_URL", default=""),
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "associacao-cache",
    }
}

# === Segurança base (produção sobrescreve em prod.py) ===
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
