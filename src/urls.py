#! /usr/bin/python
# -*- coding: utf-8 -*-

"""Codes used for parsing contents of an arbitrary URL."""


from collections import defaultdict
from datetime import date as datetime_date
from difflib import get_close_matches
from html import unescape as html_unescape
import logging
import re
from threading import Thread
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse

from langid import classify
import regex
from requests import get as requests_get, Response as RequestsResponse
from requests.exceptions import RequestException

from src.commons import (
    find_any_date, Response, USER_AGENT_HEADER,
    dictionary_to_response, ANYDATE_PATTERN, Name,
)
from src.urls_authors import find_authors, CONTENT_ATTR


MAX_RESPONSE_LENGTH = 2_000_000

# https://stackoverflow.com/questions/3458217/how-to-use-regular-expression-to-match-the-charset-string-in-html
CHARSET = re.compile(
    rb'''<meta(?!\s*(?:name|value)\s*=)[^>]*?charset\s*=[\s"']*([^\s"'/>]*)''',
    re.IGNORECASE,
).search

TITLE_META_NAME_OR_PROP = r'''
    (?>name|property)=(?<q>["\'])
        (?>citation_title|title|Headline|og:title)
    (?P=q)
'''
TITLE_SEARCH = regex.compile(
    rf'''
    <meta\s+(?:
        {TITLE_META_NAME_OR_PROP}\s+{CONTENT_ATTR}
        |
        {CONTENT_ATTR}\s+{TITLE_META_NAME_OR_PROP}
    )
    |
    class=(?<q>["\'])(?>main-hed|heading1)(?P=q)[^>]+?>(?<result>.*?)<
    ''',
    regex.VERBOSE | regex.IGNORECASE,
).search

TITLE_TAG = re.compile(
    r'''
    <title\b[^>]*>
        (?P<result>\s*[\s\S]*?\s*)
    </title\s*>
    ''',
    re.VERBOSE | re.IGNORECASE,
).search

DATE_META_NAME_OR_PROP = r'''
    (?>name|property)=(?<q>["\'])(?>
        article:(?>modified_time|published_time)
        |citation_(?>date|publication_date)
        |date
        |DC.date.[^'"\n>]*
        |last-modified
        |pub_?date
        |sailthru\.date
    )(?P=q)
'''
DATE_CONTENT_ATTR = rf'''
    content=(?<q>["\'])[^"'<]*?{ANYDATE_PATTERN}(?>[^"'<]*?(?P=q))
'''
DATE_SEARCH = regex.compile(
    rf'''
    <meta\s+[^\n<]*?(?:
        {DATE_META_NAME_OR_PROP}\s+[^\n<]*?{DATE_CONTENT_ATTR}
        |
        {DATE_CONTENT_ATTR}\s+[^\n<]*?{DATE_META_NAME_OR_PROP}
    )
    |
    # http://livescience.com/46619-sterile-neutrino-experiment-beginning.html
    # https://www.thetimes.co.uk/article/woman-who-lost-brother-on-mh370-mourns-relatives-on-board-mh17-r07q5rwppl0
    date(?>Published|line)[^\w]+?{ANYDATE_PATTERN}
    ''',
    regex.VERBOSE | regex.IGNORECASE,
).search

JOURNAL_META_NAME_OR_PROP = r'''
    (?>name|property)=(?<q>["\'])citation_journal_title(?P=q)
'''
JOURNAL_TITLE_SEARCH = regex.compile(
    rf'''
    <meta\s+[^\n<]*?(?:
        {CONTENT_ATTR}\s+[^\n<]*?{JOURNAL_META_NAME_OR_PROP}
        |
        {JOURNAL_META_NAME_OR_PROP}\s+[^\n<]*?{CONTENT_ATTR}
    )
    ''',
    re.VERBOSE | re.IGNORECASE,
).search

URL_META_NAME_OR_PROP = r'''
    (?>name|property)=(?<q>["\'])og:url(?P=q)
'''
URL_SEARCH = regex.compile(
    rf'''
    <meta\s+[^\n<]*?(?:
        {CONTENT_ATTR}\s+[^\n<]*?{URL_META_NAME_OR_PROP}
        |
        {URL_META_NAME_OR_PROP}\s+[^\n<]*?{CONTENT_ATTR}
    )
    ''',
    re.VERBOSE | re.IGNORECASE,
).search

ISSN_META_NAME_OR_PROP = r'''
    (?>name|property)=(?<q>["\'])citation_issn(?P=q)
'''
ISSN_SEARCH = regex.compile(
    rf'''
    <meta\s+[^\n<]*?(?:
        {CONTENT_ATTR}\s+[^\n<]*?{ISSN_META_NAME_OR_PROP}
        |
        {ISSN_META_NAME_OR_PROP}\s+[^\n<]*?{CONTENT_ATTR}
    )
    ''',
    re.VERBOSE | re.IGNORECASE,
).search

PMID_META_NAME_OR_PROP = r'''
    (?>name|property)=(?<q>["\'])citation_pmid(?P=q)
'''
PMID_SEARCH = regex.compile(
    rf'''
    <meta\s+[^\n<]*?(?:
        {CONTENT_ATTR}\s+[^\n<]*?{PMID_META_NAME_OR_PROP}
        |
        {PMID_META_NAME_OR_PROP}\s+[^\n<]*?{CONTENT_ATTR}
    )
    ''',
    re.VERBOSE | re.IGNORECASE,
).search

DOI_META_NAME_OR_PROP = r'''
    (?>name|property)=(?<q>["\'])citation_doi(?P=q)
'''
DOI_SEARCH = regex.compile(
    rf'''
    <meta\s+[^\n<]*?(?:
        {CONTENT_ATTR}\s+[^\n<]*?{DOI_META_NAME_OR_PROP}
        |
        {DOI_META_NAME_OR_PROP}\s+[^\n<]*?{CONTENT_ATTR}
    )
    ''',
    re.VERBOSE | re.IGNORECASE,
).search


VOLUME_META_NAME_OR_PROP = r'''
    (?>name|property)=(?<q>["\'])citation_volume(?P=q)
'''
VOLUME_SEARCH = regex.compile(
    rf'''
    <meta\s+[^\n<]*?(?:
        {CONTENT_ATTR}\s+[^\n<]*?{VOLUME_META_NAME_OR_PROP}
        |
        {VOLUME_META_NAME_OR_PROP}\s+[^\n<]*?{CONTENT_ATTR}
    )
    ''',
    re.VERBOSE | re.IGNORECASE,
).search

ISSUE_META_NAME_OR_PROP = r'''
    (?>name|property)=(?<q>["\'])citation_issue(?P=q)
'''
ISSUE_SEARCH = regex.compile(
    rf'''
    <meta\s+[^\n<]*?(?:
        {CONTENT_ATTR}\s+[^\n<]*?{ISSUE_META_NAME_OR_PROP}
        |
        {ISSUE_META_NAME_OR_PROP}\s+[^\n<]*?{CONTENT_ATTR}
    )
    ''',
    re.VERBOSE | re.IGNORECASE,
).search

FIRST_PAGE_NAME_OR_PROP = r'''
    (?>name|property)=(?<q>["\'])citation_firstpage(?P=q)
'''
FIRST_PAGE_SEARCH = regex.compile(
    rf'''
    <meta\s+[^\n<]*?(?:
        {CONTENT_ATTR}\s+[^\n<]*?{FIRST_PAGE_NAME_OR_PROP}
        |
        {FIRST_PAGE_NAME_OR_PROP}\s+[^\n<]*?{CONTENT_ATTR}
    )
    ''',
    re.VERBOSE | re.IGNORECASE,
).search


LAST_PAGE_NAME_OR_PROP = r'''
    (?>name|property)=(?<q>["\'])citation_lastpage(?P=q)
'''
LAST_PAGE_SEARCH = regex.compile(
    rf'''
    <meta\s+[^\n<]*?(?:
        {CONTENT_ATTR}\s+[^\n<]*?{LAST_PAGE_NAME_OR_PROP}
        |
        {LAST_PAGE_NAME_OR_PROP}\s+[^\n<]*?{CONTENT_ATTR}
    )
    ''',
    re.VERBOSE | re.IGNORECASE,
).search


SITE_NAME_NAME_OR_PROP = r'''
    (?>name|property)=(?<q>["\'])og:site_name(?P=q)
'''
SITE_NAME_SEARCH = regex.compile(
    rf'''
    <meta\s+[^\n<]*?(?:
        {CONTENT_ATTR}\s+[^\n<]*?{SITE_NAME_NAME_OR_PROP}
        |
        {SITE_NAME_NAME_OR_PROP}\s+[^\n<]*?{CONTENT_ATTR}
    )
    ''',
    re.VERBOSE | re.IGNORECASE,
).search


class ContentTypeError(ValueError):

    """Raise when content-type header does not start with 'text/'."""

    pass


class ContentLengthError(ValueError):

    """Raise when content-length header indicates a very long content."""

    pass


class StatusCodeError(ValueError):

    """Raise when requests_get.status_code != 200."""

    pass


def urls_response(url: str, date_format: str= '%Y-%m-%d') -> Response:
    """Create the response namedtuple."""
    try:
        dictionary = url2dict(url)
    except (ContentTypeError, ContentLengthError) as e:
        logger.exception(url)
        return Response(sfn='Could not process the request.', cite=e, ref='')
    dictionary['date_format'] = date_format
    return dictionary_to_response(dictionary)


def find_journal(html: str) -> Optional[str]:
    """Return journal title as a string."""
    # http://socialhistory.ihcs.ac.ir/article_319_84.html
    m = JOURNAL_TITLE_SEARCH(html)
    if m:
        return m['result']


def find_url(html: str, url: str) -> str:
    """Return og:url or url as a string."""
    # http://www.ft.com/cms/s/836f1b0e-f07c-11e3-b112-00144feabdc0,Authorised=false.html?_i_location=http%3A%2F%2Fwww.ft.com%2Fcms%2Fs%2F0%2F836f1b0e-f07c-11e3-b112-00144feabdc0.html%3Fsiteedition%3Duk&siteedition=uk&_i_referer=http%3A%2F%2Fwww.ft.com%2Fhome%2Fuk
    m = URL_SEARCH(html)
    if m:
        ogurl = m['result']
        if urlparse(ogurl).path:
            return ogurl
    return url


def find_issn(html: str) -> Optional[str]:
    """Return International Standard Serial Number as a string.

    Normally ISSN should be in the  '\d{4}\-\d{3}[\dX]' format, but this
    function does not check that.
    """
    m = ISSN_SEARCH(html)
    # http://socialhistory.ihcs.ac.ir/article_319_84.html
    # http://psycnet.apa.org/journals/edu/30/9/641/
    if m:
        return m['result']


def find_pmid(html: str) -> Optional[str]:
    """Return pmid as a string."""
    # http://jn.physiology.org/content/81/1/319
    m = PMID_SEARCH(html)
    if m:
        return m['result']


def find_doi(html: str) -> Optional[str]:
    """Return DOI as a string."""
    # http://jn.physiology.org/content/81/1/319
    m = DOI_SEARCH(html)
    if m:
        return m['result']


def find_volume(html: str) -> Optional[str]:
    """Return citatoin volume number as a string."""
    # http://socialhistory.ihcs.ac.ir/article_319_84.html
    m = VOLUME_SEARCH(html)
    if m:
        return m['result']


def find_issue(html: str) -> Optional[str]:
    """Return citation issue number as a string."""
    # http://socialhistory.ihcs.ac.ir/article_319_84.html
    m = ISSUE_SEARCH(html)
    if m:
        return m['result']


def find_pages(html: str) -> Optional[str]:
    """Return citation pages as a string."""
    # http://socialhistory.ihcs.ac.ir/article_319_84.html
    fp_match = FIRST_PAGE_SEARCH(html)
    if fp_match:
        lp_match = LAST_PAGE_SEARCH(html)
        if lp_match:
            return \
                fp_match['result'] + '–' + lp_match['result']


def find_site_name(
    html: str,
    html_title: str,
    url: str,
    authors: List[Name],
    home_title: List[str],
    thread: Thread,
) -> str:
    """Return (site's name as a string, where).

    Parameters:
        html: The html string of the page being processed.
        html_title: Title of the page found in the title tag of the html.
        url: URL of the page.
        authors: Authors list returned from find_authors function.
        home_title: A list containing the title of the home page as a str.
        thread: The thread that should be joined before using home_title list.
    Returns site's name as a string.
    """
    m = SITE_NAME_SEARCH(html)
    if m:
        return m['result']
    # search the title
    site_name = parse_title(
        html_title, url, authors, home_title, thread
    )[2]
    if site_name:
        return site_name
    # noinspection PyBroadException
    try:
        # using home_title
        thread.join()
        if ':' in home_title[0]:
            # http://www.washingtonpost.com/wp-dyn/content/article/2005/09/02/AR2005090200822.html
            site_name = home_title[0].split(':')[0].strip()
            if site_name:
                return site_name
        site_name = parse_title(home_title[0], url, None)[2]
        if site_name:
            return site_name
        return home_title[0]
    except Exception:
        logger.exception(url)
    # return hostname
    hostname = urlparse(url).hostname
    if hostname.startswith('www.'):
        return hostname[4:]
    return hostname


def find_title(
    html: str,
    html_title: str,
    url: str,
    authors: List[Name],
    home_title: List[str],
    thread: Thread,
) -> Optional[str]:
    """Return (title_string, where_info)."""
    m = TITLE_SEARCH(html)
    if m:
        return parse_title(
            html_unescape(m['result']), url, authors, home_title, thread,
        )[1]
    elif html_title:
        return parse_title(html_title, url, authors, home_title, thread)[1]
    else:
        return None


def parse_title(
    title: str,
    url: str,
    authors: Optional[List[Name]],
    home_title_list: Optional[List[str]]=None,
    thread: Thread=None,
) -> Tuple[Optional[str], str, Optional[str]]:
    """Return (intitle_author, pure_title, intitle_sitename).

    Examples:

    >>> parse_title("Rockhopper raises Falklands oil estimate - FT.com",
            "http://www.ft.com/cms/s/ea29ffb6-c759-11e0-9cac-00144feabdc0",
            None)
    (None, 'Rockhopper raises Falklands oil estimate', 'FT.com')

    >>> parse_title('some title - FT.com - something unknown',
            "http://www.ft.com/cms/s/ea29ffb6-c759-11e0-9cac-00144feabdc0",
            None)
    (None, 'some title - something unknown', 'FT.com')

    >>> parse_title("Alpha decay - Wikipedia, the free encyclopedia",
            "https://en.wikipedia.org/wiki/Alpha_decay",
            None)
    (None, 'Alpha decay', 'Wikipedia, the free encyclopedia')

    >>> parse_title("	BBC NEWS | Health | New teeth 'could soon be grown'",
            'http://news.bbc.co.uk/2/hi/health/3679313.stm',
            None)
    (None, "Health - New teeth 'could soon be grown'", 'BBC NEWS')
    """
    intitle_author = intitle_sitename = None
    sep_regex = ' - | — |\|'
    title_parts = re.split(sep_regex, title.strip())
    if len(title_parts) == 1:
        return None, title, None
    hostname = urlparse(url).hostname.replace('www.', '')
    # Searching for intitle_sitename
    # 1. In hostname
    hnset = set(hostname.split('.'))
    for part in title_parts:
        if (part in hostname) or not set(part.lower().split()) - hnset:
            intitle_sitename = part
            break
    if not intitle_sitename:
        # 2. Using difflib on hostname
        # Cutoff = 0.3: 'BBC - Homepage' will match u'‭BBC ‮فارسی‬'
        close_matches = get_close_matches(
            hostname, title_parts, n=1, cutoff=.3
        )
        if close_matches:
            intitle_sitename = close_matches[0]
    if not intitle_sitename:
        if thread:
            thread.join()
        if home_title_list:
            home_title = home_title_list[0]
        else:
            home_title = ''
        # 3. In homepage title
        for part in title_parts:
            if part in home_title:
                intitle_sitename = part
                break
    if not intitle_sitename:
        # 4. Using difflib on home_title
        close_matches = get_close_matches(
            home_title, title_parts, n=1, cutoff=.3
        )
        if close_matches:
            intitle_sitename = close_matches[0]
    # Remove sitename from title_parts
    if intitle_sitename:
        title_parts.remove(intitle_sitename)
        intitle_sitename = intitle_sitename.strip()
    # Searching for intitle_author
    if authors:
        for author in authors:
            for part in title_parts:
                if author.lastname.lower() in part.lower():
                    intitle_author = part
                    break
    # Remove intitle_author from title_parts
    if intitle_author:
        title_parts.remove(intitle_author)
        intitle_author = intitle_author.strip()
    pure_title = ' - '.join(title_parts)
    return intitle_author, pure_title, intitle_sitename


def find_date(html: str, url: str) -> datetime_date:
    """Return the date of the document."""
    # Example for find_any_date(url):
    # http://ftalphaville.ft.com/2012/05/16/1002861/recap-and-tranche-primer/?Authorised=false
    # Example for find_any_date(html):
    # https://www.bbc.com/news/uk-england-25462900
    m = DATE_SEARCH(html)
    return find_any_date(m) if m else find_any_date(url) or find_any_date(html)


def get_home_title(url: str, home_title_list: List[str]) -> None:
    """Get homepage of the url and return it's title.

    home_title_list will be used to return the thread result.
    This function is invoked through a thread.
    """
    # Todo: cache the result.
    home_url = '://'.join(urlparse(url)[:2])
    with requests_get(
        home_url, stream=True, headers=USER_AGENT_HEADER, timeout=15
    ) as r:
        try:
            check_response_headers(r)
        except (
            RequestException, StatusCodeError,
            ContentTypeError, ContentLengthError,
        ):
            return
        content = next(r.iter_content(MAX_RESPONSE_LENGTH))
    m = CHARSET(content)
    html = content.decode(m[1].decode() if m else r.encoding)
    m = TITLE_TAG(html)
    title = html_unescape(m['result']) if m else None
    home_title_list.append(title)


def check_response_headers(r: RequestsResponse) -> None:
    """Check content-type and content-length of the response.

    Raise ContentLengthError or ContentTypeError when appropriate.

    """
    if r.status_code != 200:
        raise StatusCodeError(r.status_code)
    response_headers = r.headers
    if 'content-length' in response_headers:
        bytes_length = int(response_headers['content-length'])
        if bytes_length > MAX_RESPONSE_LENGTH:
            raise ContentLengthError(
                f'Content-length was too long. '
                f'({bytes_length / 1_000_000:.2f} MB)'
            )
    content_type = response_headers.get('content-type')
    if content_type:
        if content_type.startswith('text/'):
            return
        raise ContentTypeError(
            'Invalid content-type: ' +
            content_type + ' (URL-content is supposed to be text/html)'
        )
    return


def get_html(url: str) -> str:
    """Return the html string for the given url."""
    with requests_get(
        url, stream=True, headers=USER_AGENT_HEADER, timeout=15
    ) as r:
        check_response_headers(r)
        content = next(r.iter_content(MAX_RESPONSE_LENGTH))
    charset_match = CHARSET(content)
    return content.decode(
        charset_match[1].decode() if charset_match else r.encoding
    )


def url2dict(url: str) -> Dict[str, Any]:
    """Get url and return the result as a dictionary."""
    d = defaultdict(lambda: None)
    # Creating a thread to fetch homepage title in background
    home_title_list = []  # A mutable variable used to get the thread result
    home_title_thread = Thread(
        target=get_home_title, args=(url, home_title_list)
    )
    home_title_thread.start()

    html = get_html(url)
    d['url'] = find_url(html, url)
    m = TITLE_TAG(html)
    html_title = html_unescape(m['result']) if m else None
    if html_title:
        d['html_title'] = html_title
    # d['html_title'] is used in waybackmechine.py.
    authors = find_authors(html)
    if authors:
        d['authors'] = authors
    d['issn'] = find_issn(html)
    d['pmid'] = find_pmid(html)
    d['doi'] = find_doi(html)
    d['volume'] = find_volume(html)
    d['issue'] = find_issue(html)
    d['page'] = find_pages(html)
    d['journal'] = find_journal(html)
    if d['journal']:
        d['cite_type'] = 'journal'
    else:
        d['cite_type'] = 'web'
        d['website'] = find_site_name(
            html, html_title, url, authors, home_title_list, home_title_thread
        )
    d['title'] = find_title(
        html, html_title, url, authors, home_title_list, home_title_thread
    )
    date = find_date(html, url)
    if date:
        d['date'] = date
        d['year'] = str(date.year)
    d['language'] = classify(html)[0]
    return d


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("langid").setLevel(logging.WARNING)
    logger = logging.getLogger()
else:
    logger = logging.getLogger(__name__)
