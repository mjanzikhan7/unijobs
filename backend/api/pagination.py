"""Pagination shared by every list endpoint."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class DefaultPagination(PageNumberPagination):
    """Page-number pagination. The client can choose the page size.

    The response has ``total_pages`` as well as ``count``, so the client does not have to
    repeat the page size logic to show "page 3 of 17".
    """

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200

    def get_paginated_response(self, data: Any) -> Response:
        """Return the standard envelope plus page metadata."""
        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("total_pages", self.page.paginator.num_pages),
                    ("page", self.page.number),
                    ("page_size", self.get_page_size(self.request)),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )
