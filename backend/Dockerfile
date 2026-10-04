# syntax=docker/dockerfile:1
#
# One file, four images:
#   development          API, worker and scheduler on a developer machine
#   development-crawler  the same, plus Chromium for sites that need a browser
#   production           API, worker and scheduler, running as a non-root user
#   production-crawler   the same, plus Chromium
#
# Only the crawler carries Chromium. It adds about 1 GB, and nothing else needs it.

ARG PYTHON_VERSION=3.13

# ---------------------------------------------------------------- base
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

WORKDIR /app

RUN useradd --system --uid 10001 --create-home app \
    && mkdir -p /var/lib/hejobs/rawcache /var/lib/hejobs/media \
    && chown -R app:app /var/lib/hejobs

COPY docker/install-chromium.sh /usr/local/bin/install-chromium

# The package folders are created empty, so the dependency layer is cached.
# A change to the source code then does not reinstall every library.
COPY pyproject.toml ./
RUN for package in shared config accounts analytics institutions crawler jobs screening api; do \
        mkdir -p "$package" && touch "$package/__init__.py"; \
    done

# ---------------------------------------------------------------- development
FROM base AS development

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -e ".[dev]"

COPY . .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---------------------------------------------------------------- development-crawler
FROM development AS development-crawler

RUN install-chromium

CMD ["celery", "-A", "config", "worker", "--queues", "crawl", "--loglevel", "info"]

# ---------------------------------------------------------------- source
# Tests and fixtures are useful in development. They do not belong in a production image.
FROM base AS source

COPY . /source
RUN rm -rf /source/tests

# ---------------------------------------------------------------- production
FROM base AS production

ENV DJANGO_SETTINGS_MODULE=config.settings.production

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -e .

COPY --from=source --chown=app:app /source /app

# Static files are collected at build time. No real secret exists yet, so a placeholder is used.
RUN mkdir -p /app/staticfiles \
    && DJANGO_SECRET_KEY=build-time-only DJANGO_COLLECTSTATIC=1 \
       python manage.py collectstatic --noinput \
    && chown -R app:app /app/staticfiles

USER app

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--config", "docker/gunicorn.conf.py"]

# ---------------------------------------------------------------- production-crawler
FROM production AS production-crawler

USER root
RUN install-chromium
USER app

CMD ["celery", "-A", "config", "worker", "--queues", "crawl", "--loglevel", "info"]
