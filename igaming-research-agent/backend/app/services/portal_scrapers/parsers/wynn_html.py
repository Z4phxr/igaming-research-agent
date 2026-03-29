from __future__ import annotations

import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.portal_scrapers.base import ListingParseResult, PortalListingParser


class WynnHtmlParser(PortalListingParser):
    """Dedicated parser for Wynn Resorts investor press releases."""

    def matches(self, source_url: str, company_name: str) -> bool:
        token_url = (source_url or "").lower()
        token_name = (company_name or "").lower()
        return "investors.wynnresorts.com/press-releases" in token_url or "wynn" in token_name

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
        seen: set[str] = set()
        rows = soup.select("table.table tbody tr") or soup.select("tbody tr")
        if rows:
            for index, row in enumerate(rows):
                link = row.select_one(
                    "a.more-item[href*='/news-releases/news-release-details/'], "
                    "a[href*='/news-releases/news-release-details/'], "
                    "a[href*='/press-releases/']"
                )
                if link is None:
                    continue

                href = str(link.get("href") or "").strip()
                if not href:
                    continue

                absolute_url = urljoin(source_url, href)
                if absolute_url in seen:
                    continue

                title_node = link.select_one("span.more-item__text")
                title = re.sub(
                    r"\s+",
                    " ",
                    (title_node.get_text(" ", strip=True) if title_node is not None else link.get_text(" ", strip=True)),
                ).strip()
                if not title:
                    continue

                time_node = row.select_one("time")
                time_text = time_node.get_text(" ", strip=True) if time_node is not None else ""
                row_text = re.sub(r"\s+", " ", row.get_text(" ", strip=True)).strip()
                published = self._parse_mmddyy(time_text) or self._parse_mmddyy(row_text)

                if published is not None and cutoff is not None and published < cutoff:
                    if index == 0:
                        result.empty_reason = "listing_first_wynn_item_outside_time_window"
                        return result
                    break

                if published is not None and now_utc is not None and published > now_utc:
                    continue

                seen.add(absolute_url)
                result.candidate_urls.append(absolute_url)
                result.candidate_titles[absolute_url] = title
                if published is not None:
                    result.candidate_published_dates[absolute_url] = published
        else:
            # Fallback for simpler pages that expose direct release links without table rows.
            links = soup.select(
                "a[href*='/news-releases/news-release-details/'][href], "
                "a[href*='/press-releases/'][href]:not([href$='/press-releases'])"
            )
            for index, link in enumerate(links):
                href = str(link.get("href") or "").strip()
                if not href:
                    continue

                absolute_url = urljoin(source_url, href)
                if absolute_url in seen:
                    continue

                title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
                if not title:
                    continue

                parent_text = re.sub(
                    r"\s+", " ", link.parent.get_text(" ", strip=True) if link.parent else ""
                ).strip()
                published = self._parse_mmddyy(parent_text)

                if published is not None and cutoff is not None and published < cutoff:
                    if index == 0:
                        result.empty_reason = "listing_first_wynn_item_outside_time_window"
                        return result
                    break

                if published is not None and now_utc is not None and published > now_utc:
                    continue

                seen.add(absolute_url)
                result.candidate_urls.append(absolute_url)
                result.candidate_titles[absolute_url] = title
                if published is not None:
                    result.candidate_published_dates[absolute_url] = published

        if not rows and not result.candidate_urls:
            result.empty_reason = "no_wynn_release_links"
            return result

        if not result.candidate_urls and result.empty_reason is None:
            result.empty_reason = "no_wynn_in_window_links"

        return result

    def is_likely_descending_chronological(self) -> bool:
        return True

    @staticmethod
    def _parse_mmddyy(value: str) -> datetime.datetime | None:
        match = re.search(r"\b(\d{2}/\d{2}/\d{2})\b", value or "")
        if not match:
            return None
        try:
            return datetime.datetime.strptime(match.group(1), "%m/%d/%y")
        except ValueError:
            return None
