# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""
In process LRU cache for report execution results.

Scope: a single Odoo worker. Multi worker consistency relies on the
res.company.eh_move_version counter, not on shared cache. A miss on one
worker still triggers recomputation, but the result will agree with other
workers because the version counter participates in the cache key.

Phase 2 will add a Redis or DB backed shared cache. For Phase 1 the in
process LRU is sufficient and avoids any external dependency.
"""

import threading
from collections import OrderedDict


class ReportCache:
    """Thread safe LRU cache.

    Keys are arbitrary hashable tuples (typically (report_code, options_hash,
    move_version_total)). Values are arbitrary Python objects (typically
    serialised report payloads or row lists).
    """

    DEFAULT_MAX_ENTRIES = 256

    def __init__(self, max_entries=None):
        self._lock = threading.Lock()
        self._entries = OrderedDict()
        self._max_entries = int(max_entries or self.DEFAULT_MAX_ENTRIES)
        self._hits = 0
        self._misses = 0

    def get(self, key):
        with self._lock:
            if key in self._entries:
                value = self._entries.pop(key)
                self._entries[key] = value
                self._hits += 1
                return value
            self._misses += 1
            return None

    def put(self, key, value):
        with self._lock:
            if key in self._entries:
                self._entries.pop(key)
            self._entries[key] = value
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    def invalidate(self, predicate=None):
        """Remove cache entries.

        If predicate is None, clears the whole cache. Otherwise removes
        entries where predicate(key) returns True.
        """
        with self._lock:
            if predicate is None:
                self._entries.clear()
                return
            to_remove = [k for k in self._entries if predicate(k)]
            for k in to_remove:
                self._entries.pop(k)

    def clear(self):
        with self._lock:
            self._entries.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self):
        with self._lock:
            return {
                'hits': self._hits,
                'misses': self._misses,
                'size': len(self._entries),
                'max_entries': self._max_entries,
            }


# Module level singleton, one per worker process.
_REPORT_CACHE = ReportCache()


def get_cache():
    """Return the worker scoped report cache singleton."""
    return _REPORT_CACHE


def reset_cache_for_tests():
    """Test helper: clear the singleton's state. Do not call from production."""
    _REPORT_CACHE.clear()
