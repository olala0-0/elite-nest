# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""
Unit tests for the in process LRU report cache.

Covers:

* Hit and miss accounting.
* LRU ordering and eviction.
* Selective invalidation by predicate.
* Thread safety under concurrent put / get / invalidate.
"""

import threading

from odoo.tests import tagged

from odoo.addons.eh_account_base.tools.report_cache import ReportCache
from .common import EhAccountUnitTestCase


@tagged('eh_account_base', 'unit')
class TestReportCacheBasics(EhAccountUnitTestCase):

    def test_get_miss_returns_none_and_increments_misses(self):
        cache = ReportCache(max_entries=4)
        self.assertIsNone(cache.get(('a', 1)))
        self.assertEqual(cache.stats['misses'], 1)
        self.assertEqual(cache.stats['hits'], 0)

    def test_put_then_get_returns_value(self):
        cache = ReportCache(max_entries=4)
        cache.put(('a', 1), 'payload')
        self.assertEqual(cache.get(('a', 1)), 'payload')
        self.assertEqual(cache.stats['hits'], 1)

    def test_lru_eviction(self):
        cache = ReportCache(max_entries=3)
        cache.put('k1', 1)
        cache.put('k2', 2)
        cache.put('k3', 3)
        # Touch k1 so it is most recently used.
        cache.get('k1')
        # Insert k4: k2 is least recently used and should be evicted.
        cache.put('k4', 4)
        self.assertIsNone(cache.get('k2'))
        self.assertEqual(cache.get('k1'), 1)
        self.assertEqual(cache.get('k4'), 4)
        self.assertEqual(cache.stats['size'], 3)

    def test_repeat_put_updates_value_and_recency(self):
        cache = ReportCache(max_entries=3)
        cache.put('a', 'old')
        cache.put('b', 1)
        cache.put('c', 2)
        cache.put('a', 'new')
        cache.put('d', 3)
        # 'b' was the LRU after the second put('a'), so it should be evicted.
        self.assertIsNone(cache.get('b'))
        self.assertEqual(cache.get('a'), 'new')

    def test_clear(self):
        cache = ReportCache(max_entries=4)
        cache.put('a', 1)
        cache.get('a')
        cache.clear()
        self.assertEqual(cache.stats['size'], 0)
        self.assertEqual(cache.stats['hits'], 0)
        self.assertEqual(cache.stats['misses'], 0)

    def test_invalidate_with_predicate(self):
        cache = ReportCache(max_entries=10)
        cache.put(('profit_loss', 'h1', 1), 'a')
        cache.put(('profit_loss', 'h2', 1), 'b')
        cache.put(('balance_sheet', 'h3', 1), 'c')
        cache.invalidate(lambda k: k[0] == 'profit_loss')
        self.assertIsNone(cache.get(('profit_loss', 'h1', 1)))
        self.assertIsNone(cache.get(('profit_loss', 'h2', 1)))
        self.assertEqual(cache.get(('balance_sheet', 'h3', 1)), 'c')

    def test_invalidate_no_predicate_clears_all(self):
        cache = ReportCache(max_entries=4)
        cache.put('a', 1)
        cache.put('b', 2)
        cache.invalidate()
        self.assertEqual(cache.stats['size'], 0)


@tagged('eh_account_base', 'unit', 'concurrency')
class TestReportCacheThreadSafety(EhAccountUnitTestCase):

    def test_concurrent_put_get_does_not_corrupt(self):
        cache = ReportCache(max_entries=64)
        n_threads = 16
        n_iterations = 500
        errors = []

        def worker(prefix):
            try:
                for i in range(n_iterations):
                    key = (prefix, i % 32)
                    cache.put(key, f"{prefix}-{i}")
                    val = cache.get(key)
                    if val is not None and not val.startswith(f"{prefix}-"):
                        errors.append((prefix, i, val))
            except Exception as exc:  # pragma: no cover
                errors.append((prefix, str(exc)))

        threads = [
            threading.Thread(target=worker, args=(f"t{n}",)) for n in range(n_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"unexpected errors: {errors!r}")
        # Cache size should respect the cap.
        self.assertLessEqual(cache.stats['size'], 64)
