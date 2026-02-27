#!/usr/bin/env python
# _*_ coding: utf-8 _*_

from logger import logger
import asyncpg

__pool = None


def _build_dsn(**kw):
    dsn = kw.get('dsn')
    if dsn:
        return dsn

    user = kw.get('user')
    password = kw.get('password', '')
    host = kw.get('host', 'localhost')
    port = kw.get('port', 5432)
    database = kw.get('database')

    if user and database:
        return 'postgresql://{}:{}@{}:{}/{}'.format(user, password, host, port, database)

    raise ValueError('Missing database connection settings, provide dsn or host/user/password/database.')


def _replace_placeholders(sql):
    parts = sql.split('?')
    if len(parts) == 1:
        return sql

    query = [parts[0]]
    for i, part in enumerate(parts[1:], start=1):
        query.append('${}'.format(i))
        query.append(part)
    return ''.join(query)


def _parse_affected(command_tag):
    try:
        return int(command_tag.strip().split()[-1])
    except (ValueError, AttributeError, IndexError):
        return 0


async def create_pool(loop=None, **kw):
    logger.info('Create PostgreSQL connection pool...{}'.format(str(kw)))
    engine = str(kw.get('engine', 'postgresql')).lower()
    if engine not in ('postgres', 'postgresql'):
        raise ValueError('Unsupported database engine: {}. Only postgresql is supported.'.format(engine))
    global __pool
    __pool = await asyncpg.create_pool(
        dsn=_build_dsn(**kw),
        min_size=kw.get('minsize', 1),
        max_size=kw.get('maxsize', 10),
    )


async def destroy_pool():
    global __pool
    if __pool is not None:
        await __pool.close()
        __pool = None


async def destory_pool():
    await destroy_pool()


async def select(sql, args, size=None):
    logger.info('SQL:{}\tARGS:{}'.format(sql, args))
    global __pool
    query = _replace_placeholders(sql)
    async with __pool.acquire() as conn:
        if size == 1:
            row = await conn.fetchrow(query, *(args or ()))
            rs = [dict(row)] if row else []
        else:
            rows = await conn.fetch(query, *(args or ()))
            rs = [dict(row) for row in rows]
            if size:
                rs = rs[:size]
        logger.info('rows returned: {}'.format(len(rs)))
        return rs


async def execute(sql, args, autocommit=True, fetch_row=False):
    logger.info(sql)
    global __pool
    query = _replace_placeholders(sql)
    async with __pool.acquire() as conn:
        try:
            if autocommit:
                if fetch_row:
                    row = await conn.fetchrow(query, *(args or ()))
                    return (1 if row else 0), (dict(row) if row else None)
                command_tag = await conn.execute(query, *(args or ()))
                return _parse_affected(command_tag), None

            transaction = conn.transaction()
            await transaction.start()
            if fetch_row:
                row = await conn.fetchrow(query, *(args or ()))
                affected = 1 if row else 0
                value = dict(row) if row else None
            else:
                command_tag = await conn.execute(query, *(args or ()))
                affected = _parse_affected(command_tag)
                value = None
            if not autocommit:
                await transaction.commit()
            return affected, value
        except BaseException as e:
            if not autocommit:
                await transaction.rollback()
            raise


def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)


class Field(object):

    def __init__(self, name, colummn_type, primary_key, default):
        self.name = name
        self.column_type = colummn_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<{}, {}:{}>'.format(self.__class__.__name__, self.column_type, self.name)


class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)


class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)


class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)


class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)


class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)


class ModelMetaclass(type):

    def __new__(cls, name, bases, attrs):
        #
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)

        table_name = attrs.get('__table__', None) or name
        logger.info('found model : {} (table:{})'.format(name, table_name))

        # get all field and primary key
        mappings = dict()
        fields = []
        primary_key = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logger.info('   found mapping: {} ===> {}'.format(k, v))
                mappings[k] = v
                if v.primary_key:
                    if primary_key:
                        raise RuntimeError('Duplicate primary key for field: {}'.format(k))
                    primary_key = k
                else:
                    fields.append(k)

        if not primary_key:
            raise RuntimeError('Primary key not found')

        for k in mappings.keys():
            attrs.pop(k)

        def _column_name(key):
            return mappings.get(key).name or key

        escaped_fields = list(map(lambda f: '"{}"'.format(_column_name(f)), fields))
        primary_key_column = _column_name(primary_key)
        attrs['__mappings__'] = mappings
        attrs['__table__'] = table_name
        attrs['__primary_key__'] = primary_key
        attrs['__primary_key_column__'] = primary_key_column
        attrs['__fields__'] = fields

        attrs['__select__'] = 'select "{}", {} from "{}"'.format(primary_key_column, ', '.join(escaped_fields), table_name)
        attrs['__insert__'] = 'insert into "{}" ({}, "{}") values ({})'.format(
            table_name,
            ', '.join(escaped_fields),
            primary_key_column,
            create_args_string(len(escaped_fields) + 1),
        )
        attrs['__insert_returning__'] = '{} returning "{}"'.format(attrs['__insert__'], primary_key_column)
        attrs['__insert_without_pk__'] = 'insert into "{}" ({}) values ({})'.format(
            table_name,
            ', '.join(escaped_fields),
            create_args_string(len(escaped_fields)),
        )
        attrs['__insert_without_pk_returning__'] = '{} returning "{}"'.format(
            attrs['__insert_without_pk__'],
            primary_key_column,
        )
        attrs['__update__'] = 'update "{}" set {} where "{}" = ?'.format(table_name, ', '.join(
            map(lambda f: '"{}"=?'.format(_column_name(f)), fields)), primary_key_column)
        attrs['__delete__'] = 'delete from "{}" where "{}"=?'.format(table_name, primary_key_column)

        return type.__new__(cls, name, bases, attrs)


class Model(dict, metaclass=ModelMetaclass):

    def __init__(self, **kwargs):
        super(Model, self).__init__(**kwargs)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r'"Model" object has no attribute "{}"'.format(key))

    def __setattr__(self, key, value):
        self[key] = value

    def get_value(self, key):
        return getattr(self, key, None)

    def get_value_or_default(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logger.info('using default value for {}: {}'.format(key, str(value)))
                setattr(self, key, value)
        return value

    @classmethod
    async def find(cls, pk):
        ''' find object by primary key '''
        rs = await select('{} where "{}"=?'.format(cls.__select__, cls.__primary_key_column__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    @classmethod
    async def find_all(cls, where=None, args=None, **kwargs):
        ''' find objects by where clause. '''

        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []

        order_by = kwargs.get('order_by', None)

        if order_by:
            sql.append('order by')
            sql.append(order_by)

        limit = kwargs.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                offset, row_count = limit
                sql.append('? offset ?')
                args.extend([row_count, offset])
            else:
                raise ValueError('Invalid limit value: {}'.format(str(limit)))

        rs = await select(' '.join(sql), args)

        return [cls(**r) for r in rs]

    @classmethod
    async def find_number(cls, select_field, where=None, args=None):
        ''' find number by select and where. '''
        sql = ['select {} as _num_ from "{}"'.format(select_field, cls.__table__)]

        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']

    async def save(self):
        field_values = list(map(self.get_value_or_default, self.__fields__))
        primary_key_value = self.get_value_or_default(self.__primary_key__)
        if primary_key_value is None:
            rows, row = await execute(self.__insert_without_pk_returning__, field_values, fetch_row=True)
        else:
            args = list(field_values)
            args.append(primary_key_value)
            rows, row = await execute(self.__insert_returning__, args, fetch_row=True)
        if rows != 1:
            logger.warning('Failed to insert record: affected rows: {}'.format(rows))
        primary_key = self.__primary_key_column__
        inserted_id = None if row is None else row.get(primary_key)
        if inserted_id is not None:
            setattr(self, self.__primary_key__, inserted_id)
        return rows, inserted_id

    async def update(self):
        args = list(map(self.get_value, self.__fields__))
        args.append(self.get_value(self.__primary_key__))
        rows, _ = await execute(self.__update__, args)
        if rows != 1:
            logger.warning('Failed to update by primary key: affected rows: {}'.format(rows))

    async def remove(self):
        args = [self.get_value(self.__primary_key__)]
        rows, _ = await execute(self.__delete__, args)
        if rows != 1:
            logger.warning('Failed to remove by primary key: affected rows: {}'.format(rows))
