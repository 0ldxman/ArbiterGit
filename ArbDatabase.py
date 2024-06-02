import random
import sqlite3
import datetime
from queue import Queue
import threading
import logging
from typing import TypedDict, Any, TextIO
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
DEFAULT_POOL = ConnectionPool(50)


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

    def __del__(self):
    #    self.cursor.close()
    #    self.commit_transaction()
        self.connection_pool.release_connection(self.connection)

