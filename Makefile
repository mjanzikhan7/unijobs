SHELL := /bin/bash
COMPOSE := docker compose
BACKEND := $(COMPOSE) run --rm -T backend
CRAWLER := $(COMPOSE) run --rm -T crawler
FRONTEND := $(COMPOSE) run --rm -T --no-deps frontend
PRODUCTION := docker compose -f compose.production.yaml

# Targets for a running stack that has a problem: doctor, backup, restore.
include operations/Makefile

.DEFAULT_GOAL := help
.PHONY: help up down logs ps shell dbshell migrate makemigrations seed seed-demo static-site crawl superuser \
        verify-user mail test test-backend test-frontend coverage e2e storybook lint lint-backend \
        lint-frontend fix schema types refresh-fixtures audit build-production check-deploy clean

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

up: ## Build and start the whole stack
	$(COMPOSE) up --build

down: ## Stop the stack and keep the data
	$(COMPOSE) down

logs: ## Follow the logs of every service
	$(COMPOSE) logs -f --tail=100

ps: ## Show service status
	$(COMPOSE) ps

shell: ## Open a Django shell
	$(COMPOSE) run --rm backend python manage.py shell

dbshell: ## Open psql
	$(COMPOSE) exec db psql -U $${POSTGRES_USER:-hejobs} -d $${POSTGRES_DB:-hejobs}

migrate: ## Apply database migrations
	$(BACKEND) python manage.py migrate

makemigrations: ## Create new migrations
	$(BACKEND) python manage.py makemigrations

seed: ## Load institutions, the sponsor register and the current ruleset (safe to repeat)
	$(BACKEND) python manage.py seed_all

seed-demo: ## Load a few demo vacancies
	$(BACKEND) python manage.py seed_demo_jobs

static-site: ## Write open vacancies as a static site (HTML, CSV, JSON, no JavaScript) to backend/static-site
	$(BACKEND) python manage.py export_static_site --out /app/static-site

crawl: ## Start a crawl from the command line
	$(CRAWLER) python manage.py crawl $(ARGS)

superuser: ## Create an administrator account
	$(COMPOSE) run --rm backend python manage.py createsuperuser

verify-user: ## Confirm an account without email: make verify-user ARGS="alice --role MANAGER"
	$(BACKEND) python manage.py verify_user $(ARGS)

mail: ## Where to read the emails this app sends
	@echo "Mailpit: http://localhost:8025"

test: test-backend test-frontend ## Run every test suite

test-backend: ## pytest, with the coverage check (a few tests start a real browser)
	$(CRAWLER) pytest $(ARGS)

test-frontend: ## vitest
	$(FRONTEND) npm run test -- --run

coverage: ## pytest with an HTML coverage report
	$(CRAWLER) pytest --cov-report=html

e2e: ## Playwright tests in their own container. The crawler is stopped, so no site is contacted
	$(COMPOSE) up -d --build --wait
	$(COMPOSE) stop crawler
	$(COMPOSE) exec -T backend python manage.py seed_test_users
	$(COMPOSE) --profile e2e run --rm --build e2e; status=$$?; $(COMPOSE) start crawler; exit $$status

storybook: ## The component catalogue
	cd frontend && npm run storybook

lint: lint-backend lint-frontend ## Run every linter

lint-backend:
	$(BACKEND) ruff check .
	$(BACKEND) ruff format --check .
	$(BACKEND) mypy screening crawler

lint-frontend:
	$(FRONTEND) npm run lint
	$(FRONTEND) npm run typecheck

fix: ## Fix what the tools can fix on their own
	$(BACKEND) ruff format .
	$(BACKEND) ruff check --fix .
	$(FRONTEND) npm run lint -- --fix

schema: ## Write the OpenAPI schema to backend/openapi.yaml
	$(BACKEND) python manage.py spectacular --file /app/openapi.yaml --fail-on-warn

types: schema ## Rebuild the frontend API types from the schema
	cp backend/openapi.yaml frontend/openapi.yaml
	$(FRONTEND) npm run generate:types; rm -f frontend/openapi.yaml

refresh-fixtures: ## Capture crawler pages again (uses the network, read the diff)
	$(CRAWLER) python manage.py refresh_fixtures $(ARGS)

audit: ## Check every dependency for known security problems
	$(BACKEND) pip-audit
	npm audit --omit=dev

build-production: ## Build the production images
	$(PRODUCTION) --env-file .env.production.example build

check-deploy: ## Run Django's deployment checks against the production settings
	$(BACKEND) env DJANGO_SETTINGS_MODULE=config.settings.production python manage.py check --deploy --fail-level WARNING

clean: ## Stop the stack and DELETE the database volume
	$(COMPOSE) down -v --remove-orphans
