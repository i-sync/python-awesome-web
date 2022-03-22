# coding=UTF-8
import sys
import asyncio
import aiomysql
import datetime
from config import configs


loop = asyncio.get_event_loop()

async def generate_sitemap():
    conn = await aiomysql.connect(host=configs.database.host,
                                  port=configs.database.port,
                                  user=configs.database.user,
                                  password=configs.database.password,
                                  db=configs.database.database,
                                  loop = loop)

    cur = await conn.cursor()
    await cur.execute("SELECT id, created_at FROM blogs where enabled=1")

    sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{configs.web_meta.base_url}</loc>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>'''

    for row in await cur.fetchall():
        id = row[0]
        created_at = row[1]        
        date_time = datetime.fromtimestamp(created_at)
        str_date = date_time.strftime("%Y-%m-%d")
        item = f'''
        <url>
            <loc>{configs.web_mate.base_url}/blog/{id}/</loc>
            <lastmod>{str_date}</lastmod>
            <changefreq>daily</changefreq>
            <priority>1.0</priority>
        </url>'''
        sitemap = sitemap + item
    sitemap = sitemap +'''
    </urlset>'''

    await cur.close()
    conn.close()

    with open("./sitemap.xml", "w+", encoding="utf-8") as f:
        f.writelines(sitemap)

if __name__=="__main__":
    loop.run_until_complete(generate_sitemap())