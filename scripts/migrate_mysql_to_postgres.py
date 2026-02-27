#!/usr/bin/env python3
# _*_ coding: utf-8 _*_

import argparse
import asyncio
import json
import os
from pathlib import Path

import aiomysql
import asyncpg


TABLE_ORDER = [
    'users',
    'categories',
    'tags',
    'blogs',
    'comments',
    'comments_anonymous',
]

BOOLEAN_COLUMNS = {
    'users': {'admin'},
    'blogs': {'enabled'},
}


def _merge(base, override):
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_default_config():
    root = Path(__file__).resolve().parents[1]
    config_dir = root / 'www' / 'config'
    base_path = config_dir / 'config.json'
    user_path = config_dir / 'user.json'

    if not base_path.exists():
        return {}

    with base_path.open(encoding='utf-8') as f:
        config = json.load(f)

    if user_path.exists():
        with user_path.open(encoding='utf-8') as f:
            user = json.load(f)
        config = _merge(config, user)

    return config


def _build_parser(defaults):
    mysql_defaults = defaults.get('mysql_source', {})
    pg_defaults = defaults.get('database', {})

    parser = argparse.ArgumentParser(description='Migrate data from MySQL to PostgreSQL.')
    parser.add_argument('--mysql-host', default=os.getenv('MYSQL_HOST', mysql_defaults.get('host', '127.0.0.1')))
    parser.add_argument('--mysql-port', default=int(os.getenv('MYSQL_PORT', mysql_defaults.get('port', 3306))), type=int)
    parser.add_argument('--mysql-user', default=os.getenv('MYSQL_USER', mysql_defaults.get('user', 'root')))
    parser.add_argument('--mysql-password', default=os.getenv('MYSQL_PASSWORD', mysql_defaults.get('password', '')))
    parser.add_argument('--mysql-database', default=os.getenv('MYSQL_DATABASE', mysql_defaults.get('database', 'awesome_blog')))

    parser.add_argument('--pg-dsn', default=os.getenv('PG_DSN', pg_defaults.get('dsn')), required=False)
    parser.add_argument('--skip-truncate', action='store_true', help='Append data without truncating destination tables.')
    return parser


def _transform_value(table, column, value):
    if column in BOOLEAN_COLUMNS.get(table, set()):
        return bool(value)
    return value


def _build_insert_sql(table, columns):
    quoted_columns = ', '.join('"{}"'.format(column) for column in columns)
    placeholders = ', '.join('${}'.format(i) for i in range(1, len(columns) + 1))
    return 'insert into "{}" ({}) values ({})'.format(table, quoted_columns, placeholders)


async def _read_mysql_rows(mysql_conn, table):
    cursor = await mysql_conn.cursor(aiomysql.DictCursor)
    try:
        await cursor.execute('select * from `{}`'.format(table))
        return await cursor.fetchall()
    finally:
        await cursor.close()


async def _migrate_table(mysql_conn, pg_conn, table, skip_truncate):
    rows = await _read_mysql_rows(mysql_conn, table)
    mysql_count = len(rows)

    if not skip_truncate:
        await pg_conn.execute('truncate table "{}" restart identity cascade'.format(table))

    if rows:
        columns = list(rows[0].keys())
        sql = _build_insert_sql(table, columns)
        values = [
            tuple(_transform_value(table, column, row[column]) for column in columns)
            for row in rows
        ]
        await pg_conn.executemany(sql, values)

    pg_count = await pg_conn.fetchval('select count(*) from "{}"'.format(table))
    if pg_count != mysql_count:
        raise RuntimeError(
            'Row count mismatch for table {} (mysql={}, postgres={})'.format(table, mysql_count, pg_count)
        )

    print('Migrated table {:>18}: {}'.format(table, mysql_count))


async def _sync_tag_sequence(pg_conn):
    await pg_conn.execute(
        """
        select setval(
            pg_get_serial_sequence('tags', 'id'),
            coalesce((select max(id) from tags), 1),
            (select count(*) > 0 from tags)
        )
        """
    )


async def migrate(args):
    if not args.pg_dsn:
        raise ValueError('Missing --pg-dsn (or set PG_DSN / database.dsn in config).')

    mysql_conn = None
    pg_conn = None

    try:
        mysql_conn = await aiomysql.connect(
            host=args.mysql_host,
            port=args.mysql_port,
            user=args.mysql_user,
            password=args.mysql_password,
            db=args.mysql_database,
            autocommit=True,
            charset='utf8mb4',
        )
        pg_conn = await asyncpg.connect(args.pg_dsn)

        for table in TABLE_ORDER:
            await _migrate_table(mysql_conn, pg_conn, table, args.skip_truncate)
        await _sync_tag_sequence(pg_conn)
        print('Migration finished successfully.')
    finally:
        if mysql_conn is not None:
            mysql_conn.close()
            try:
                await mysql_conn.ensure_closed()
            except Exception:
                pass
        if pg_conn is not None:
            await pg_conn.close()


def main():
    defaults = _load_default_config()
    parser = _build_parser(defaults)
    args = parser.parse_args()
    asyncio.run(migrate(args))


if __name__ == '__main__':
    main()
