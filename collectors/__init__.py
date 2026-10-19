from typing import Dict, Type
from collectors.base_collector import BaseCollector, RawJobRecord
from collectors.greenhouse_collector import GreenhouseCollector
from collectors.lever_collector import LeverCollector
from collectors.ashby_collector import AshbyCollector
from collectors.workday_collector import WorkdayCollector
from collectors.remotive_collector import RemotiveCollector
from collectors.remoteok_collector import RemoteOKCollector
from collectors.arbeitnow_collector import ArbeitnowCollector
from collectors.company_careers_collector import CompanyCareersCollector
from collectors.smartrecruiters_collector import SmartRecruitersCollector
from collectors.workable_collector import WorkableCollector
from collectors.recruitee_collector import RecruiteeCollector
from collectors.adzuna_collector import AdzunaCollector
from collectors.jobicy_collector import JobicyCollector
from collectors.themuse_collector import TheMuseCollector
from collectors.himalayas_collector import HimalayasCollector
from collectors.bamboohr_collector import BambooHRCollector
from collectors.personio_collector import PersonioCollector
from collectors.usajobs_collector import USAJobsCollector

COLLECTOR_REGISTRY: Dict[str, Type[BaseCollector]] = {
    "greenhouse": GreenhouseCollector,
    "lever": LeverCollector,
    "ashby": AshbyCollector,
    "workday": WorkdayCollector,
    "smartrecruiters": SmartRecruitersCollector,
    "workable": WorkableCollector,
    "recruitee": RecruiteeCollector,
    "remotive": RemotiveCollector,
    "remoteok": RemoteOKCollector,
    "arbeitnow": ArbeitnowCollector,
    "company_career": CompanyCareersCollector,
    "adzuna": AdzunaCollector,
    "jobicy": JobicyCollector,
    "themuse": TheMuseCollector,
    "himalayas": HimalayasCollector,
    "bamboohr": BambooHRCollector,
    "personio": PersonioCollector,
    "usajobs": USAJobsCollector
}

def get_collector_for_platform(platform_name: str) -> BaseCollector:
    cls = COLLECTOR_REGISTRY.get(platform_name.lower())
    if not cls:
        raise ValueError(f"No collector registered for platform: {platform_name}")
    return cls()

__all__ = [
    "BaseCollector",
    "RawJobRecord",
    "GreenhouseCollector",
    "LeverCollector",
    "AshbyCollector",
    "WorkdayCollector",
    "SmartRecruitersCollector",
    "WorkableCollector",
    "RecruiteeCollector",
    "RemotiveCollector",
    "RemoteOKCollector",
    "ArbeitnowCollector",
    "CompanyCareersCollector",
    "AdzunaCollector",
    "JobicyCollector",
    "TheMuseCollector",
    "HimalayasCollector",
    "BambooHRCollector",
    "PersonioCollector",
    "USAJobsCollector",
    "COLLECTOR_REGISTRY",
    "get_collector_for_platform"
]
