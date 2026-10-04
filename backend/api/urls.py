"""API routes.

Everything needs sign-in, except ``/health/``, the schema, and the ``/auth/`` endpoints a
signed-out person needs: login, register, confirm email and password reset.
"""

from __future__ import annotations

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from api.views.account import (
    AccountView,
    ChangePasswordView,
    ConfirmEmailChangeView,
    DigestPreferenceView,
    ExportPersonalDataView,
)
from api.views.analytics import (
    CandidateInsightsView,
    InstitutionInsightsView,
    SearchCloudView,
)
from api.views.auth import LoginView, MeView
from api.views.crawl import CrawlRunViewSet
from api.views.cvs import CVViewSet
from api.views.health import HealthView
from api.views.institutions import InstitutionViewSet, SponsorMatchViewSet
from api.views.jobs import JobViewSet
from api.views.metrics import MetricsView
from api.views.registration import (
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    VerifyEmailView,
)
from api.views.screening import CandidateProfileViewSet, RulesetViewSet
from api.views.tracking import ApplicationViewSet, SavedJobViewSet, SavedSearchViewSet
from api.views.users import UserViewSet

router = DefaultRouter()
router.register("jobs", JobViewSet, basename="job")
router.register("institutions", InstitutionViewSet, basename="institution")
router.register("sponsor-matches", SponsorMatchViewSet, basename="sponsor-match")
router.register("crawl-runs", CrawlRunViewSet, basename="crawl-run")
router.register("saved-jobs", SavedJobViewSet, basename="saved-job")
router.register("applications", ApplicationViewSet, basename="application")
router.register("saved-searches", SavedSearchViewSet, basename="saved-search")
router.register("rulesets", RulesetViewSet, basename="ruleset")
router.register("profiles", CandidateProfileViewSet, basename="profile")
router.register("cvs", CVViewSet, basename="cv")
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("metrics/", MetricsView.as_view(), name="metrics"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("account/", AccountView.as_view(), name="account"),
    path("account/password/", ChangePasswordView.as_view(), name="account-password"),
    path("account/digest/", DigestPreferenceView.as_view(), name="account-digest"),
    path("account/export/", ExportPersonalDataView.as_view(), name="account-export"),
    path(
        "account/confirm-email/",
        ConfirmEmailChangeView.as_view(),
        name="account-confirm-email",
    ),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path(
        "auth/password-reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset",
    ),
    path(
        "auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("insights/candidates/", CandidateInsightsView.as_view(), name="insights-candidates"),
    path("insights/institutions/", InstitutionInsightsView.as_view(), name="insights-institutions"),
    path("insights/search-cloud/", SearchCloudView.as_view(), name="insights-search-cloud"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("schema/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
    path("", include(router.urls)),
]
