#!/usr/bin/env python3
# coding=UTF-8
import asyncio
from pathlib import Path

from app.config import configs
from app.db import orm
from app.services.sitemap import build_current_sitemap_xml, resolve_sitemap_base_url

async def generate_sitemap():
    await orm.create_pool(**configs.database)

    try:
        base_url = resolve_sitemap_base_url()
        sitemap = await build_current_sitemap_xml(base_url)
        output = Path(__file__).resolve().parents[1] / 'sitemap.xml'
        with open(output, "w+", encoding="utf-8") as f:
            f.writelines(sitemap)
    finally:
        await orm.destroy_pool()

if __name__ == "__main__":
    asyncio.run(generate_sitemap())
