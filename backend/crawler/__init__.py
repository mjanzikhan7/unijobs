"""Fetching vacancies from university careers portals.

Adapters, the polite HTTP client, the raw-response cache and the run orchestrator. The rules
that matter - the adapter contract and the per-platform quirks - are documented on each adapter
class; the closure safety rule lives with the orchestrator that enforces it.

This app may import from :mod:`jobs` and :mod:`institutions`. Nothing here may import from
:mod:`api`.
"""

from __future__ import annotations
