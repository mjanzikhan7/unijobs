"""Platform adapters.

Importing this package registers every adapter. ``CrawlerConfig.ready`` imports it at startup.

To add a platform, add a module here and decorate its class with ``@register_adapter``. The
shared contract tests in ``tests/unit/test_adapter_contract.py`` cover every registered
adapter automatically.
"""

from __future__ import annotations

from crawler.adapters.aub_vacancy_cards import AubVacancyCardsAdapter
from crawler.adapters.base import BaseAdapter
from crawler.adapters.cambridge_views_table import CambridgeViewsTableAdapter
from crawler.adapters.changeworknow import ChangeWorkNowAdapter
from crawler.adapters.contensis_jobs import ContensisJobsAdapter
from crawler.adapters.corehr import CoreHRAdapter
from crawler.adapters.corehr_categorised import CoreHRCategorisedAdapter
from crawler.adapters.dundee_vacancy_cards import DundeeVacancyCardsAdapter
from crawler.adapters.engage_ats import EngageAtsAdapter
from crawler.adapters.eploy import EployAdapter
from crawler.adapters.funnelback import FunnelbackAdapter
from crawler.adapters.generic_card_scrape import GenericCardScrapeAdapter
from crawler.adapters.guildhall_vacancy_cards import GuildhallVacancyCardsAdapter
from crawler.adapters.hireful_cms import HirefulCmsAdapter
from crawler.adapters.hireserve import HireserveAdapter
from crawler.adapters.itrent import ITrentAdapter
from crawler.adapters.jobtrain import JobtrainAdapter
from crawler.adapters.leeds_arts import LeedsArtsAdapter
from crawler.adapters.lipa_vacancy_cards import LipaVacancyCardsAdapter
from crawler.adapters.liverpool_hope_vacancy_tables import LiverpoolHopeVacancyTablesAdapter
from crawler.adapters.luminate import LuminateAdapter
from crawler.adapters.mhr_people_first import MhrPeopleFirstAdapter
from crawler.adapters.norwich_vacancy_cards import NorwichVacancyCardsAdapter
from crawler.adapters.oracle_fusion import OracleFusionAdapter
from crawler.adapters.postingpanda import PostingPandaAdapter
from crawler.adapters.rails_jobs_board import RailsJobsBoardAdapter
from crawler.adapters.rcm_vacancy_cards import RcmVacancyCardsAdapter
from crawler.adapters.rncm_vacancy_cards import RncmVacancyCardsAdapter
from crawler.adapters.stonefish import StonefishAdapter
from crawler.adapters.structured import StructuredDataAdapter
from crawler.adapters.successfactors import SuccessFactorsAdapter
from crawler.adapters.talentlink import TalentlinkAdapter
from crawler.adapters.taleo import TaleoAdapter
from crawler.adapters.tribepad import TribepadAdapter
from crawler.adapters.webrecruit import WebrecruitAdapter
from crawler.adapters.workday import WorkdayAdapter

__all__ = [
    "AubVacancyCardsAdapter",
    "BaseAdapter",
    "CambridgeViewsTableAdapter",
    "ChangeWorkNowAdapter",
    "ContensisJobsAdapter",
    "CoreHRAdapter",
    "CoreHRCategorisedAdapter",
    "DundeeVacancyCardsAdapter",
    "EngageAtsAdapter",
    "EployAdapter",
    "FunnelbackAdapter",
    "GenericCardScrapeAdapter",
    "GuildhallVacancyCardsAdapter",
    "HirefulCmsAdapter",
    "HireserveAdapter",
    "ITrentAdapter",
    "JobtrainAdapter",
    "LeedsArtsAdapter",
    "LipaVacancyCardsAdapter",
    "LiverpoolHopeVacancyTablesAdapter",
    "LuminateAdapter",
    "MhrPeopleFirstAdapter",
    "NorwichVacancyCardsAdapter",
    "OracleFusionAdapter",
    "PostingPandaAdapter",
    "RailsJobsBoardAdapter",
    "RcmVacancyCardsAdapter",
    "RncmVacancyCardsAdapter",
    "StonefishAdapter",
    "StructuredDataAdapter",
    "SuccessFactorsAdapter",
    "TalentlinkAdapter",
    "TaleoAdapter",
    "TribepadAdapter",
    "WebrecruitAdapter",
    "WorkdayAdapter",
]
