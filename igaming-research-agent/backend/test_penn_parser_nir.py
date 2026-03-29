#!/usr/bin/env python
"""Quick test of updated PENN parser with NIR widget structure."""

from app.services.portal_scrapers.parsers.penn_html import PennHtmlParser
import datetime

html = """<article class="clearfix node node--nir-news--nir-widget-list node--type-nir-news node--view-mode-nir-widget-list node--promoted">
  <div class="nir-widget--field nir-widget--news--date-time">March 12, 2026</div>
  <div class="nir-widget--field nir-widget--news--headline">
    <a href="/news-releases/news-release-details/penn-entertainment-sets-june-12-grand-opening-date-new-hotel" hreflang="en">PENN Entertainment Sets June 12 as Grand Opening Date for New Hotel at Hollywood Casino Columbus</a>
  </div>
</article>
<article class="clearfix node node--nir-news--nir-widget-list node--type-nir-news node--view-mode-nir-widget-list node--promoted">
  <div class="nir-widget--field nir-widget--news--date-time">February 26, 2026</div>
  <div class="nir-widget--field nir-widget--news--headline">
    <a href="/news-releases/news-release-details/penn-entertainment-inc-reports-fourth-quarter-results-0" hreflang="en">PENN Entertainment, Inc. Reports Fourth Quarter Results</a>
  </div>
</article>
<article class="clearfix node node--nir-news--nir-widget-list node--type-nir-news node--view-mode-nir-widget-list node--promoted">
  <div class="nir-widget--field nir-widget--news--date-time">February 23, 2026</div>
  <div class="nir-widget--field nir-widget--news--headline">
    <a href="/news-releases/news-release-details/penn-entertainment-appoints-three-new-independent-directors" hreflang="en">PENN Entertainment Appoints Three New Independent Directors to Board</a>
  </div>
</article>
<article class="clearfix node node--nir-news--nir-widget-list node--type-nir-news node--view-mode-nir-widget-list node--promoted">
  <div class="nir-widget--field nir-widget--news--date-time">January 20, 2026</div>
  <div class="nir-widget--field nir-widget--news--headline">
    <a href="/news-releases/news-release-details/penn-entertainment-report-fourth-quarter-results-and-host-2" hreflang="en">PENN Entertainment to Report Fourth Quarter Results and Host Conference Call and Webcast on February 26</a>
  </div>
</article>"""

parser = PennHtmlParser()
url = 'https://investors.pennentertainment.com/press-releases'
result = parser.parse_listing(html, url, 'PENN Entertainment')

print(f'COUNT: {len(result.candidate_urls)}')
print(f'REASON: {result.empty_reason}')
print()
for i, url in enumerate(result.candidate_urls[:3], 1):
    title = result.candidate_titles.get(url, 'N/A')
    date = result.candidate_published_dates.get(url, 'N/A')
    print(f'{i}. {title}')
    print(f'   URL: {url}')
    print(f'   Date: {date}')
    print()
