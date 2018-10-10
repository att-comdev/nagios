#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import sys

from contextlib import contextmanager

class AICMonUtil(object):
    @staticmethod
    def service_ok(message):
        print('OK: %s' % message)
        sys.exit(0)

    @staticmethod
    def service_warning(message):
        print('WARNING: %s' % message)
        sys.exit(1)

    @staticmethod
    def service_critical(message):
        print('CRITICAL: %s' % message)
        sys.exit(2)

    @staticmethod
    def service_unknown(message):
        print('UNKNOWN: %s' % message)
        sys.exit(3)

    @staticmethod
    def trim_str(my_str):
        """Return trimmed string or empty string"""
        if my_str:
            my_str = my_str.strip()
        else:
            my_str = ''
        return my_str

    @staticmethod
    def is_success(response):
        return (response and hasattr(response, 'status_code') and
                response.status_code >= 200 and response.status_code <= 299)

    @staticmethod
    @contextmanager
    def suppress_stdout():
        """Suppress stdout output"""
        with open(os.devnull, "w") as devnull:
            old_stdout = sys.stdout
            sys.stdout = devnull
            try:
                yield
            finally:
                sys.stdout = old_stdout
