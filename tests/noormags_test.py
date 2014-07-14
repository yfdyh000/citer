#! /usr/bin/python
# -*- coding: utf-8 -*-

"""Test noormags.py module."""


import unittest
import sys

import dummy_requests
sys.path.append('..')
import noormags


class NoormagsTest(unittest.TestCase):

    def test_nm1(self):
        i = 'http://www.noormags.com/view/fa/articlepage/5798/102/Text'
        o = noormags.Response(i)
        e = '* {{cite journal|last=موسوی|first=زهرا|title=مقرنس در معماری|journal=کتاب ماه هنر|issue=45|year=1381|pages=102–106|url=http://www.noormags.com/view/fa/articlepage/104040|language=fa|ref=harv|accessdate='
        self.assertIn(e, o.ctnt)

    def test_nm2(self):
        """The second author does not have a last name. (Bibtex file error)"""
        i = 'http://www.noormags.com/view/fa/articlepage/261461'
        o = noormags.Response(i)
        e = '* {{cite journal|last=ایرانی|first=هوشنگ|author2=آ. ولف|title=لوژیستیک|journal=دانش|issue=6|year=1328|pages=316–324|url=http://www.noormags.com/view/fa/articlepage/261461|language=fa|ref=harv|accessdate='
        self.assertIn(e, o.ctnt)


noormags.requests = dummy_requests.DummyRequests()
if __name__ == '__main__':
    unittest.main()