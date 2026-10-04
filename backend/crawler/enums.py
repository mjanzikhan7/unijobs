"""Crawler enumerations.

``CrawlOutcome`` matters most: only one value, ``OK``, allows a job to be closed. Every other
value means "we did not see the real list today".
"""

from __future__ import annotations

from shared.enums import LabelledEnum


class CrawlTrigger(LabelledEnum):
    """What started a run."""

    MANUAL = "MANUAL", "Manual"
    SCHEDULED = "SCHEDULED", "Scheduled"


class CrawlRunStatus(LabelledEnum):
    """The states of a run.

    ``PAUSED`` and ``CANCELLED`` come from a user, not from a worker dying.
    """

    RUNNING = "RUNNING", "Running"
    PAUSED = "PAUSED", "Paused"
    COMPLETE = "COMPLETE", "Complete"
    CANCELLED = "CANCELLED", "Cancelled"
    INCOMPLETE = "INCOMPLETE", "Incomplete"
    FAILED = "FAILED", "Failed"


ACTIVE_RUN_STATUSES: frozenset[CrawlRunStatus] = frozenset(
    {CrawlRunStatus.RUNNING, CrawlRunStatus.PAUSED}
)


class CrawlLogLevel(LabelledEnum):
    """Severity of one crawl log line, for the console's log panel."""

    INFO = "INFO", "Info"
    WARNING = "WARNING", "Warning"
    ERROR = "ERROR", "Error"


class CrawlOutcome(LabelledEnum):
    """The result of crawling one institution.

    ``ZERO_RESULTS`` is not success. A page with no jobs looks the same as a parser that stopped
    working, so it is reported as a problem.
    """

    OK = "OK", "OK"
    ZERO_RESULTS = "ZERO_RESULTS", "Zero results"
    ROBOTS_DISALLOWED = "ROBOTS_DISALLOWED", "Disallowed by robots.txt"
    BLOCKED = "BLOCKED", "Blocked"
    OFFLINE = "OFFLINE", "Site offline"
    TIMEOUT = "TIMEOUT", "Timed out"
    PARSE_ERROR = "PARSE_ERROR", "Parse error"
    NO_ADAPTER = "NO_ADAPTER", "No adapter matched"
    SKIPPED = "SKIPPED", "Skipped"


CLOSURE_SAFE_OUTCOMES: frozenset[CrawlOutcome] = frozenset({CrawlOutcome.OK})


class ExtractionStrategy(LabelledEnum):
    """How the vacancies were taken from the page.

    Saved, so after a site upgrade we can compare instead of guess.
    """

    JSON_LD = "JSON_LD", "schema.org JSON-LD"
    RSS = "RSS", "RSS feed"
    JSON_API = "JSON_API", "JSON endpoint"
    HTML = "HTML", "HTML selectors"
    BROWSER_HTML = "BROWSER_HTML", "HTML rendered in a browser"
    NONE = "NONE", "Nothing extracted"


CRAWL_TRIGGER_CHOICES = CrawlTrigger.choices()
CRAWL_RUN_STATUS_CHOICES = CrawlRunStatus.choices()
CRAWL_OUTCOME_CHOICES = CrawlOutcome.choices()
EXTRACTION_STRATEGY_CHOICES = ExtractionStrategy.choices()
