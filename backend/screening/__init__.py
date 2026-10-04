"""Decides whether a job is legally takeable and personally worth taking.

Sponsor matching, salary parsing, threshold banding and fitness scoring. The interesting logic
lives in :mod:`screening.domain`, which is pure: no Django, no I/O, no clock.

This app must not import from :mod:`crawler`.
"""

from __future__ import annotations
