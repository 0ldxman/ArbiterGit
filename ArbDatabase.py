from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import pprint
import random
import sqlite3
import datetime
from queue import Queue
import threading
import logging
from typing import Any, Dict, List, Optional
import json


class Logger:
    def __init__(self, log_file='Arbiter.log', log_level=logging.DEBUG):
        self.log_file = log_file
        self.log_level = log_level

        # Настройка логгирования
        c_log = logging
        c_log.basicConfig(filename=log_file, level=log_level,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logging = c_log.getLogger(__name__)

    def info(self, message) -> None:
        self.logging.info(message)

    def debug(self, message) -> None:
        self.logging.debug(message)

    def warning(self, message:str) -> None:
        self.logging.warning(message)

    def error(self, message) -> None:
        self.logging.error(message)

    def close(self) -> None:
        for handler in logging.root.handlers[:]:
            self.logging.root.removeHandler(handler)

    def clear_log_file(self):
        with open(self.log_file, 'w') as log_file:
            # Записываем пустую строку для очистки содержимого
            log_file.write('')

        print(f"Log file '{self.log_file}' has been cleared.")


class ConnectionPool:
    def __init__(self, max_connections:int, db_name='Arbiter.db'):
        self.max_connections = max_connections
        self.db_name = db_name
        self.connection_queue = Queue(max_connections)
        for _ in range(max_connections):
            connection = sqlite3.connect(db_name)
            self.connection_queue.put(connection)

    def get_connection(self):
        return self.connection_queue.get()

    def release_connection(self, conn):
        self.connection_queue.put(conn)

    def close_all_connections(self):
        while not self.connection_queue.empty():
            conn = self.connection_queue.get()
            conn.close()


DEFAULT_LOGGER = Logger()
DEFAULT_LOGGER.clear_log_file()
DEFAULT_POOL = ConnectionPool(100)


class DataManager:
    def __init__(self, connection_pool:ConnectionPool = DEFAULT_POOL, logger:Logger = DEFAULT_LOGGER):
        self.logger = logger

        self.connection_pool = connection_pool
        self.name = self.connection_pool.db_name

        self.connection = self.connection_pool.get_connection()
        self.cursor = self.connection.cursor()
        self.transaction_started = False

    def open_connection(self):
        self.connection = self.connection_pool.get_connection()
        self.cursor = self.connection.cursor()

    def close_connection(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection_pool.release_connection(self.connection)

    def begin_transaction(self):
        self.open_connection()
        if not self.transaction_started:
            self.connection.execute("BEGIN")
            self.transaction_started = True

    def commit_transaction(self):
        if self.transaction_started:
            self.connection.commit()
            self.logger.info("Transaction committed successfully")
            self.transaction_started = False

    def rollback_transaction(self):
        if self.transaction_started:
            self.connection.rollback()
            self.logger.warning("Transaction rolled back")
            self.transaction_started = False

    def execute(self, prompt, commit=True) -> None:
        try:
            self.cursor.execute(prompt)
            if commit:
                self.connection.commit()
                self.logger.info("Query executed successfully")
        except sqlite3.Error as e:
            self.rollback_transaction()
            self.logger.error(f"Error executing query: {prompt}, Error: {e}")
            raise

    def select(self, table_name, columns='*', filter=None) -> list[tuple]:
        query = f"SELECT {columns} FROM {table_name}"
        if filter:
            query += f" WHERE {filter}"

        self.cursor.execute(query)
        result = self.cursor.fetchall()

        self.logger.info(f"Selected data from {table_name}")

        return result

    def selectOne(self, table_name, columns='*', filter=None) -> tuple:
        query = f"SELECT {columns} FROM {table_name}"
        if filter:
            query += f" WHERE {filter}"

        self.cursor.execute(query)
        result = self.cursor.fetchone()

        self.logger.info(f"Selected one row from {table_name}")

        return result

    def delete(self, table_name:str, filter:str=None) -> None:
        query = f"DELETE FROM {table_name}"
        if filter:
            query += f" WHERE {filter}"

        self.cursor.execute(query)
        self.connection.commit()

    def update(self, table_name: str, columns_values: dict, filter: str = None) -> None:
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

        self.cursor.execute(query)
        self.connection.commit()

        self.logger.info(f"Updated data in {table_name}")

    def insert(self, table_name: str, columns_values: dict) -> None:
        columns_str = ', '.join(columns_values.keys())
        placeholders = ', '.join(['?'] * len(columns_values))

        column_names = ', '.join(f'"{col}"' for col in columns_values.keys())

        query = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
        values = tuple(columns_values.values())

        self.cursor.execute(query, values)
        self.connection.commit()

        self.logger.info(f"Inserted data into {table_name}")

    def maxValue(self, table_name: str, parameter: str, filter: str = None) -> int | float:
        if filter:
            query = f'SELECT MAX({parameter}) FROM {table_name} WHERE {filter}'
        else:
            query = f'SELECT MAX({parameter}) FROM {table_name}'

        c_output = self.cursor.execute(query).fetchone()[0]
        self.connection.commit()
        self.logger.info(f"Maximum value of {parameter} in {table_name} table is: {c_output}")

        if c_output is None:
            return -1
        else:
            return c_output

    def minValue(self, table_name: str, parameter: str, filter: str = None) -> int | float:
        if filter:
            query = f'SELECT MIN({parameter}) FROM {table_name} WHERE {filter}'
        else:
            query = f'SELECT MIN({parameter}) FROM {table_name}'

        c_output = self.cursor.execute(query).fetchone()[0]
        self.connection.commit()
        self.logger.info(f"Minimum value of {parameter} in {table_name} table is: {c_output}")
        return c_output

    def avgValue(self, table_name: str, parameter: str, filter: str = None) -> float:
        if filter:
            query = f'SELECT AVG({parameter}) FROM {table_name} WHERE {filter}'
        else:
            query = f'SELECT AVG({parameter}) FROM {table_name}'

        c_output = self.cursor.execute(query).fetchone()[0]
        self.connection.commit()
        self.logger.info(f"Average value of {parameter} in {table_name} table is: {c_output}")
        return c_output

    def get_count(self, table_name: str, parameter: str, filter: str = None) -> int | float:
        if filter:
            query = f'SELECT COUNT({parameter}) FROM {table_name} WHERE {filter}'
        else:
            query = f'SELECT COUNT({parameter}) FROM {table_name}'

        c_output = self.cursor.execute(query).fetchone()[0]
        self.connection.commit()
        self.logger.info(f"Count of {parameter} in {table_name} table is: {c_output}")
        return c_output

    def check(self, table_name: str, filter: str) -> bool:
        query = f"SELECT COUNT(*) FROM {table_name} WHERE {filter}"

        self.cursor.execute(query)
        result = self.cursor.fetchone()[0]

        self.logger.info(f"Checked data existence in {table_name}")

        return result > 0 if result else None

    def select_dict(self, table_name: str, columns='*', filter=None) -> list[dict]:
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

        self.logger.info(f"Selected data from {table_name}")

        return typed_result

    def get_all_tables(self) -> list:
        # Получение списка всех таблиц из базы данных
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in self.cursor.fetchall()]

        return tables

    def get_tables_with_prefix(self, prefix:str) -> list:
        c_tables = self.get_all_tables()
        total = [table for table in c_tables if prefix in table]
        return total

    def delete_from_all_tables(self, filters: dict, tables:list=None) -> None:
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

            self.logger.info(f"Deleted records from table {table_name} based on the given filter(s)")

        self.logger.info("Deletion from all tables completed successfully")

    def get_all_columns(self, table_name:str) -> list[str]:
        self.cursor.execute(f'SELECT * FROM {table_name} LIMIT 0')
        column_names = [desc[0] for desc in self.cursor.description]
        return column_names

    def get_columns_types(self, table_name:str) -> dict[str]:
        column_types = {}
        self.cursor.execute(f"SELECT name, type FROM pragma_table_info('{table_name}')")
        for row in self.cursor.fetchall():
            column_types[row[0]] = row[1]
        return column_types

    def __del__(self):
    #    self.cursor.close()
    #    self.commit_transaction()
        self.connection_pool.release_connection(self.connection)


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