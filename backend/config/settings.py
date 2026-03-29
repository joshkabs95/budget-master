from pathlib import Path
from datetime import timedelta
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
import sys
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')
if 'test' in sys.argv:
    ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'jazzmin',
    'django_prometheus',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'apps.users',
    'apps.categories',
    'apps.transactions',
    'apps.savings',
    'apps.goals',
    'apps.documents',
    'apps.forecasting',
    'apps.notifications',
    'apps.reconciliation',
    'apps.accounts',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': False,
        'OPTIONS': {
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

_DB_ENGINE = config('DB_ENGINE', default='sqlite')

if _DB_ENGINE == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='budgetmaster'),
            'USER': config('DB_USER', default='budgetmaster'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='db'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

FRONTEND_DIR = BASE_DIR.parent / 'frontend' / 'dist'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'

_domain = config('DOMAIN', default='localhost')
CORS_ALLOWED_ORIGINS = [
    f"https://{_domain}",
    f"http://{_domain}",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

# Security headers (activés en production)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 200,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/minute',
        'user': '300/minute',
    },
}

if 'test' in sys.argv:
    REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
    REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# ── Celery ──────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = config('REDIS_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    'spawn-recurring-1st-of-month': {
        'task': 'apps.notifications.tasks.spawn_recurring_transactions',
        'schedule': crontab(hour=6, minute=0, day_of_month=1),
    },
    'daily-budget-check': {
        'task': 'apps.notifications.tasks.daily_budget_check',
        'schedule': crontab(hour=8, minute=0),
    },
    'monthly-recap-last-day': {
        'task': 'apps.notifications.tasks.monthly_recap',
        'schedule': crontab(hour=20, minute=0, day_of_month='28-31'),
    },
}

# ── Email ───────────────────────────────────────────────────────────────────
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Budget Master <noreply@budgetmaster.app>')

# ── Jazzmin (Admin UI) ───────────────────────────────────────────────────────
JAZZMIN_SETTINGS = {
    # Titre de l'onglet navigateur
    "site_title": "Budget Master Admin",
    "site_header": "Budget Master",
    "site_brand": "BudgetMaster",
    "welcome_sign": "Bienvenue sur le panneau d'administration",
    "copyright": "Budget Master",

    # Icône dans la barre latérale (FontAwesome 5)
    "site_icon": None,
    "site_logo": None,
    "site_logo_classes": None,

    # Lien vers le site principal
    "site_url": "/",

    # Champ de recherche global (modèles fouillés)
    "search_model": ["users.User", "transactions.Transaction"],

    # Masquer les modèles dans la sidebar
    "hide_apps": [],
    "hide_models": [],

    # Ordre de la sidebar
    "order_with_respect_to": [
        "users",
        "transactions",
        "categories",
        "savings",
        "goals",
        "notifications",
        "documents",
    ],

    # Icônes par app/modèle
    "icons": {
        "auth":                          "fas fa-shield-alt",
        "users.user":                    "fas fa-user-circle",
        "transactions.transaction":      "fas fa-exchange-alt",
        "categories.category":           "fas fa-tags",
        "savings.savingsaccount":        "fas fa-piggy-bank",
        "savings.savingsrule":           "fas fa-sliders-h",
        "goals.goal":                    "fas fa-bullseye",
        "notifications.notification":    "fas fa-bell",
        "documents.document":            "fas fa-file-invoice",
        "token_blacklist.blacklistedtoken":  "fas fa-ban",
        "token_blacklist.outstandingtoken":  "fas fa-key",
    },
    "default_icon_parents": "fas fa-folder",
    "default_icon_children": "fas fa-circle",

    # Liens rapides en haut à droite
    "topmenu_links": [
        {"name": "Accueil", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Application", "url": "/", "new_window": True},
        {"model": "users.user"},
    ],

    # Liens dans la barre latérale (section utilisateur connecté)
    "usermenu_links": [
        {"model": "users.user"},
    ],

    # UI options
    "show_sidebar": True,
    "navigation_expanded": True,
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "users.user": "horizontal_tabs",
    },

    # CSS / JS personnalisés
    "custom_css": "admin/css/custom_admin.css",
    "custom_js": "admin/js/custom_admin.js",

    # Langue / i18n
    "language_chooser": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "navbar": "navbar-dark",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "darkly",       # thème Bootswatch sombre
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary":   "btn-primary",
        "secondary": "btn-secondary",
        "info":      "btn-info",
        "warning":   "btn-warning",
        "danger":    "btn-danger",
        "success":   "btn-success",
    },
}
