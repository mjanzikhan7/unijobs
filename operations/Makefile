# Targets for a stack that is already running: checks, backup and recovery.
#
# The root Makefile includes this file, so every target runs from the repository root.

OPS_DIR   := operations
BACKUP_DIR := $(OPS_DIR)/backups
PG_USER   := $${POSTGRES_USER:-hejobs}
PG_DB     := $${POSTGRES_DB:-hejobs}
STAMP     := $(shell date +%Y%m%d-%H%M%S)

.PHONY: doctor health crawl-status crawl-problems unstick rescreen \
        backup restore restore-list db-size prune disk \
        restart-frontend restart-workers logs-errors ops-help

# ---------------------------------------------------------------- diagnosis

doctor: ## Check everything that commonly breaks, in the order it breaks
	@./$(OPS_DIR)/bin/doctor.sh

health: ## One-line liveness check of every service
	@$(COMPOSE) ps --format 'table {{.Service}}\t{{.State}}\t{{.Status}}'

crawl-status: ## Last 10 crawl runs with their outcomes
	@$(COMPOSE) exec -T backend python manage.py shell -c "\
from crawler.models import CrawlRun; \
rows = CrawlRun.objects.order_by('-started_at')[:10]; \
print(f'{\"id\":>4}  {\"status\":<10} {\"done\":>7}  {\"new\":>5} {\"upd\":>5} {\"closed\":>6}  started'); \
[print(f'{r.id:>4}  {r.status:<10} {r.institutions_done:>3}/{r.institutions_total:<3}  {r.jobs_new:>5} {r.jobs_updated:>5} {r.jobs_closed:>6}  {r.started_at:%Y-%m-%d %H:%M}') for r in rows] or print('no runs yet')"

crawl-problems: ## Institutions that did not return OK on the most recent run
	@$(COMPOSE) exec -T backend python manage.py shell -c "\
from crawler.models import CrawlRun, CrawlRunInstitution; \
run = CrawlRun.objects.order_by('-started_at').first(); \
print('no runs yet') if not run else None; \
rows = CrawlRunInstitution.objects.filter(run=run).exclude(outcome='OK').select_related('institution') if run else []; \
print(f'run #{run.id}: {len(rows)} institution(s) not OK') if run else None; \
[print(f'  {r.outcome:<20} {r.institution.name[:44]:<46} {r.error_class or \"\"} {r.error_detail[:60]}') for r in rows]"

logs-errors: ## Recent errors and tracebacks across every service
	@$(COMPOSE) logs --no-color --tail 400 2>&1 \
	  | grep -iE 'error|exception|traceback|critical' \
	  | tail -40 || echo "  no errors in the last 400 lines"

# ---------------------------------------------------------------- recovery

unstick: ## Mark stalled RUNNING crawls as failed so a new one can start
	@$(COMPOSE) exec -T backend python manage.py shell -c "\
from django.utils import timezone; \
from datetime import timedelta; \
from crawler.models import CrawlRun; \
cutoff = timezone.now() - timedelta(minutes=30); \
stale = CrawlRun.objects.filter(status='RUNNING', heartbeat_at__lt=cutoff); \
n = stale.count(); \
stale.update(status='FAILED', finished_at=timezone.now(), error_detail='Marked failed by make unstick: no heartbeat for 30 minutes.'); \
print(f'released {n} stuck run(s)' if n else 'nothing stuck')"

rescreen: ## Recompute every verdict against the active ruleset (no network)
	$(BACKEND) python manage.py rescreen $(ARGS)

restart-frontend: ## Recreate the frontend container (after changing VITE_API_BASE_URL)
	$(COMPOSE) up -d --force-recreate frontend

restart-workers: ## Restart the worker, the crawler and the scheduler
	$(COMPOSE) restart worker crawler scheduler

# ---------------------------------------------------------------- backup

backup: ## Dump the database to operations/backups/
	@mkdir -p $(BACKUP_DIR)
	@$(COMPOSE) exec -T db pg_dump -U $(PG_USER) -d $(PG_DB) --clean --if-exists \
	  | gzip > $(BACKUP_DIR)/hejobs-$(STAMP).sql.gz
	@echo "wrote $(BACKUP_DIR)/hejobs-$(STAMP).sql.gz ($$(du -h $(BACKUP_DIR)/hejobs-$(STAMP).sql.gz | cut -f1))"

restore-list: ## List available backups, newest first
	@ls -lht $(BACKUP_DIR)/*.sql.gz 2>/dev/null | awk '{print "  " $$9 "  " $$5 "  " $$6, $$7, $$8}' \
	  || echo "  no backups yet — make backup"

restore: ## Restore a dump: make restore FILE=operations/backups/hejobs-....sql.gz
	@test -n "$(FILE)" || { echo "FILE= is required. Run: make restore-list"; exit 1; }
	@test -f "$(FILE)" || { echo "no such file: $(FILE)"; exit 1; }
	@echo "This REPLACES the contents of $(PG_DB). Ctrl-C within 5s to abort."
	@sleep 5
	@gunzip -c "$(FILE)" | $(COMPOSE) exec -T db psql -U $(PG_USER) -d $(PG_DB) >/dev/null
	@echo "restored from $(FILE)"
	@$(MAKE) --no-print-directory migrate

db-size: ## Row counts and on-disk size of the main tables
	@$(COMPOSE) exec -T db psql -U $(PG_USER) -d $(PG_DB) -c "\
SELECT relname AS table, n_live_tup AS rows, pg_size_pretty(pg_total_relation_size(relid)) AS size \
FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 12;"

# ---------------------------------------------------------------- housekeeping

disk: ## What Docker is using
	@docker system df

prune: ## Reclaim Docker space (build cache and unused images; keeps volumes)
	@echo "Removing build cache and unused images. Named volumes are NOT touched."
	docker builder prune -af
	docker image prune -af

ops-help: ## Operational targets only
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(OPS_DIR)/Makefile \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
