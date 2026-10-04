"""Settings shared by every environment.

Put anything that differs between development, test and production in the module for that
environment, not behind an ``if DEBUG`` check here.
"""

from __future__ import annotations

from pathlib import Path

from celery.schedules import crontab

from config.env import env_bool, env_float, env_int, env_list, env_path, env_str

BASE_DIR = Path(__file__).resolve().parent.parent.parent


SECRET_KEY = env_str("DJANGO_SECRET_KEY", "insecure-development-key")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:5173")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
    "accounts",
    "analytics",
    "institutions",
    "crawler",
    "jobs",
    "screening",
    "api",
]

MIDDLEWARE = [
    "config.observability.RequestIdMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

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
            ],
        },
    },
]


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env_str("POSTGRES_DB", "hejobs"),
        "USER": env_str("POSTGRES_USER", "hejobs"),
        "PASSWORD": env_str("POSTGRES_PASSWORD", "hejobs"),
        "HOST": env_str("POSTGRES_HOST", "localhost"),
        "PORT": env_str("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "ATOMIC_REQUESTS": False,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = env_str("DJANGO_MEDIA_ROOT", str(BASE_DIR / ".media"))

CV_MAX_BYTES = env_int("CV_MAX_BYTES", 5 * 1024 * 1024)

DATA_UPLOAD_MAX_MEMORY_SIZE = CV_MAX_BYTES + (1024 * 1024)

DATA_UPLOAD_MAX_NUMBER_FIELDS = env_int("DATA_UPLOAD_MAX_NUMBER_FIELDS", 200)

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "api.authentication.RoleAwareTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["api.permissions.RoleRequired"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "api.pagination.DefaultPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "api.exceptions.exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env_str("THROTTLE_ANON", "60/min"),
        "user": env_str("THROTTLE_USER", "1000/hour"),
        "login": env_str("THROTTLE_LOGIN", "10/min"),
        "login_username": env_str("THROTTLE_LOGIN_USERNAME", "20/hour"),
        "register": env_str("THROTTLE_REGISTER", "5/hour"),
        "password_reset": env_str("THROTTLE_PASSWORD_RESET", "5/hour"),
        "cv_upload": env_str("THROTTLE_CV_UPLOAD", "10/hour"),
    },
}

SESSION_COOKIE_AGE = env_int("SESSION_COOKIE_AGE", 12 * 60 * 60)
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"

EMAIL_VERIFICATION_MAX_AGE_SECONDS = env_int("EMAIL_VERIFICATION_MAX_AGE_SECONDS", 48 * 3600)

ANALYTICS_RETENTION_DAYS = env_int("ANALYTICS_RETENTION_DAYS", 365)

UNVERIFIED_ACCOUNT_TTL_DAYS = env_int("UNVERIFIED_ACCOUNT_TTL_DAYS", 7)

FRONTEND_BASE_URL = env_str("FRONTEND_BASE_URL", "http://localhost:5173")

SPECTACULAR_SETTINGS = {
    "TITLE": "UniJobs API",
    "DESCRIPTION": "UK higher-education vacancies, screened for Skilled Worker sponsorship.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api",
    "ENUM_NAME_OVERRIDES": {
        "JobStatus": "jobs.enums.JOB_STATUS_CHOICES",
        "JobSource": "jobs.enums.JOB_SOURCE_CHOICES",
        "ContractType": "jobs.enums.CONTRACT_TYPE_CHOICES",
        "Hours": "jobs.enums.HOURS_CHOICES",
        "Workplace": "jobs.enums.WORKPLACE_CHOICES",
        "ApplicationStatus": "jobs.enums.APPLICATION_STATUS_CHOICES",
        "ChangeField": "jobs.enums.CHANGE_FIELD_CHOICES",
        "Discipline": "jobs.enums.DISCIPLINE_CHOICES",
        "CrawlTrigger": "crawler.enums.CRAWL_TRIGGER_CHOICES",
        "CrawlRunStatus": "crawler.enums.CRAWL_RUN_STATUS_CHOICES",
        "CrawlOutcome": "crawler.enums.CRAWL_OUTCOME_CHOICES",
        "ExtractionStrategy": "crawler.enums.EXTRACTION_STRATEGY_CHOICES",
        "SponsorVerdict": "screening.enums.SPONSOR_VERDICT_CHOICES",
        "ThresholdVerdict": "screening.enums.THRESHOLD_VERDICT_CHOICES",
        "SalaryConfidence": "screening.enums.SALARY_CONFIDENCE_CHOICES",
        "SalaryPeriod": "screening.enums.SALARY_PERIOD_CHOICES",
        "RulesetFigureKey": "screening.enums.RULESET_FIGURE_KEY_CHOICES",
        "MatchMethod": "screening.enums.MATCH_METHOD_CHOICES",
        "Role": "accounts.enums.ROLE_CHOICES",
        "EventKind": "analytics.enums.EVENT_KIND_CHOICES",
        "SkillTermKind": "screening.enums.SKILL_TERM_KIND_CHOICES",
        "Platform": "institutions.enums.PLATFORM_CHOICES",
        "Nation": "institutions.enums.NATION_CHOICES",
        "InstitutionType": "institutions.enums.INSTITUTION_TYPE_CHOICES",
    },
}

CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ALLOWED_ORIGINS", "http://localhost:5173")
CORS_ALLOW_CREDENTIALS = True


REDIS_URL = env_str("REDIS_URL", "redis://localhost:6379/0")

CACHE_URL = env_str("CACHE_URL", REDIS_URL.rsplit("/", 1)[0] + "/1")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": CACHE_URL,
    }
}
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = False
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_ROUTES = {"crawler.tasks.crawl_institution": {"queue": "crawl"}}
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50

CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60

CELERY_BEAT_SCHEDULE = {
    "scheduled-crawl": {
        "task": "crawler.tasks.scheduled_crawl",
        "schedule": crontab(hour="6,14,22", minute="0"),
    },
    "sweep-stalled-runs": {
        "task": "crawler.tasks.sweep_stalled_runs",
        "schedule": crontab(minute="*/10"),
    },
    "screen-unscreened-jobs": {
        "task": "crawler.tasks.screen_unscreened_jobs",
        "schedule": crontab(minute="*/10"),
    },
    "prune-raw-cache": {
        "task": "crawler.tasks.prune_raw_cache",
        "schedule": crontab(hour="4", minute="30"),
    },
    "prune-unverified-accounts": {
        "task": "accounts.tasks.prune_unverified_accounts",
        "schedule": crontab(hour="4", minute="45"),
    },
    "roll-up-search-terms": {
        "task": "analytics.tasks.roll_up_search_terms",
        "schedule": crontab(hour="3", minute="15"),
    },
    "prune-analytics-events": {
        "task": "analytics.tasks.prune_analytics_events",
        "schedule": crontab(hour="3", minute="45"),
    },
    "flag-ghosted-applications": {
        "task": "jobs.tasks.flag_ghosted_applications",
        "schedule": crontab(hour="7", minute="0"),
    },
    "refresh-search-vectors": {
        "task": "jobs.tasks.refresh_search_vectors",
        "schedule": crontab(hour="5", minute="30"),
    },
}


CRAWLER = {
    "CONTACT_EMAIL": env_str("CRAWLER_CONTACT_EMAIL", "you@example.com"),
    "USER_AGENT_NAME": env_str("CRAWLER_USER_AGENT_NAME", "HEJobPortal"),
    "HOST_CONCURRENCY": env_int("CRAWLER_HOST_CONCURRENCY", 8),
    "MIN_HOST_DELAY_SECONDS": env_float("CRAWLER_MIN_HOST_DELAY_SECONDS", 2.0),
    "HOST_DELAY_JITTER_SECONDS": env_float("CRAWLER_HOST_DELAY_JITTER_SECONDS", 0.5),
    "REQUEST_TIMEOUT_SECONDS": env_float("CRAWLER_REQUEST_TIMEOUT_SECONDS", 30.0),
    "MAX_RETRIES": env_int("CRAWLER_MAX_RETRIES", 3),
    "RAW_CACHE_DIR": env_path("CRAWLER_RAW_CACHE_DIR", str(BASE_DIR / ".rawcache")),
    "RAW_CACHE_TTL_DAYS": env_int("CRAWLER_RAW_CACHE_TTL_DAYS", 90),
    "PLAYWRIGHT_ENABLED": env_bool("CRAWLER_PLAYWRIGHT_ENABLED", True),
    "PLAYWRIGHT_TIMEOUT_MS": env_int("CRAWLER_PLAYWRIGHT_TIMEOUT_MS", 30_000),
    "RUN_STALE_AFTER_MINUTES": env_int("CRAWLER_RUN_STALE_AFTER_MINUTES", 90),
    "MAX_DETAIL_FETCHES_PER_INSTITUTION": env_int("CRAWLER_MAX_DETAIL_FETCHES_PER_INSTITUTION", 60),
}

SPONSOR_TRIGRAM_THRESHOLD = env_float("SPONSOR_TRIGRAM_THRESHOLD", 0.62)


DIGEST_ENABLED = env_bool("DIGEST_ENABLED", False)
DIGEST_TO_EMAIL = env_str("DIGEST_TO_EMAIL", "you@example.com")
DIGEST_CLOSING_SOON_DAYS = env_int("DIGEST_CLOSING_SOON_DAYS", 7)
DIGEST_MIN_FITNESS = env_int("DIGEST_MIN_FITNESS", 70)

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env_str("EMAIL_HOST", "localhost")
EMAIL_PORT = env_int("EMAIL_PORT", 1025)
EMAIL_HOST_USER = env_str("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env_str("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
DEFAULT_FROM_EMAIL = env_str("DEFAULT_FROM_EMAIL", "hejobs@localhost")


LOG_FORMAT = env_str("LOG_FORMAT", "text")
LOG_LEVEL = env_str("LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"request_id": {"()": "config.observability.RequestIdFilter"}},
    "formatters": {
        "text": {"format": "{levelname} {asctime} {name} [{request_id}] {message}", "style": "{"},
        "json": {"()": "config.observability.JsonFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": LOG_FORMAT if LOG_FORMAT in {"text", "json"} else "text",
            "filters": ["request_id"],
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.db.backends": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "crawler": {"level": LOG_LEVEL, "handlers": ["console"], "propagate": False},
        "screening": {"level": LOG_LEVEL, "handlers": ["console"], "propagate": False},
    },
}

METRICS_TOKEN = env_str("METRICS_TOKEN", "")
