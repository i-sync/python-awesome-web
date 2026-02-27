import asyncio

from app.services.sitemap import SitemapCache, build_sitemap_xml


def test_build_sitemap_xml_contains_home_and_blog_urls():
    rows = [
        {'id': 'post-1', 'updated_at': 1700000000},
        {'id': 'a&b', 'updated_at': 1700000100},
    ]
    xml = build_sitemap_xml('https://example.com/', rows)

    assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert '<loc>https://example.com</loc>' in xml
    assert '<loc>https://example.com/blog/post-1</loc>' in xml
    assert '<loc>https://example.com/blog/a&amp;b</loc>' in xml
    assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in xml


def test_sitemap_cache_hits_within_ttl():
    now = [1000.0]
    calls = {'count': 0}

    async def builder():
        calls['count'] += 1
        return 'xml-{}'.format(calls['count'])

    cache = SitemapCache(ttl_seconds=300, time_fn=lambda: now[0])

    first = asyncio.run(cache.get_or_build(builder, key='site-a'))
    second = asyncio.run(cache.get_or_build(builder, key='site-a'))

    assert first == 'xml-1'
    assert second == 'xml-1'
    assert calls['count'] == 1


def test_sitemap_cache_expires_and_invalidate_works():
    now = [1000.0]
    calls = {'count': 0}

    async def builder():
        calls['count'] += 1
        return 'xml-{}'.format(calls['count'])

    cache = SitemapCache(ttl_seconds=10, time_fn=lambda: now[0])

    v1 = asyncio.run(cache.get_or_build(builder, key='site-a'))
    now[0] += 11
    v2 = asyncio.run(cache.get_or_build(builder, key='site-a'))
    cache.invalidate()
    v3 = asyncio.run(cache.get_or_build(builder, key='site-a'))

    assert v1 == 'xml-1'
    assert v2 == 'xml-2'
    assert v3 == 'xml-3'
    assert calls['count'] == 3
