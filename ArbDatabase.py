import asyncio
import os
import time
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import pprint
import random
import sqlite3
import datetime
from queue import Queue
import threading
import logging
from typing import Any, Dict, List, Tuple, Union
import json
from tenacity import retry, wait_fixed, stop_after_attempt
from contextlib import asynccontextmanager, contextmanager


class Logger:
    def __init__(self, log_file='Logs/Arbiter.log', max_size=1024 * 1024 * 5):  # 5 MB
        self.log_file = log_file
        self.max_size = max_size
        # Создаем директорию, если она не существует
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

    def _rotate_log(self):
        """Проверяем размер файла и переименовываем, если он превышает максимальный размер."""
        if os.path.exists(self.log_file) and os.path.getsize(self.log_file) >= self.max_size:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            os.rename(self.log_file, f"{self.log_file}.{timestamp}")

    def _log(self, level, message):
        """Записываем сообщение в лог файл с форматом, подходящим для Ideolog."""
        self._rotate_log()
        with open(self.log_file, 'a', encoding='utf-8') as f:
            log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{level}] {message}"
            f.write(log_entry + '\n')

    def debug(self, message):
        """Записываем сообщение уровня DEBUG."""
        self._log('DEBUG', message)

    def info(self, message):
        """Записываем сообщение уровня INFO."""
        self._log('INFO', message)

    def warning(self, message):
        """Записываем сообщение уровня WARNING."""
        self._log('WARNING', message)

    def error(self, message):
        """Записываем сообщение уровня ERROR."""
        self._log('ERROR', message)

    def critical(self, message):
        """Записываем сообщение уровня CRITICAL."""
        self._log('CRITICAL', message)


class ConnectionPool:
    def __init__(self, max_connections: int, db_name='Arbiter.db', timeout=10):
        self.max_connections = max_connections
        self.db_name = db_name
        self.timeout = timeout
        self.connection_queue = Queue(max_connections)

        for _ in range(max_connections):
            connection = sqlite3.connect(db_name, timeout=self.timeout, check_same_thread=False)
            self.connection_queue.put(connection)

    def get_connection(self):
        if not self.connection_queue.empty():
            return self.connection_queue.get()
        else:
            raise Exception("Нет доступных подключений!")

    def release_connection(self, conn):
        self.connection_queue.put(conn)

    def close_all_connections(self):
        while not self.connection_queue.empty():
            conn = self.connection_queue.get()
            conn.close()


DEFAULT_LOGGER = Logger()
DEFAULT_POOL = ConnectionPool(1000)


class DataManager:
    def __init__(self, connection_pool: ConnectionPool = DEFAULT_POOL, logger: Logger = DEFAULT_LOGGER, idle_timeout=10):
        self.logger = logger or Logger()
        self.connection_pool = connection_pool
        self.connection = None
        self.cursor = None
        self.transaction_started = False
        self.auto_commit = True
        self.idle_timeout = idle_timeout
        self.idle_timer = None

    def open_connection(self):
        """Открываем соединение, если его нет"""
        if not self.connection:
            self.connection = self.connection_pool.get_connection()
            self.cursor = self.connection.cursor()
            self.logger.info(f"Соединение с базой данных открыто")
            self._cancel_idle_timer()  # Отменяем таймер закрытия, если он был установлен

    def close_connection(self):
        """Закрываем соединение и освобождаем ресурсы"""
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.connection:
            self.connection_pool.release_connection(self.connection)
            self.connection = None
            self.logger.info("Соединение с базой данных закрыто.")

    def reset_if_needed(self):
        """Проверяем, нужно ли восстановить соединение"""
        if self.connection is None or not self.is_connection_open():
            self.logger.info("Соединение закрыто. Переподключение к базе данных")
            self.reset_connection()

    def _start_idle_timer(self):
        """Запускаем таймер для автоматического закрытия соединения после простоя"""
        # self.idle_timer = threading.Timer(self.idle_timeout, self.close_connection)
        # self.idle_timer.start()
        pass

    def _cancel_idle_timer(self):
        """Отменяем таймер простоя, если выполняются запросы"""
        # if self.idle_timer:
        #     self.idle_timer.cancel()
        #     self.idle_timer = None
        pass

    @contextmanager
    def managed_connection(self):
        """Контекстный менеджер для автоматического управления соединениями"""
        try:
            self.reset_if_needed()
            yield self
        finally:
            if not self.transaction_started:
                self._start_idle_timer()  # Запускаем таймер после завершения запроса

    def reset_connection(self):
        """Сбрасывает текущее соединение и переподключается."""
        self.logger.warning("Переподключение из-за закрытия базы данных или других проблем")
        self.close_connection()
        self.open_connection()

    def is_connection_open(self):
        """Проверяет, открыто ли соединение к базе данных."""
        try:
            self.connection.execute("SELECT 1")  # Простой запрос для проверки
            return True
        except sqlite3.ProgrammingError:  # Если соединение закрыто, будет выброшено исключение
            return False

    @retry(wait=wait_fixed(2), stop=stop_after_attempt(5), reraise=True)
    def execute(self, prompt, commit=True) -> None:
        self.reset_if_needed()
        try:
            self.cursor.execute(prompt)
            if commit:
                self.connection.commit()
                self.logger.info(f"Запрос успешно выполнен: {prompt}")
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                self.logger.warning(f"База данных закрыта. Повторная попытка: {prompt}")
                time.sleep(1)
                self.reset_connection()
                raise e  # попытка снова
            else:
                self.logger.critical(f"Ошибка при работе с базой данных: {e}")
                raise

    def select(self, table_name, columns='*', filter=None) -> list[tuple]:
        with self.managed_connection():
            query = f"SELECT {columns} FROM {table_name}"
            if filter:
                query += f" WHERE {filter}"
            self.execute(query, commit=False)
            result = self.cursor.fetchall()
            return result

    def selectOne(self, table_name, columns='*', filter=None) -> tuple:
        with self.managed_connection():
            query = f"SELECT {columns} FROM {table_name}"
            if filter:
                query += f" WHERE {filter}"
            self.execute(query, commit=False)
            result = self.cursor.fetchone()
            return result

    def insert(self, table_name: str, columns_values: dict) -> None:
        with self.managed_connection():
            placeholders = ', '.join(['?'] * len(columns_values))

            column_names = ', '.join(f'"{col}"' for col in columns_values.keys())

            query = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
            values = tuple(columns_values.values())

            self.cursor.execute(query, values)
            self.connection.commit()

    def update(self, table_name: str, columns_values: dict, filter: str = None) -> None:
        with self.managed_connection():
            set_values = []
            for col, val in columns_values.items():
                if val is None:
                    set_values.append(f"{col} = NULL")
                elif isinstance(val, str):
                    set_values.append(f"{col} = '{val}'")
                elif isinstance(val, (int, float)):
                    set_values.append(f"{col} = {val}")

            set_values_str = ', '.join(set_values)

            query = f"UPDATE {table_name} SET {set_values_str}"

            if filter:
                query += f" WHERE {filter}"

            print(query)

            self.cursor.execute(query)
            self.connection.commit()

    def delete(self, table_name: str, filter: str = None) -> None:
        with self.managed_connection():
            query = f"DELETE FROM {table_name}"
            if filter:
                query += f" WHERE {filter}"
            self.execute(query)

    def maxValue(self, table_name: str, parameter: str, filter: str = None) -> int | float:
        with self.managed_connection():
            if filter:
                query = f'SELECT MAX({parameter}) FROM {table_name} WHERE {filter}'
            else:
                query = f'SELECT MAX({parameter}) FROM {table_name}'

            c_output = self.cursor.execute(query).fetchone()[0]
            self.connection.commit()

            if c_output is None:
                return -1
            else:
                return c_output

    def minValue(self, table_name: str, parameter: str, filter: str = None) -> int | float:
        with self.managed_connection():
            if filter:
                query = f'SELECT MIN({parameter}) FROM {table_name} WHERE {filter}'
            else:
                query = f'SELECT MIN({parameter}) FROM {table_name}'

            c_output = self.cursor.execute(query).fetchone()[0]
            self.connection.commit()
            return c_output

    def avgValue(self, table_name: str, parameter: str, filter: str = None) -> float:
        with self.managed_connection():
            if filter:
                query = f'SELECT AVG({parameter}) FROM {table_name} WHERE {filter}'
            else:
                query = f'SELECT AVG({parameter}) FROM {table_name}'

            c_output = self.cursor.execute(query).fetchone()[0]
            self.connection.commit()
            return c_output

    def get_count(self, table_name: str, parameter: str, filter: str = None) -> int | float:
        with self.managed_connection():
            if filter:
                query = f'SELECT COUNT({parameter}) FROM {table_name} WHERE {filter}'
            else:
                query = f'SELECT COUNT({parameter}) FROM {table_name}'

            c_output = self.cursor.execute(query).fetchone()[0]
            self.connection.commit()
            return c_output

    def check(self, table_name: str, filter: str) -> bool:
        with self.managed_connection():
            query = f"SELECT COUNT(*) FROM {table_name} WHERE {filter}"

            self.cursor.execute(query)
            result = self.cursor.fetchone()[0]

            return result > 0 if result else None

    def select_dict(self, table_name: str, columns='*', filter=None) -> list[dict]:
        with self.managed_connection():
            query = f"SELECT {columns} FROM {table_name}"
            if filter:
                query += f" WHERE {filter}"

            self.cursor.execute(query)
            result = self.cursor.fetchall()

            columns = [desc[0] for desc in self.cursor.description]

            typed_result = []

            for row in result:
                typed_row = {}
                for col, val in zip(columns, row):
                    typed_row[col] = val
                typed_result.append(typed_row)

            return typed_result

    def get_all_tables(self) -> list:
        with self.managed_connection():
            # Получение списка всех таблиц из базы данных
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in self.cursor.fetchall()]

            return tables

    def get_tables_with_prefix(self, prefix:str) -> list:
        with self.managed_connection():
            c_tables = self.get_all_tables()
            total = [table for table in c_tables if prefix in table]
            return total

    def delete_from_all_tables(self, filters: dict, tables:list=None) -> None:
        with self.managed_connection():
            if not tables:
                tables = self.get_all_tables()

            for table_name in tables:
                # Generating filter conditions for deleting records in a specific table
                where_clauses = []
                for column, value in filters.items():
                    # Check if the value is numeric
                    if str(value).replace(".", "", 1).isdigit():  # Check if the value is numeric (int or float)
                        value_formatted = int(value) if value.is_integer() else float(value)
                    else:
                        value_formatted = f"'{value}'"

                    where_clauses.append(f"{column} = {value_formatted}")

                where_clause = ' AND '.join(where_clauses)

                # Construct and execute the delete query
                delete_query = f"DELETE FROM {table_name}"
                if where_clause:
                    delete_query += f" WHERE {where_clause}"

                self.cursor.execute(delete_query)
                self.connection.commit()

    def get_all_columns(self, table_name:str) -> list[str]:
        with self.managed_connection():
            self.cursor.execute(f'SELECT * FROM {table_name} LIMIT 0')
            column_names = [desc[0] for desc in self.cursor.description]
            return column_names

    def get_columns_desc(self, table_name:str):
        with self.managed_connection():
            self.cursor.execute(f"PRAGMA table_info('{table_name}')")
            column_desc = self.cursor.fetchall()
            print(column_desc)
            return column_desc

    def get_columns_types(self, table_name:str) -> dict[str]:
        with self.managed_connection():
            column_types = {}
            self.cursor.execute(f"SELECT name, type FROM pragma_table_info('{table_name}')")
            for row in self.cursor.fetchall():
                column_types[row[0]] = row[1]
            return column_types

    def bulk_insert(self, table_name: str, columns_values_list: list[dict]):
        with self.managed_connection():
            if not columns_values_list:
                return

            columns_str = ', '.join(columns_values_list[0].keys())
            placeholders = ', '.join(['?'] * len(columns_values_list[0]))
            values_list = [tuple(item.values()) for item in columns_values_list]

            query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"

            self.cursor.executemany(query, values_list)
            self.connection.commit()

    def raw_execute(self, query: str, params: tuple = None, fetch: str = 'all') -> list | tuple:
        """Выполнение произвольного SQL-запроса."""
        with self.managed_connection():
            self.cursor.execute(query, params or ())
            if fetch == 'all':
                result = self.cursor.fetchall()
            elif fetch == 'one':
                result = self.cursor.fetchone()
            else:
                result = None
            self.connection.commit()
            return result

    def selector(self, table: str, columns: list[str] | str = None, key: Union[str, 'EID'] = None):
        with self.managed_connection():
            if isinstance(columns, str):
                columns_list = columns
            elif isinstance(columns, list):
                columns_list = ', '.join(columns)
            else:
                columns_list = '*'

            query = f"SELECT {columns_list} FROM {table}"
            if key:
                query += f" WHERE {str(key)}"

            self.execute(query)
            result = self.cursor.fetchall()

            columns = [desc[0] for desc in self.cursor.description]

            typed_result = []

            for row in result:
                typed_row = {}
                for col, val in zip(columns, row):
                    typed_row[col] = val
                typed_result.append(typed_row)

            return typed_result

    def updator(self, table: str, key: Union[str, 'EID'] = None, **kwargs):
        set_values = []
        for col, val in kwargs.items():
            if val is None:
                set_values.append(f"{col} = NULL")
            elif isinstance(val, str):
                set_values.append(f"{col} = '{val}'")
            elif isinstance(val, (int, float)):
                set_values.append(f"{col} = {val}")

        set_values_str = ', '.join(set_values)

        query = f"UPDATE {table} SET {set_values_str}"

        if key:
            query += f" WHERE {str(key)}"

        print(query)

        self.execute(query)
        self.connection.commit()

    def deleter(self, table: str, key: Union[str, 'EID'] = None):
        query = f"DELETE FROM {table}"
        if filter:
            query += f" WHERE {str(key)}"
        self.execute(query)

    def inserter(self, table: str, **kwargs):
        placeholders = ', '.join(kwargs.values())

        column_names = ', '.join(f'"{col}"' for col in kwargs.keys())

        query = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"

        self.cursor.execute(query)
        self.connection.commit()


DEFAULT_MANAGER = DataManager(idle_timeout=15)


class DataModel:
    def __init__(self, table_name: str, key_filter: str, **kwargs):
        self._table_name = table_name
        self._key_filter = key_filter
        self.data_manager = kwargs.get('data_manager', DataManager())
        self._data = None
        self.refresh_data()

    def refresh_data(self):
        """Refresh the data from the database."""

        columns = self.data_manager.get_all_columns(self._table_name)
        if self.data_manager.check(self._table_name, self._key_filter):
            self._data = self.data_manager.select_dict(self._table_name, filter=self._key_filter)[0]
        else:
            self._data = {col: None for col in columns}

    def update_record(self, data: Dict[str, Any]):
        """Update the record in the database and the local cache."""

        self.data_manager.update(self._table_name, data, self._key_filter)
        self.refresh_data()

    def delete_record(self):
        """Delete the record from the database."""
        self.data_manager.delete(self._table_name, self._key_filter)
        self._data = {col: None for col in self._data.keys()}

    def get(self, key: str, default_value=None):
        """Get the value of a specific key with an optional default value."""
        return self._data.get(key, default_value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the data model to a dictionary."""
        return {
            'data': self._data,
            'data_manager': self.data_manager
        }

    @property
    def data(self) -> Dict[str, Any]:
        """Property to access the data dictionary."""
        return self._data

    @property
    def table_name(self) -> str:
        """Property to access the table name."""
        return self._table_name

    @property
    def key_filter(self) -> str:
        """Property to access the key filter."""
        return self._key_filter


class DataObject:
    def __init__(self, table: str, key: 'EID', data_manager: DataManager = None):
        self.__table_name__ = table
        self.__key__ = key
        self.data_manager = data_manager or DataManager()

    def field(self, column: str, default: Any = None) -> 'Link':
        return Link(self.__table_name__, column, self.__key__, default)

    def delete_record(self):
        """Delete the record from the database."""
        self.data_manager.deleter(self.__table_name__, self.__key__)


class RecordModel:
    def __init__(self, table_name: str, **kwargs):
        self._table_name = table_name
        self.data_manager = kwargs.get('data_manager', DataManager())
        self._data = None
        self.refresh_columns()

    def refresh_columns(self):
        """Get the table structure from the database."""
        self._columns = self.data_manager.get_all_columns(self._table_name)
        self._data = {col: None for col in self._columns}

    def create_record(self):
        """Create a new record in the database."""
        self.data_manager.insert(self._table_name, self._data)

    def update_record(self, data: Dict[str, Any], key_filter: str):
        """Update the record in the database."""
        self.data_manager.update(self._table_name, data, key_filter)
        self.refresh_columns()

    def get(self, key: str, default_value=None):
        """Get the value of a specific key with an optional default value."""
        return self._data.get(key, default_value)

    def set(self, key: str, value):
        """Set the value of a specific key."""
        if key in self._columns:
            self._data[key] = value
        else:
            raise ValueError(f"Column '{key}' does not exist in the table '{self._table_name}'.")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the data model to a dictionary."""
        return {
            'data': self._data,
            'data_manager': self.data_manager
        }

    @property
    def data(self) -> Dict[str, Any]:
        """Property to access the data dictionary."""
        return self._data

    @property
    def table_name(self) -> str:
        """Property to access the table name."""
        return self._table_name

    @property
    def columns(self) -> List[str]:
        """Property to access the columns."""
        return self._columns\


class DataDict:
    def __init__(self, table_name:str, key_filter:str=None, **kwargs):
        self._data_manager = kwargs.get('data_manager', DataManager())
        self._table_name = table_name
        self._key_filter = key_filter

        self._data = self._get_record()

    def _get_record(self) -> dict:
        if self._data_manager.check(self._table_name, self._key_filter):
            return self._data_manager.select_dict(self._table_name, filter=self._key_filter)[0]
        else:
            return {}

    def get(self, key: str, default_value=None) -> Any:
        value = self._data.get(key, default_value) if self._data.get(key) is not None else default_value if default_value else None
        return value

    def to_dict(self) -> dict:
        return self._data

    def __repr__(self):
        return f"DataDict({self._table_name}, {self._key_filter})\n{self._data}"

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        return self._data[key]

    def __delitem__(self, key):
        del self._data[key]

    def __contains__(self, key):
        return key in self._data

    def columns(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()


class DataList:
    def __init__(self, table_name: str, key_filter: str = None, **kwargs):
        self._data_manager = kwargs.get('data_manager', DataManager())
        self._table_name = table_name
        self._key_filter = key_filter
        self._data = self._get_records()

    def _get_records(self) -> list:
        if self._key_filter:
            return self._data_manager.select_dict(self._table_name, filter=self._key_filter)
        else:
            return self._data_manager.select_dict(self._table_name)

    def get(self, index: int) -> dict:
        return self._data[index] if index < len(self._data) else None

    def to_dict(self) -> list:
        return self._data

    def filter(self, field: str, value: Any) -> 'DataList':
        filtered_data = [record for record in self._data if record.get(field) == value]
        return DataList.from_list(filtered_data, self._table_name, self._data_manager)

    def sort(self, field: str, reverse: bool = False) -> None:
        self._data.sort(key=lambda record: record.get(field), reverse=reverse)

    def aggregate(self, func, field: str) -> Any:
        values = [record.get(field) for record in self._data if field in record]
        return func(values)

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, index):
        return self._data[index]

    def __delitem__(self, index):
        del self._data[index]

    def __contains__(self, item):
        return item in self._data

    def columns(self):
        return self._data[0].keys() if self._data else []

    def values(self):
        return [record.values() for record in self._data]

    def items(self):
        return [record.items() for record in self._data]

    @classmethod
    def from_list(cls, data_list: list[dict], table_name: str, data_manager: DataManager):
        instance = cls(table_name, data_manager=data_manager)
        instance._data = data_list
        return instance

    def __repr__(self):
        return f"DataList({self._table_name}, {self._key_filter})\n{self._data}"


class DataInsert:
    def __init__(self, data:dict = None, **kwargs):
        self._data = data if data else {}
        self._data_manager = kwargs.get('data_manager', DataManager())

    def set(self, key: str, value: str | int | float | None):
        self._data[key] = value

    def insert_in_database(self, table_name: str):
        try:
            self._data_manager.insert(table_name, self._data)
        except Exception as e:
            print(f"Error inserting record in {table_name}: {e}")

    def update_in_database(self, table_name: str, key_filter=None):
        try:
            self._data_manager.update(table_name, self._data, key_filter)
        except Exception as e:
            print(f"Error updating record in {table_name}: {e}")

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f"DataInsert({self._data})"

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def __getitem__(self, key):
        return self._data[key]

    def __delitem__(self, key):
        del self._data[key]

    def __contains__(self, key):
        return key in self._data


class DataTable:
    def __init__(self, table_name: str, data_manager: DataManager = None):
        self._table_name = table_name
        self._data_manager = data_manager if data_manager else DataManager()
        self._columns = self._get_columns()

    def _get_columns(self):
        if self._table_name not in self._data_manager.get_all_tables():
            return []
        columns = self._data_manager.get_all_columns(self._table_name)
        return columns

    def get_record(self, filter: str):
        data = self._data_manager.select_dict(self._table_name, filter=filter)
        if not data:
            return {}

        return data[0]

    def get_value(self, filter:str, column:str):
        data = self.get_record(filter)
        if not data:
            return None

        return data.get(column)

    def get_all_records(self, filter:str=None):
        data = self._data_manager.select_dict(self._table_name, filter=filter)
        return data

    def sort_records(self, field: str, reverse: bool = False):
        pass

    def aggregate_records(self, field: str, aggregate_func: str):
        pass

    def __repr__(self):
        return f"TABLE.{self._table_name}({', '.join(self._columns)})"



class Table:
    def __init__(self, table_name:str, data_manager:DataManager = None):
        self._table_name = table_name
        self._data_manager = data_manager if data_manager else DataManager()
        self._columns = self._data_manager.get_all_columns(self._table_name)


class Link:
    def __init__(self, table: str, column: str, key: Union[str, 'EID'], default: Any = None):
        self.table = table
        self.column = column
        self.key = key
        self._value = None
        self._default_value = default
        self._is_loaded = False

    def load(self, data_manager: DataManager):
        """Загружает список данных из базы, если они еще не загружены."""
        if self._is_loaded:
            return self._value

        data = data_manager.selector(self.table, [self.column], str(self.key))

        if not data:
            self._value = self._default_value
        else:
            self._value = data[0].get(self.column)

        self._is_loaded = True
        return self._value

    def set_default(self, data_manager: DataManager):
        if self._value != self._default_value:
            self.save(data_manager, self._default_value)
            self._value = self._default_value

    def __get__(self, instance, owner):
        """Автоматически вызывается при доступе к атрибуту."""
        if instance is None:
            return self
        return self.load(instance.data_manager)

    def __set__(self, instance, value):
        """Сохраняем новое значение и автоматически синхронизируем его с базой данных."""
        if value != self._value:
            self.save(instance.data_manager, value)

    def save(self, data_manager: DataManager, value: Union[str, int, float]):
        """Сохраняет новое значение в базу данных."""
        data_manager.updator(self.table, str(self.key), **{self.column: value})
        self._value = value

    def invalidate_cache(self):
        """Сбрасывает кеш для загрузки новых данных при следующем доступе."""
        self._is_loaded = False
        self._value = None

    def set_value(self, value: Union[str, int, float]):
        """Устанавливает новое значение и автоматически синхронизируем его с базой данных."""
        self._value = value

    def __repr__(self):
        return f'{self.table}.{self.column} = {self._value if self._is_loaded else "[NOT LOADED]"}'


class EID:
    def __init__(self, **kwargs):
        self._key_data = kwargs

    def _format_value(self, key: str, value: Any):
        if value is None:
            return f'{key} is NULL'
        elif isinstance(value, str):
            return f'{key} = "{value}"'
        elif isinstance(value, (int, float)):
            return f'{key} = {value}'
        else:
            raise ValueError('Значение ключа может быть в форматах None (NULL), str (TEXT), int (INTEGER), float (REAL)')

    def _process_key(self):
        """Преобразует ключевые значения в SQL формат."""
        conditions = []
        for key, value in self._key_data.items():
            conditions.append(self._format_value(key, value))

        return f' AND '.join(conditions)

    def __repr__(self):
        return f'IDKey[ {self._process_key()} ]'

    def __str__(self):
        return self._process_key()

    def __get__(self, instance, owner):
        """Автоматически вызывается при доступе к атрибуту."""
        return self.__str__()

    def __set__(self, instance, values):
        """Сохраняем новое значение и обновляем базу данных."""
        if not isinstance(values, dict):
            raise ValueError("ID-ключ изменяется только словарём!")
        self._key_data = values


#
#
# class Base:
#     @classmethod
#     def from_dict(cls, data: dict):
#         instance = cls()
#         for key, value in data.items():
#             setattr(instance, key, value)
#
#         return instance
#
#     def to_dict(self):
#         return {key: getattr(self, key) for key in vars(self) if not key.startswith('_')}
#
#
# class Record(Base):
#     def __init__(self, **kwargs):
#         self.table_name = kwargs.pop('table')
#         self.data = kwargs
#         for key, value in kwargs.items():
#             setattr(self, key, value)
#
#     def save(self, data_manager: DataManager):
#         try:
#             data_manager.insert(self.table_name, self.data)
#         except Exception as e:
#             print(f"Error saving record: {e}")
#
#     def update(self, data_manager: DataManager, filter=None):
#         try:
#             self.data = {k: v for k, v in self.__dict__.items() if k != 'table_name' and k != 'data'}
#             data_manager.update(self.table_name, self.data, filter)
#         except Exception as e:
#             print(f"Error updating record: {e}")
#
#     def delete(self, data_manager: DataManager, filter=None):
#         try:
#             if filter is None:
#                 self.data = {k: v for k, v in self.__dict__.items() if k != 'table_name' and k != 'data'}
#                 filter = " AND ".join(f"{key} = '{value}'" for key, value in self.data.items())
#             data_manager.delete(self.table_name, filter)
#         except Exception as e:
#             print(f"Error deleting record: {e}")
#
#     @classmethod
#     def fetch_if_exists(cls, table_name: str, filter: str, data_manager: DataManager = None):
#         data_manager = data_manager if data_manager is not None else DataManager()
#
#         record_data = data_manager.select_dict(table_name, filter=filter)
#         if record_data:
#             return cls(table=table_name, **record_data[0])
#         else:
#             columns = data_manager.get_all_columns(table_name)
#             data = {column: None for column in columns}
#             return cls(table=table_name, **data)
#
#     @classmethod
#     def fetch_all(cls, table_name: str, filter: str, data_manager: DataManager = None):
#         data_manager = data_manager if data_manager is not None else DataManager()
#
#         records_data = data_manager.select_dict(table_name, filter=filter)
#         if records_data:
#             return [cls(table=table_name, **record_data) for record_data in records_data]
#         else:
#             columns = data_manager.get_all_columns(table_name)
#             data = {column: None for column in columns}
#             return [cls(table=table_name, **data)]
#
#     def __repr__(self):
#         return f'Record.{self.table_name}(columns={list(self.__dict__.keys())})'
#
#
# class TableRecord:
#     def __init__(self, table_name: str, filter: Optional[str] = None, data_manager: Optional[DataManager] = None):
#         self.table_name = table_name
#         self.data_manager = data_manager if data_manager is not None else DataManager()
#         self.filter = filter
#         self._load_record()
#
#     def _load_record(self):
#         record_data = self.data_manager.select_dict(self.table_name, filter=self.filter)
#         columns = self.data_manager.get_all_columns(self.table_name)
#         if record_data:
#             for key, value in record_data[0].items():
#                 setattr(self, key, value)
#         else:
#             for column in columns:
#                 setattr(self, column, None)
#
#     def __repr__(self):
#         return f'TableRecord(table_name={self.table_name}, filter={self.filter})'
#
#
# class Table:
#     def __init__(self, table_name, **kwargs):
#         self.table_name = table_name
#         self.data_manager = kwargs.get('data_manager', DataManager())
#
#     def get_all_records(self, filter=None):
#         pass
#
#
# @dataclass()
# class Column:
#     table: str
#     column: str
#     value: Any
#     filter: str = None
#
#     def update(self, value: Any, data_manager: DataManager = None):
#         db = data_manager if data_manager is not None else DataManager()
#         try:
#             db.update(self.table, {self.column: value}, filter=self.filter)
#             self.value = value
#             print(f"Updated {self.table}.{self.column} to {value} with filter: {self.filter}")
#         except Exception as e:
#             print(f"Error updating {self.table}.{self.column} to {value}: {e}")
#             raise
#
#     def get_value(self, data_manager: DataManager = None) -> Any:
#         db = data_manager if data_manager is not None else DataManager()
#         try:
#             result = db.select(self.table, columns=self.column, filter=self.filter)
#             if result:
#                 self.value = result[0][0]
#                 print(f"Fetched value {self.value} for {self.table}.{self.column} with filter: {self.filter}")
#                 return self.value
#             else:
#                 print(f"No value found for {self.table}.{self.column} with filter: {self.filter}")
#                 return None
#         except Exception as e:
#             print(f"Error fetching value for {self.table}.{self.column}: {e}")
#             raise
#
#     def validate_value(self) -> bool:
#         if isinstance(self.value, (int, float, str, type(None))):
#             return True
#         else:
#             raise ValueError(f"Invalid value type: {type(self.value)} for {self.table}.{self.column}")
#
#     @classmethod
#     def get_value_from_table(cls, table: str, column:str, filter: str = None, data_manager: DataManager = None) -> Any:
#         db = data_manager if data_manager is not None else DataManager()
#         try:
#             result = db.select_dict(table, filter=filter)
#             if result:
#                 return cls(table=table, column=column, value=result[0][column], filter=filter)
#             else:
#                 print(f"No value found for {table}.{column} with filter: {filter}")
#                 return None
#         except Exception as e:
#             print(f"Error fetching value for {table}.{column}: {e}")
#             raise
#
#     def __repr__(self):
#         return f'{self.column}: {self.value}'
#
#
# @dataclass
# class Row:
#     table: str
#     columns: dict[str, Column]
#     filter: str = None
#
#     @classmethod
#     def load_row(cls, table: str, filter: str = None, data_manager: DataManager = None):
#         data_manager = data_manager if data_manager is not None else DataManager()
#         result = data_manager.select_dict(table, filter=filter)
#
#         if not result:
#             raise ValueError(f"No row found in {table} with filter: {filter}")
#
#         columns = {}
#         for col_name, value in result[0].items():
#             columns[col_name] = Column(table=table, column=col_name, value=value, filter=filter)
#
#         return cls(table=table, columns=columns, filter=filter)
#
#     def update_column(self, column_name: str, value: Any, data_manager: DataManager = None):
#         if column_name in self.columns:
#             self.columns[column_name].update(value, data_manager=data_manager if data_manager is not None else DataManager())
#         else:
#             raise ValueError(f"Column {column_name} does not exist in row of table {self.table}")
#
#     def get_column_value(self, column_name: str, data_manager: DataManager = None) -> Any:
#         if column_name in self.columns:
#             return self.columns[column_name].get_value(data_manager=data_manager if data_manager is not None else DataManager())
#         else:
#             raise ValueError(f"Column {column_name} does not exist in row of table {self.table}")
#
#     def to_dict(self) -> dict[str, Any]:
#         return {col_name: col.value for col_name, col in self.columns.items()}
#
#     def update_row(self, new_values: dict[str, Any]):
#         for col_name, value in new_values.items():
#             self.update_column(col_name, value)
#
#     def row_to_record(self, data_manager: DataManager = None) -> Record:
#         return Record.fetch_if_exists(self.table, self.filter, data_manager=data_manager if data_manager is not None else DataManager())
#
#     def __repr__(self):
#         return f'{self.table}(columns={list(self.columns.values())})'
#
#
# @dataclass
# class Table:
#     name: str
#     rows: List[Row] = field(default_factory=list)
#
#     @classmethod
#     def get_filtered_table(cls, name: str, filter: Optional[str] = None, data_manager: Optional[DataManager] = None):
#         data_manager = data_manager if data_manager is not None else DataManager()
#         table = cls(name=name)
#         table.load_all_rows(filter=filter, data_manager=data_manager)
#         return table
#
#     @classmethod
#     def get_table(cls, name: str, data_manager: Optional[DataManager] = None):
#         data_manager = data_manager if data_manager is not None else DataManager()
#         table = cls(name=name)
#         table.load_all_rows(data_manager=data_manager)
#         return table
#
#     def load_all_rows(self, filter: Optional[str] = None, data_manager: Optional[DataManager] = None):
#         data_manager = data_manager if data_manager is not None else DataManager()
#         rows_data = data_manager.select_dict(self.name, filter=filter)
#
#         self.rows = [Row(table=self.name,
#                          columns={col: Column(table=self.name, column=col, value=val) for col, val in row.items()})
#                      for row in rows_data]
#
#     def insert_row(self, row_data: Dict[str, Any], data_manager: Optional[DataManager] = None):
#         data_manager = data_manager if data_manager is not None else DataManager()
#         data_manager.insert(self.name, row_data)
#         new_row = Row(table=self.name,
#                       columns={col: Column(table=self.name, column=col, value=val) for col, val in row_data.items()})
#         self.rows.append(new_row)
#
#     def delete_row(self, filter: str, data_manager: Optional[DataManager] = None):
#         data_manager = data_manager if data_manager is not None else DataManager()
#         data_manager.delete(self.name, filter)
#         self.rows = [row for row in self.rows if not (row.filter == filter)]
#
#     def update_row(self, filter: str, updated_values: Dict[str, Any], data_manager: Optional[DataManager] = None):
#         data_manager = data_manager if data_manager is not None else DataManager()
#         data_manager.update(self.name, updated_values, filter)
#         for row in self.rows:
#             if row.filter == filter:
#                 for col, val in updated_values.items():
#                     row.columns[col].value = val
#
#
# class TotalManager:
#     def __init__(self, **kwargs):
#         self.data_manager = kwargs.get('data_manager', DataManager())
#
#     def get_column(self, table_name: str, column_name: str, filter:str=None) -> Column:
#         return Column.get_value_from_table(table_name, column_name, filter=filter, data_manager=self.data_manager)
#
#     def get_row(self, table_name: str, filter: str=None) -> Row:
#         return Row.load_row(table_name, filter=filter, data_manager=self.data_manager)
#
#     def get_table(self, table_name: str, filter: str=None) -> Table:
#         return Table.get_filtered_table(table_name, filter=filter, data_manager=self.data_manager)