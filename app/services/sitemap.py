import asyncio
import os
import time
from datetime import datetime
from xml.sax.saxutils import escape

from app.config import configs
from app.db import orm
from app.logger import logger


def _normalize_base_url(url):
    value = (url or '').strip()
    return value.rstrip('/')


def get_sitemap_ttl_seconds():
    raw = os.getenv('SITEMAP_CACHE_TTL', '300')
    try:
        ttl = int(raw)
    except (TypeError, ValueError):
        ttl = 300
    return max(ttl, 0)


def format_lastmod(timestamp):
    try:
        return datetime.fromtimestamp(float(timestamp)).strftime('%Y-%m-%d')
    except (TypeError, ValueError, OSError):
        return datetime.utcnow().strftime('%Y-%m-%d')


async def fetch_sitemap_rows():
    return await orm.select('SELECT id, updated_at FROM blogs WHERE enabled=? ORDER BY updated_at DESC', [True])


def build_sitemap_xml(base_url, rows):
    base = _normalize_base_url(base_url)
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

    if base:
        parts.extend(
            [
                '  <url>',
                '    <loc>{}</loc>'.format(escape(base)),
                '    <changefreq>daily</changefreq>',
                '    <priority>1.0</priority>',
                '  </url>',
            ]
        )

    for row in rows:
        blog_id = str(row.get('id', '')).strip()
        if not blog_id:
            continue
        loc = '{}/blog/{}'.format(base, blog_id) if base else '/blog/{}'.format(blog_id)
        parts.extend(
            [
                '  <url>',
                '    <loc>{}</loc>'.format(escape(loc)),
                '    <lastmod>{}</lastmod>'.format(format_lastmod(row.get('updated_at'))),
                '    <changefreq>daily</changefreq>',
                '    <priority>1.0</priority>',
                '  </url>',
            ]
        )

    parts.append('</urlset>')
    return '\n'.join(parts)


class SitemapCache(object):
    def __init__(self, ttl_seconds=300, time_fn=None):
        self._ttl_seconds = max(0, int(ttl_seconds))
        self._time_fn = time_fn or time.time
        self._xml = None
        self._key = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def get_or_build(self, builder, *, key=None, force=False):
        now = self._time_fn()
        if (not force) and self._xml is not None and key == self._key and now < self._expires_at:
            return self._xml

        async with self._lock:
            now = self._time_fn()
            if (not force) and self._xml is not None and key == self._key and now < self._expires_at:
                return self._xml

            xml = await builder()
            self._xml = xml
            self._key = key
            self._expires_at = now + self._ttl_seconds
            return xml

    def invalidate(self):
        self._xml = None
        self._key = None
        self._expires_at = 0.0


_sitemap_cache = SitemapCache(ttl_seconds=get_sitemap_ttl_seconds())


def resolve_sitemap_base_url(request=None):
    configured = _normalize_base_url(getattr(configs.web_meta, 'base_url', ''))
    if configured:
        return configured
    if request is not None:
        return _normalize_base_url(str(request.url.origin()))
    return ''


async def build_current_sitemap_xml(base_url):
    rows = await fetch_sitemap_rows()
    return build_sitemap_xml(base_url, rows)


async def get_cached_sitemap_xml(base_url):
    key = _normalize_base_url(base_url)

    async def _builder():
        return await build_current_sitemap_xml(key)

    return await _sitemap_cache.get_or_build(_builder, key=key)


def invalidate_sitemap_cache():
    logger.info('Invalidate sitemap cache')
    _sitemap_cache.invalidate()
