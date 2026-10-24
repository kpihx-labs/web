"""Stable search records; evidence and retrieval status remain separate."""

import re
from dataclasses import dataclass, field

import phonenumbers


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    engine: str
    category: str
    timestamp: str
    score: float = 0
    extracted_emails: list[str] = field(default_factory=list)
    extracted_phones: list[str] = field(default_factory=list)
    engines: list[str] = field(default_factory=list)
    provider_fields: dict = field(default_factory=dict)


def extract_osint_entities(text, region=None):
    if region is None:
        from .user_config import settings

        region = settings()["phone_region"]
    emails = (
        sorted(set(re.findall(r"[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63})+", text)))
        if "@" in text
        else []
    )
    phones = sorted(
        {
            phonenumbers.format_number(m.number, phonenumbers.PhoneNumberFormat.E164)
            for m in phonenumbers.PhoneNumberMatcher(text, region)
            if phonenumbers.is_valid_number(m.number)
        }
    )
    return {"emails": emails, "phones": phones}
