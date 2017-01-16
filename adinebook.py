#! /usr/bin/python
# -*- coding: utf-8 -*-

"""All things that are specifically related to adinebook website"""

import re
import logging

import requests
from bs4 import BeautifulSoup

import commons


class Response(commons.BaseResponse):

    """Create Adinebook's response object."""

    def __init__(self, adinebook_url: str, date_format: str='%Y-%m-%d'):
        """Make the dictionary and run self.generate()."""
        self.date_format = date_format
        self.url = adinebook_url
        self.dictionary = url2dictionary(adinebook_url)
        if 'language' not in self.dictionary:
            # assume that language is either fa or en
            # todo: give warning about this assumption
            self.detect_language(self.dictionary['title'], {'en', 'fa'})
        self.generate()


def isbn2url(isbn: str):
    """Convert isbn to AdinebookURL. Return the url as string."""
    # Apparently adinebook uses 10 digit codes (without hyphens) for its
    # book-urls. If it's an isbn13 then the first 3 digits are excluded
    isbn = isbn.replace('-', '')
    isbn = isbn.replace(' ', '')
    if len(isbn) == 13:
        isbn = isbn[3:]
    url = 'http://www.adinebook.com/gp/product/' + isbn
    return url


def url2dictionary(adinebook_url: str):
    """Get adinebook_url and return the result as a dict."""
    try:
        # Try to see if adinebook is available,
        # ottobib should continoue its work in isbn.py if it is not.
        headers = {
            'User-agent':
            'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:33.0) '
            'Gecko/20100101 Firefox/33.0'
        }
        r = requests.get(adinebook_url, headers=headers)
        adinebook_html = r.content.decode('utf-8')
    except Exception:
        logger.exception(adinebook_url)
        return
    if 'صفحه مورد نظر پبدا نشد.' in adinebook_html:
        return
    else:
        d = {'type': 'book'}  # type: Dict[str: Any]
        bs = BeautifulSoup(adinebook_html, 'lxml')
        if bs.title:
            m = re.search(
                'آدینه بوک:\s*(?P<title>.*?)\s*~(?P<names>.*?)\s*$',
                bs.title.text
            )
            if m:
                d['title'] = m.group('title')
        names = m.group('names').split('،')
        # initiating name lists:
        if m.group('names'):
            d['authors'] = []
            d['others'] = []
        if '(ويراستار)' in m.group('names'):
            d['editors'] = []
        if '(مترجم)' in m.group('names'):
            d['translators'] = []
        # building lists:
        for name in names:
            if '(ويراستار)' in name:
                d['editors'].append(commons.Name(name.split('(ويراستار)')[0]))
            elif '(مترجم)' in name:
                d['translators'].append(commons.Name(name.split('(مترجم)')[0]))
            elif '(' in name:
                d['others'].append(commons.Name(re.split('\(.*\)', name)[0]))
                d['others'][-1].fullname = name
            else:
                d['authors'].append(commons.Name(name))
        if not d['authors']:
            del d['authors']
        if not d['others']:
            del d['others']
        m = re.search('نشر:</b>\s*(.*?)\s*\(.*</li>', adinebook_html)
        if m:
            d['publisher'] = m.group(1)
        m = re.search('نشر:</b>.*\([\d\s]*(.*?)،.*', adinebook_html)
        if m:
            d['month'] = m.group(1)
        m = re.search('نشر:</b>.*?\(.*?(\d\d\d\d)\)</li>', adinebook_html)
        if m:
            d['year'] = m.group(1)
        m = re.search('شابک:.*?([\d-]*X?)</span></li>', adinebook_html)
        if m:
            d['isbn'] = m.group(1)
    return d

logger = logging.getLogger(__name__)
