from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class AristocratHtmlParser(PortalListingParser):
    """Dedicated parser for Aristocrat news listing."""

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "aristocrat.com/news" in token_url or "aristocrat" in token_name

    def parse_listing(
        self,
        listing_html: str,
        source_url: str,
        company_name: str,
        cutoff: datetime.datetime | None = None,
        now_utc: datetime.datetime | None = None,
    ) -> ListingParseResult:
        result = ListingParseResult()
        soup = BeautifulSoup(listing_html or "", "html.parser")
        articles = soup.select("main article, article.anim-fade-in-up, article")

        if not articles:
            result.empty_reason = "no_aristocrat_articles"
            return result

        seen: set[str] = set()
        for index, article in enumerate(articles):
            link = article.select_one(".entry-title a[href], h2.entry-title a[href], h3.entry-title a[href]")
            if link is None:
                # Fallback: pick the first non-empty text link (skip image-only anchors).
                for candidate in article.select("a[href]"):
                    candidate_text = re.sub(r"\s+", " ", candidate.get_text(" ", strip=True)).strip()
                    if candidate_text:
                        link = candidate
                        break
            if link is None:
                continue

            href = str(link.get("href") or "").strip()
            if not href:
                continue
            absolute_url = urljoin(source_url, href)
            if "/news/" in absolute_url.rstrip("/").lower() and absolute_url.rstrip("/").lower().endswith("/news"):
                continue
            if absolute_url in seen:
                continue

            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
            if not title:
                continue

            published = self._extract_date(article)
            if published is not None and cutoff is not None and published < cutoff:
                if index == 0:
                    result.empty_reason = "listing_first_aristocrat_item_outside_time_window"
                    return result
                break

            if published is not None and now_utc is not None and published > now_utc:
                continue

            seen.add(absolute_url)
            result.candidate_urls.append(absolute_url)
            result.candidate_titles[absolute_url] = title
            if published is not None:
                result.candidate_published_dates[absolute_url] = published

        if not result.candidate_urls and result.empty_reason is None:
            result.empty_reason = "no_aristocrat_in_window_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    @staticmethod
    def _extract_date(article) -> datetime.datetime | None:
        time_node = article.select_one("time[datetime]")
        if time_node is not None:
            raw_dt = str(time_node.get("datetime") or "").strip()
            if raw_dt:
                candidates = [raw_dt]
                if raw_dt.endswith("Z"):
                    candidates.append(raw_dt[:-1] + "+00:00")
                for candidate in candidates:
                    try:
                        parsed = datetime.datetime.fromisoformat(candidate)
                        if parsed.tzinfo is not None:
                            return parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                        return parsed
                    except ValueError:
                        continue

        text = re.sub(r"\s+", " ", article.get_text(" ", strip=True)).strip()
        match = re.search(r"\b([A-Z][a-z]{2,8}\s+\d{1,2},\s+\d{4})\b", text)
        if not match:
            return None
        for fmt in ("%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.datetime.strptime(match.group(1), fmt)
            except ValueError:
                continue
        return None
