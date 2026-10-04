# UniJobs

A self-hosted job search service for UK higher education. It crawls university careers pages,
reads the vacancies, checks each one against Skilled Worker sponsorship rules, and shows the
results in a React web app with search, filters, a crawl console and an application tracker.

**It never submits anything to an employer.** Every Apply link opens the employer's own advert
in a new tab. There is no auto-apply and no form filling.

## Why it exists

To find an academic job that can lead to a sponsored visa, you must ask three questions about
every advert:

1. Does this university hold a sponsor licence?
2. Is the salary above the threshold?
3. Is the advert still open?

A computer can answer all three. By hand, it is slow and easy to get wrong.

The tool answers them and shows how it got each answer. When it cannot tell, it says so. It
never guesses. Showing a job as sponsorable when it is not can cost a person an application,
an interview and several weeks.

## Roles

Each account has exactly one role. With a set of roles, the permission code would need a rule
for which role wins, and that is where privilege bugs hide.

| Role | Can use |
|---|---|
| `CANDIDATE` | Job search, institutions, saved jobs, their own pipeline, profile and CV |
| `RECRUITER` | All of the above, plus job admin for **only** the institutions they are assigned to |
| `MANAGER` | All of the above, plus the crawl console, sponsor review, and job and institution admin for every institution |
| `ADMIN` | Everything, plus user accounts and the salary threshold rules |

## Running it

You need Docker with Docker Compose. Nothing else.

```bash
cp .env.example .env
make up          # build and start every container
make seed        # 167 institutions, the sponsor register, the current rules (safe to repeat)
make superuser   # create the first administrator
make doctor      # check that it all came up
```

Then open <http://localhost:5173>.

`make up` runs in the foreground. To start in the background, use `docker compose up -d --build`.

Every value in `.env.example` is also the default in `compose.yaml`, so `make up` works without
a `.env` file. The file is there to show what you can change.

| Service | Address |
|---|---|
| App | <http://localhost:5173> |
| API | <http://localhost:8000/api/> |
| API docs (Swagger) | <http://localhost:8000/api/schema/swagger/> |
| Mailpit | <http://localhost:8025>: **every email the app sends goes here, never to a real inbox** |

All ports are bound to `127.0.0.1`, so they are not open to your local network.

### Containers

Each component runs in its own container, so each can be scaled, limited or restarted on its own.

| Container | What it does |
|---|---|
| `db` | PostgreSQL 16 |
| `redis` | Task queue and cache |
| `migrate` | Applies database migrations, then exits |
| `backend` | Django REST API |
| `worker` | Background tasks that do not need a browser |
| `crawler` | Crawl tasks, with Chromium |
| `scheduler` | Starts the timed tasks |
| `frontend` | Vite dev server for the React app |
| `mailpit` | Catches all email |
| `e2e` | Playwright tests (only with `make e2e`) |

For production, use `compose.production.yaml`, or the Terraform and Ansible files in `deploy/`.

### Looking around without crawling

```bash
make seed-demo   # eight awkward example adverts, screened by the real code
```

The examples cover the difficult cases: a salary range with no lower figure, a university with
no licence, an advert that mentions sponsorship and one that says nothing.

### Accounts

Registering sends a confirmation link to Mailpit. To confirm an account without email:

```bash
make verify-user ARGS="alice --role MANAGER"
```

### Crawling

```bash
make crawl                                   # all 167, slowly and politely
make crawl ARGS="--slug university-of-bath"  # one institution
make crawl ARGS="--no-browser"               # skip Chromium; sites that need JS report ZERO_RESULTS
```

Watch it live in the crawl console at <http://localhost:5173/admin/crawl>, or from the command
line:

```bash
make crawl-status     # the last 10 runs and their totals
make crawl-problems   # institutions in the latest run that were not OK
```

Pause, Resume and Stop are next to the run banner while a run is active. They are not instant:
an institution that is already being fetched finishes and records its real result. Only work
that has not started yet is held back. A finished run offers **Restart** (same scope) and
**Retry failures** (only the institutions that were not `OK`).

### Timed tasks

The `scheduler` container starts these. Times are Europe/London, so 06:00 means 06:00 local
time in both summer and winter.

| When | What |
|---|---|
| 06:00, 14:00, 22:00 | Crawl every institution |
| Every 10 minutes | Mark stuck runs as failed, so a new one can start |
| 03:15, 03:45 | Count search terms, delete old usage events |
| 04:30, 04:45 | Delete old crawler responses and unconfirmed accounts |
| 05:30 | Rebuild the search index (a safety net) |
| 07:00 | Flag applications with no reply for a long time |

## Everyday commands

```bash
make test          # pytest and vitest
make lint          # ruff, mypy, eslint, tsc
make fix           # fix what the tools can fix on their own
make e2e           # Playwright tests, with accessibility checks, in their own container
make audit         # known vulnerabilities in dependencies
make check-deploy  # Django's deployment checks against the production settings
make static-site   # open vacancies as plain HTML, CSV and JSON, with no JavaScript
make schema        # write backend/openapi.yaml
make types         # rebuild the TypeScript API types from the schema
make storybook     # every component, every state, both themes
make health        # one-line status of every service
make logs          # follow the logs
make down          # stop, keep the data
make clean         # stop and DELETE the database volume
```

`make help` lists everything. `make ops-help` lists only the operations targets.

CI runs on every push, on GitHub Actions and GitLab: lint, types, tests, dependency audit,
production images, browser tests with accessibility checks, and the Terraform and Ansible checks.

## How the code is organised

```
backend/                       Django project
  crawler/                     an adapter per recruitment system, polite HTTP, a response cache
  screening/                   sponsor matching, salary parsing, threshold rules, fitness scores
  jobs/                        jobs, search, saved jobs, the application pipeline
  institutions/                the institution list and its seed data
  accounts/                    roles and account verification
  analytics/                   search term totals and institution insights
  api/                         REST views, serializers, permissions, the personal data export
  shared/                      small helpers used by every app
  config/                      settings (base, development, production, test), Celery, URLs
frontend/                      React app
  src/models/                  API client and types (Model)
  src/viewmodels/              data hooks (ViewModel)
  src/store/                   Redux store and the sagas that fetch, poll and mutate
  src/views/                   screens (View)
  src/components/              shared UI parts
  nginx/                       the production gateway config
packages/accessibility-toolbar the accessibility settings, as a separate npm package
end-to-end-tests/              Playwright tests and their Dockerfile
operations/                    doctor script, backup and restore targets
deploy/                        Terraform (OpenStack) and Ansible for production
```

Dependencies point inwards: `api` → `jobs` / `screening` / `crawler` → `institutions`.
`screening` never imports from `crawler`, and neither imports from `api`.

Inside each backend app the layers are `api → services → domain → models`. The `domain` modules
are pure Python: no Django, no I/O, no clock and no randomness. The time is passed in. This
makes the important logic quick and simple to test.

The frontend follows MVVM. A screen in `views/` never calls the API client. It uses a hook from
`viewmodels/`.

State lives in one Redux store (`src/store/`), and every side effect is a redux-saga. A viewmodel
hook describes a query or a mutation; mounting it dispatches an action, and the sagas decide when
to call the API, retry, poll, refetch after a change, or forget an answer nobody is showing.
Reducers only record what happened.

## The rules that matter

These rules protect the person using the tool. Tests enforce them.

1. **A job is only closed after an `OK` crawl.** A blocked, offline or empty crawl leaves
   existing jobs alone. A broken site must never empty the list in silence.
2. **`ZERO_RESULTS` is not success.** It is its own outcome and is reported, because a page with
   no jobs looks the same as a parser that stopped working.
3. **Every job has a sponsor verdict and a threshold verdict.** Never empty. A missing verdict
   would look like "confirmed", which is the dangerous direction to be wrong in.
4. **Salary is checked on the bottom of the advertised range.** That is what goes on the
   Certificate of Sponsorship. A top figure with no bottom figure is `SALARY_UNCLEAR`.
5. **The raw text is always kept** next to anything parsed: `salary_raw`, `location_raw`,
   `grade_raw`. When a verdict looks wrong, the raw value shows where the fault is.
6. **Threshold figures live in the database**, versioned, with a check date and a source URL.
   There are no salary figures in Python. Editing creates a new version, so an old verdict can
   still be explained.
7. **The crawler is honest and polite.** It follows `robots.txt` (RFC 9309), waits between
   requests, says who it is, hides nothing, and records a block as `BLOCKED` instead of getting
   around it.
8. **Nothing is ever submitted to an employer.**

An advert that does not mention sponsorship tells you nothing. Most licensed sponsors never
mention it.

## Testing

```bash
make test          # everything
make coverage      # HTML coverage report
make e2e           # browser tests, including axe checks on the main screens
```

No test uses the real internet. Adapters run against saved pages in
`backend/tests/fixtures/captured_pages/`, and httpx is stubbed with respx.

`screening/domain.py` has 100% line and branch coverage. The project minimum is 80%. Code in
`screening/` and `crawler/` is written test-first. A bug fix starts with a failing test.

Saved pages are captured again only on purpose:

```bash
make refresh-fixtures ARGS="--slug university-of-bath"
```

This is the only command that visits live sites. It removes contact details and reminds you to
read the diff. A fixture that changed without anyone noticing can hide a real bug.

## Adding an institution

Add it to `backend/institutions/seeds/institutions.json` and run `make seed`.

If it uses a recruitment system with no adapter yet, add one class in `crawler/adapters/`:

```python
@register_adapter
class ExampleAdapter(PlatformAdapter):
    platform = Platform.EXAMPLE
```

The crawler finds adapters through a registry, so nothing else needs editing. The shared
contract tests run against every registered adapter automatically.

Each adapter's module docstring says which system it targets, how to recognise it, its quirks,
whether it needs a browser, and one real example URL.

## Operating it

**When something is wrong and you do not know what:** run `make doctor`. It checks the usual
problems in the order they happen, and names the command that fixes each one.

### Backups

The database holds the things that are expensive to rebuild: crawled jobs, saved jobs, the
application pipeline, and the rules history. Institutions and the sponsor register can be loaded
again. **A pipeline cannot.**

```bash
make backup        # -> operations/backups/hejobs-YYYYmmdd-HHMMSS.sql.gz
make restore-list  # what you have, newest first
make restore FILE=operations/backups/hejobs-20260824-054410.sql.gz
```

`restore` replaces the database contents and gives you five seconds to press Ctrl-C. It runs
`make migrate` afterwards. Take a backup before changing the rules, before a bulk re-screen, and
before `make clean`.

`operations/backups/` is ignored by git. Dumps contain personal data.

### Common problems

**The app loads but shows no jobs.** The Vite proxy cannot reach Django. Check
`VITE_API_BASE_URL`: it must be `http://backend:8000`, because the dev server reads it inside its
own container. Then run `make restart-frontend`.

**"A run is already in progress".** A run stopped without finishing, usually because a container
restarted. `make unstick` marks runs with no heartbeat for 30 minutes as failed.

**An institution reports `ZERO_RESULTS`.** Do not ignore it. Run `make crawl-problems`, then open
that careers page and compare. If the site changed, capture the fixture again, read the diff and
fix the adapter.

**Jobs without verdicts.** This should never happen, and `make doctor` fails if it does. Run
`make rescreen`. If it continues, there is probably no active rule set: run `make seed`.

**Tasks are not running.** Run `make health`, then `make restart-workers`. Redis must be healthy.

**Disk full.** `make disk` shows what Docker uses. `make prune` removes build cache and unused
images, but not the database. `make clean` does delete the database.

### Changing threshold figures

Skilled Worker figures change. They are not in Python.

1. `make backup`
2. Open <http://localhost:5173/admin/thresholds>.
3. Change the figures. Add the **source URL** and the date you checked it. Both are required.
4. Save. This creates a new version. The old one is kept.
5. Re-screen from the screen or with `make rescreen`. It reports how many verdicts changed and
   makes no network calls.

## Licence

Private