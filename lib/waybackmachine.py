"""Define related tools for web.archive.org (aka Wayback Machine)."""

import logging
from threading import Thread
from datetime import date
from urllib.parse import urlparse

from regex import compile as regex_compile
from requests import ConnectionError as RequestsConnectionError

from lib.urls import (
    url_to_dict as urls_url_to_dict, url2dict, analyze_home, get_html, find_authors,
    find_journal, find_site_name, find_title, ContentTypeError,
    ContentLengthError, StatusCodeError, TITLE_TAG
)


URL_FULLMATCH = regex_compile(
    r'https?+://web(?:-beta)?+\.archive\.org/(?:web/)?+'
    r'(\d{4})(\d{2})(\d{2})\d{6}(?>cs_|i(?>d_|m_)|js_)?+/(http.*)'
).fullmatch


def url_to_dict(
    archive_url: str, date_format: str = '%Y-%m-%d'
) -> dict:
    """Create the response namedtuple."""
    if (m := URL_FULLMATCH(archive_url)) is None:
        # Could not parse the archive_url. Treat as an ordinary URL.
        return urls_url_to_dict(archive_url, date_format)
    archive_year, archive_month, archive_day, original_url = \
        m.groups()
    original_dict = {}
    thread = Thread(
        target=original_url2dict, args=(original_url, original_dict)
    )
    thread.start()
    archive_dict = url2dict(archive_url)
    archive_dict['date_format'] = date_format
    archive_dict['url'] = original_url
    archive_dict['archive-url'] = archive_url
    archive_dict['archive-date'] = date(
        int(archive_year), int(archive_month), int(archive_day)
    )
    thread.join()
    if original_dict:
        # The original_process has been successful
        if (
            original_dict['title'] == archive_dict['title']
            or original_dict['html_title'] == archive_dict['html_title']
        ):
            archive_dict.update(original_dict)
            archive_dict['url-status'] = 'live'
        else:
            # and original title is the same as archive title. Otherwise it
            # means that the content probably has changed and the original data
            # cannot be trusted.
            archive_dict['url-status'] = 'unfit'
    else:
        archive_dict['url-status'] = 'dead'
    if archive_dict['website'] == 'Wayback Machine':
        archive_dict['website'] = (
            urlparse(original_url).hostname.replace('www.', '')
        )
    return archive_dict


def original_url2dict(ogurl: str, original_dict) -> None:
    """Fill the dictionary with the information found in ogurl."""
    # noinspection PyBroadException
    try:
        original_dict.update(original_url_dict(ogurl))
    except (
        ContentTypeError,
        ContentLengthError,
        StatusCodeError,
        RequestsConnectionError,
    ):
        pass
    except Exception:
        logger.exception(
            'There was an unexpected error in waybackmechine thread'
        )


def original_url_dict(url: str):
    """Retuan dictionary only containing required data for og:url."""
    d = {}
    # Creating a thread to request homepage title in background
    hometitle_list = []  # A mutable variable used to get the thread result
    home_title_thread = Thread(
        target=analyze_home, args=(url, hometitle_list)
    )
    home_title_thread.start()
    html = get_html(url)

    if (m := TITLE_TAG(html)) is not None:
        if html_title := m['result']:
            d['html_title'] = html_title
    else:
        html_title = None

    if authors := find_authors(html):
        d['authors'] = authors

    if journal := find_journal(html):
        d['journal'] = journal
        d['cite_type'] = 'journal'
    else:
        d['cite_type'] = 'web'
        d['website'] = find_site_name(
            html, html_title, url, authors, hometitle_list, home_title_thread
        )
    d['title'] = find_title(
        html, html_title, url, authors, hometitle_list, home_title_thread
    )
    return d


logger = logging.getLogger(__name__)
