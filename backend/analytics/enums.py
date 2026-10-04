"""Enumerations owned by the analytics app."""

from __future__ import annotations

from shared.enums import LabelledEnum


class EventKind(LabelledEnum):
    """What happened.

    Kept broad on purpose. A list with one value per button would be impossible to add up.
    """

    SEARCH = "SEARCH", "Searched"
    JOB_VIEW = "JOB_VIEW", "Viewed a job"
    JOB_SAVE = "JOB_SAVE", "Saved a job"
    JOB_UNSAVE = "JOB_UNSAVE", "Unsaved a job"
    APPLY = "APPLY", "Recorded an application"
    APPLICATION_MOVE = "APPLICATION_MOVE", "Moved an application"
    INSTITUTION_VIEW = "INSTITUTION_VIEW", "Viewed an institution"
    CV_UPLOAD = "CV_UPLOAD", "Uploaded a CV"
    EXPORT = "EXPORT", "Exported results"


EVENT_KIND_CHOICES = EventKind.choices()
