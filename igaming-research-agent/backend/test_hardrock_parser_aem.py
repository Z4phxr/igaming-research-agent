#!/usr/bin/env python
"""Quick test of updated Hard Rock parser with AEM card structure."""

from app.services.portal_scrapers.parsers.hardrock_html import HardRockHtmlParser
import datetime

html = """<div class="aem-Grid aem-Grid--9 aem-Grid--tablet--12 aem-Grid--default--9 aem-Grid--phone--9">
    <div class="title cmp-title--left aem-GridColumn--tablet--12 aem-GridColumn--default--9 aem-GridColumn aem-GridColumn--phone--9"><div id="title-026c2b1ff3" class="cmp-title ">
   <h2 class="cmp-title__text">
      Latest Headlines
   </h2>
</div></div>

<div class="newssearchresult cfcards cf-list hrccard--split hrccard--listcard hrccard--img-left aem-GridColumn--tablet--12 aem-GridColumn--default--9 aem-GridColumn aem-GridColumn--phone--9">
  <div class="cfcards news-cf cmp-button--primary">
        <div class="cmp-teaser">
          <div class="cmp-teaser__content">
		  <ul class="cmp-contentfragment__element--categories">
              <li>
               	<a class="cmp-teaser__tags" href="/blog/results.category.page.1?keyword=shrss:news-categories/press-releases">Press Releases</a>
              </li>
			
              <li>
               	<a class="cmp-teaser__tags" href="/blog/results.category.page.1?keyword=shrss:news-categories/hotel-news">Hotel News</a>
              </li>
			
              <li>
               	<a class="cmp-teaser__tags" href="/blog/results.category.page.1?keyword=shrss:brands/hri">Hard Rock International</a>
              </li>
			</ul>
			<a class="cmp-teaser__title" href="/blog/hard-rock-hotel-malta-now-accepting-bookings-summer-2026-debut">
              Hard Rock Hotel Malta Now Accepting Bookings for Summer 2026 Debut
            </a>
			
            <h3 class="cmp-teaser__date"> March 24, 2026</h3>
              
            <div class="cmp-teaser__description">
              <p>
                Hard Rock International announces reservations are now open to bookings for July 2026 and onward at the highly anticipated Hard Rock Hotel Malta.
              </p>
            </div>
            <div class="cmp-teaser__action-container">
              <div class="button">
                <a href="/blog/hard-rock-hotel-malta-now-accepting-bookings-summer-2026-debut" class="cmp-button">
                  Read more
                </a>
              </div>
            </div>
          </div>
           <div class="cmp-teaser__image">
            <div class="cmp-image" itemscope="" alt="card image" title="Hard Rock International announces reservations are now open to bookings for July 2026 and onward at the highly anticipated Hard Rock Hotel Malta.">
                <img src="/adobe/dynamicmedia/deliver/dm-aid--6e83f193-672d-4184-89d7-acf09558cc86/hot-malta-aerial-view-2000x1100.jpg.webp?preferwebp=true&quality=85" loading="lazy" class="cmp-image__image" alt="Hard Rock Malta"/>
              <meta itemprop="caption" content="Hard Rock International announces reservations are now open to bookings for July 2026 and onward at the highly anticipated Hard Rock Hotel Malta."/>
            </div>
          </div>
        </div>
      </div>
</div>
</div>"""

parser = HardRockHtmlParser()
url = 'https://www.hardrock.com/blog'
result = parser.parse_listing(html, url, 'Hard Rock Bet')

print(f'COUNT: {len(result.candidate_urls)}')
print(f'REASON: {result.empty_reason}')
print()
if result.candidate_urls:
    for i, url in enumerate(result.candidate_urls[:3], 1):
        title = result.candidate_titles.get(url, 'N/A')
        date = result.candidate_published_dates.get(url, 'N/A')
        print(f'{i}. {title}')
        print(f'   URL: {url}')
        print(f'   Date: {date}')
        print()
