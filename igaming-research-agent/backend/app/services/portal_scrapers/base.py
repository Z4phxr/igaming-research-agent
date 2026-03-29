from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ListingParseResult:
    candidate_urls: list[str] = field(default_factory=list)
    # Optional hint map: article URL -> title discovered on listing.
    candidate_titles: dict[str, str] = field(default_factory=dict)
    # Optional hint map: article URL -> published date discovered on listing.
    candidate_published_dates: dict[str, datetime.datetime] = field(default_factory=dict)
    empty_reason: str | None = None


class PortalListingParser(ABC):
    @abstractmethod
    def matches(self, source_url: str, company_name: str) -> bool:
        """Return True when this parser should handle the source."""

    @abstractmethod
    def parse_listing(
        self,
        listing_html: str,
        source_url: str,
        company_name: str,
        cutoff: datetime.datetime | None = None,
        now_utc: datetime.datetime | None = None,
    ) -> ListingParseResult:
        """Extract article candidate URLs from source listing HTML."""

    def extract_article_published_date(self, article_html: str):
        """Optional per-portal article date extraction hook."""
        return None

    def is_likely_descending_chronological(self) -> bool:
        """Return True when listing order is newest->oldest and stale hit can stop scan."""
        return False
