#!/usr/bin/env bash
#
# Check the things that usually break, in the order they break.
#
# Each check prints PASS, WARN or FAIL with a short reason. WARN means it works now but
# will cause trouble later. FAIL means the app is broken now. The exit code is the number
# of FAILs.
#
# No check changes anything. This script is run when something is already wrong.

set -uo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1

RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; DIM=$'\033[2m'; OFF=$'\033[0m'
fails=0
warns=0

pass() { printf '  %sPASS%s  %-34s %s\n' "$GREEN" "$OFF" "$1" "${2-}"; }
warn() { printf '  %sWARN%s  %-34s %s\n' "$YELLOW" "$OFF" "$1" "${2-}"; warns=$((warns + 1)); }
fail() { printf '  %sFAIL%s  %-34s %s\n' "$RED" "$OFF" "$1" "${2-}"; fails=$((fails + 1)); }
section() { printf '\n%s%s%s\n' "$DIM" "$1" "$OFF"; }

COMPOSE="docker compose"
BE="$COMPOSE exec -T backend"

# ---------------------------------------------------------------- prerequisites
section "Prerequisites"

if ! command -v docker >/dev/null 2>&1; then
  fail "docker installed" "not on PATH — nothing else can be checked"
  exit 1
fi
pass "docker installed" "$(docker --version | cut -d, -f1)"

if ! docker info >/dev/null 2>&1; then
  fail "docker daemon" "not responding — start Docker Desktop"
  exit 1
fi
pass "docker daemon" "responding"

avail_kb=$(df -k . | awk 'NR==2 {print $4}')
avail_gb=$((avail_kb / 1024 / 1024))
if [ "$avail_gb" -lt 3 ]; then
  fail "disk space" "${avail_gb}GB free — builds and Postgres will fail. make prune"
elif [ "$avail_gb" -lt 10 ]; then
  warn "disk space" "${avail_gb}GB free — getting tight"
else
  pass "disk space" "${avail_gb}GB free"
fi

# ---------------------------------------------------------------- configuration
section "Configuration"

if [ ! -f .env ]; then
  fail ".env present" "missing — cp .env.example .env"
else
  pass ".env present"

  proxy=$(grep -E '^VITE_API_BASE_URL=' .env | cut -d= -f2-)
  case "$proxy" in
    *//backend:*) pass "VITE_API_BASE_URL" "$proxy" ;;
    *localhost*|*127.0.0.1*)
      fail "VITE_API_BASE_URL" "$proxy — inside the container that is the frontend itself; use http://backend:8000" ;;
    "") warn "VITE_API_BASE_URL" "unset — defaults to http://backend:8000" ;;
    *) warn "VITE_API_BASE_URL" "$proxy — unusual, check it resolves from the frontend container" ;;
  esac

  secret=$(grep -E '^DJANGO_SECRET_KEY=' .env | cut -d= -f2-)
  case "$secret" in
    *dev-only*|*change-me*|"") warn "DJANGO_SECRET_KEY" "still the example value — fine locally, not for anything exposed" ;;
    *) pass "DJANGO_SECRET_KEY" "set" ;;
  esac
fi

# ---------------------------------------------------------------- containers
section "Containers"

running=$($COMPOSE ps --services --filter status=running 2>/dev/null)
if [ -z "$running" ]; then
  fail "stack running" "nothing up — make up"
  printf '\n%s%d failed, %d warnings%s\n' "$RED" "$fails" "$warns" "$OFF"
  exit "$fails"
fi

for svc in db redis backend worker crawler scheduler frontend; do
  if grep -qx "$svc" <<<"$running"; then
    health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' \
      "$($COMPOSE ps -q "$svc" 2>/dev/null)" 2>/dev/null)
    case "$health" in
      healthy|no-healthcheck) pass "$svc" "running" ;;
      starting)               warn "$svc" "still starting" ;;
      *)                      fail "$svc" "running but $health" ;;
    esac
  else
    fail "$svc" "not running — make up"
  fi
done

# ---------------------------------------------------------------- reachability
section "Reachability"

check_url() {
  local name=$1 url=$2 expect=${3:-200}
  local code
  code=$(curl -s -o /dev/null -m 5 -w '%{http_code}' "$url" 2>/dev/null)
  if [ "$code" = "$expect" ]; then
    pass "$name" "$url"
  else
    fail "$name" "$url returned ${code:-no response}, expected $expect"
  fi
}

check_url "API health" "http://localhost:8000/api/health/"
check_url "frontend" "http://localhost:5173"

# The bug that makes the UI render its chrome and no data. Unauthenticated, so 401 is the
# healthy answer - it proves the proxy reached Django rather than failing to connect.
proxy_code=$(curl -s -o /dev/null -m 5 -w '%{http_code}' "http://localhost:5173/api/jobs/" 2>/dev/null)
case "$proxy_code" in
  401|403) pass "frontend proxy -> API" "reaches Django (${proxy_code} unauthenticated)" ;;
  200)     pass "frontend proxy -> API" "reaches Django" ;;
  500|502|504) fail "frontend proxy -> API" "$proxy_code — check VITE_API_BASE_URL is http://backend:8000, then: make restart-frontend" ;;
  *)       fail "frontend proxy -> API" "${proxy_code:-no response}" ;;
esac

# ---------------------------------------------------------------- database
section "Database"

pending=$($BE python manage.py showmigrations --plan 2>/dev/null | grep -c '^\[ \]')
if [ "${pending:-0}" -gt 0 ]; then
  fail "migrations applied" "$pending pending — make migrate"
else
  pass "migrations applied"
fi

counts=$($BE python manage.py shell -c "
from institutions.models import Institution
from jobs.models import Job
from screening.models import Ruleset, JobScreening
print(Institution.objects.count(), Job.objects.count(), Ruleset.objects.filter(is_active=True).count(), Job.objects.filter(screening__isnull=True).count())
" 2>/dev/null | tail -1)

read -r n_inst n_jobs n_rules n_unscreened <<<"${counts:-0 0 0 0}"

if [ "${n_inst:-0}" -eq 0 ]; then
  fail "institutions seeded" "none — make seed"
else
  pass "institutions seeded" "$n_inst"
fi

if [ "${n_rules:-0}" -eq 0 ]; then
  fail "active ruleset" "none — every threshold verdict would be unscreenable. make seed"
else
  pass "active ruleset" "1 in force"
fi

if [ "${n_jobs:-0}" -eq 0 ]; then
  warn "jobs present" "none yet — make seed-demo, or make crawl"
else
  pass "jobs present" "$n_jobs"
fi

# Domain rule: every job carries both verdicts. A null reads as "confirmed" in the UI.
if [ "${n_unscreened:-0}" -gt 0 ]; then
  fail "every job screened" "$n_unscreened without a verdict — make rescreen"
else
  pass "every job screened"
fi

# ---------------------------------------------------------------- crawl health
section "Crawl health"

crawl=$($BE python manage.py shell -c "
from django.utils import timezone
from datetime import timedelta
from crawler.models import CrawlRun, CrawlRunInstitution
stuck = CrawlRun.objects.filter(status='RUNNING', heartbeat_at__lt=timezone.now() - timedelta(minutes=30)).count()
last = CrawlRun.objects.order_by('-started_at').first()
bad = 0
if last:
    bad = CrawlRunInstitution.objects.filter(run=last).exclude(outcome='OK').count()
print(stuck, bad, last.status if last else 'NONE')
" 2>/dev/null | tail -1)

read -r stuck bad last_status <<<"${crawl:-0 0 NONE}"

if [ "${stuck:-0}" -gt 0 ]; then
  fail "no stuck runs" "$stuck RUNNING with no heartbeat for 30min — make unstick"
else
  pass "no stuck runs"
fi

if [ "$last_status" = "NONE" ]; then
  warn "last crawl" "never run — make crawl"
elif [ "${bad:-0}" -gt 0 ]; then
  warn "last crawl" "$last_status, $bad institutions not OK — see make crawl-status"
else
  pass "last crawl" "$last_status"
fi

# ---------------------------------------------------------------- verdict
printf '\n'
if [ "$fails" -gt 0 ]; then
  printf '%s%d check(s) failed%s, %d warning(s). Fix FAILs top-down — later ones are often caused by earlier ones.\n' \
    "$RED" "$fails" "$OFF" "$warns"
elif [ "$warns" -gt 0 ]; then
  printf '%sHealthy%s, with %d warning(s).\n' "$GREEN" "$OFF" "$warns"
else
  printf '%sAll checks passed.%s\n' "$GREEN" "$OFF"
fi

exit "$fails"
