#!/usr/bin/env python3
# coding=UTF-8
import asyncio
from datetime import datetime
from pathlib import Path

from app.config import configs
from app.db import orm

async def generate_sitemap():
    await orm.create_pool(**configs.database)

    try:
        rows = await orm.select('SELECT id, updated_at FROM blogs WHERE enabled=? ORDER BY updated_at DESC', [True])

        sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>{configs.web_meta.base_url}</loc>
            <changefreq>daily</changefreq>
            <priority>1.0</priority>
        </url>'''

        for row in rows:
            blog_id = row['id']
            updated_at = row['updated_at']
            date_time = datetime.fromtimestamp(updated_at)
            str_date = date_time.strftime("%Y-%m-%d")
            item = f'''
        <url>
            <loc>{configs.web_meta.base_url}/blog/{blog_id}</loc>
            <lastmod>{str_date}</lastmod>
            <changefreq>daily</changefreq>
            <priority>1.0</priority>
        </url>'''
            sitemap = sitemap + item
        sitemap = sitemap + '''
    </urlset>'''

        output = Path(__file__).resolve().parents[1] / 'sitemap.xml'
        with open(output, "w+", encoding="utf-8") as f:
            f.writelines(sitemap)
    finally:
        await orm.destroy_pool()

if __name__ == "__main__":
    asyncio.run(generate_sitemap())
