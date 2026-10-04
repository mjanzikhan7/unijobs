"""A model with an owner may only be served through a scoped viewset.

``test_tenant_isolation`` proves the four owned models behave today. This proves the *next* one
will: add an ``owner`` field, register a viewset, forget the mixin, and this fails at import time
rather than leaking on the list endpoint nobody thought to test.
"""

from __future__ import annotations

import pytest
from django.apps import apps
from django.db import models

from api.permissions import OwnedQuerysetMixin
from api.urls import router

_OWNER_FIELD = "owner"


def _models_with_an_owner() -> list[type[models.Model]]:
    return [
        model
        for model in apps.get_models()
        if any(field.name == _OWNER_FIELD for field in model._meta.get_fields())
    ]


def _viewsets_by_model() -> dict[type[models.Model], type]:
    """Map each routed model onto the viewset serving it."""
    found: dict[type[models.Model], type] = {}
    for _prefix, viewset, _basename in router.registry:
        queryset = getattr(viewset, "queryset", None)
        model = getattr(viewset, "model", None) or (
            queryset.model if queryset is not None else None
        )
        if model is not None:
            found[model] = viewset
    return found


def test_there_are_owned_models_to_check() -> None:
    """Guard the guard - an empty list would make the assertion below vacuous."""
    assert len(_models_with_an_owner()) >= 4


@pytest.mark.parametrize("model", _models_with_an_owner(), ids=lambda model: model._meta.label)
def test_an_owned_model_is_served_only_through_a_scoped_viewset(model: type[models.Model]) -> None:
    """If it is routed at all, its viewset must filter by owner."""
    viewset = _viewsets_by_model().get(model)
    if viewset is None:
        return

    assert issubclass(viewset, OwnedQuerysetMixin), (
        f"{viewset.__name__} serves {model._meta.label}, which has an `owner`, but does not use "
        f"OwnedQuerysetMixin — its list endpoint would return every user's rows."
    )
