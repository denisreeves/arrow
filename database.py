import mysql.connector
import pandas as pd
import numpy as np
from pathlib import Path
import os
from typing import Dict, Optional, Union, List, Tuple
import logging
import os
import mysql.connector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration from .env
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Connect to MySQL
def connect_db():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# Example: Create users table if it doesn’t exist
def init_db():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()
    print("✅ MySQL Database initialized successfully!")

# Run the initialization
init_db()

class Database:
    def __init__(self, host="localhost", user="root", password="", database="resumes"):
        """Initialize database connection."""
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.setup_logging()
        self.connect_db()

    def setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='resume_search.log'
        )
        self.logger = logging.getLogger(__name__)

    def connect_db(self):
        """Connect to MySQL database."""
        try:
            self.conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            self.cursor = self.conn.cursor()
            self.create_database()
        except mysql.connector.Error as err:
            self.logger.error(f"Error: {err}")
            raise

    def create_database(self):
        """Create database if not exists."""
        try:
            self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            self.conn.database = self.database
        except mysql.connector.Error as err:
            self.logger.error(f"Database creation error: {err}")
            raise

    def create_table_from_df(self, df: pd.DataFrame, table_name: str) -> None:
        """Dynamically create table based on DataFrame columns."""
        try:
            columns = []
            for col in df.columns:
                if df[col].dtype in [np.float64, np.int64]:
                    col_type = "DOUBLE"
                elif df[col].dtype == object:
                    col_type = "TEXT"
                else:
                    col_type = "VARCHAR(255)"
                columns.append(f"`{col}` {col_type}")

            columns_str = ", ".join(columns)
            create_table_sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` (id INT AUTO_INCREMENT PRIMARY KEY, {columns_str})"
            self.cursor.execute(create_table_sql)
            self.conn.commit()
        except mysql.connector.Error as err:
            self.logger.error(f"Table creation error: {err}")
            raise

    def insert_data_from_df(self, df: pd.DataFrame, table_name: str) -> None:
        """Insert data from DataFrame into table."""
        try:
            for _, row in df.iterrows():
                values = tuple(row)
                placeholders = ", ".join(["%s"] * len(row))
                insert_sql = f"INSERT INTO `{table_name}` ({', '.join(df.columns)}) VALUES ({placeholders})"
                self.cursor.execute(insert_sql, values)

            self.conn.commit()
        except mysql.connector.Error as err:
            self.logger.error(f"Data insertion error: {err}")
            raise

    def query_data(self, query: str) -> List[Tuple]:
        """Execute a query and return the result."""
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except mysql.connector.Error as err:
            self.logger.error(f"Query execution error: {err}")
            raise

    def close_connection(self):
        """Close the database connection."""
        self.cursor.close()
        self.conn.close()
