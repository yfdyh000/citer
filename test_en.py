#! /usr/bin/python
# -*- coding: utf-8 -*-

"""Discover all tests (except the ones inside test_fa.py) and run them."""


import unittest


if __name__ == '__main__':
    tests = unittest.defaultTestLoader.discover('.', '*_test.py')
    runner = unittest.runner.TextTestRunner()
    runner.run(tests)