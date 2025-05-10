import sqlite3
import logging
import pandas as pd

def execute_query(query, db_path):
    """
    Executes an SQL query on the specified SQLite database.

    Args:
        query (str): The SQL query to execute.
        db_path (str): Path to the SQLite database file.

    Returns:
        pd.DataFrame: Query results as a pandas DataFrame, or an empty DataFrame on error.
    """
    try:
        # Connect to the SQLite database
        with sqlite3.connect(db_path) as conn:
            # Execute the query and fetch the results into a DataFrame
            result = pd.read_sql_query(query, conn)
            return result
    except sqlite3.Error as e:
        logging.error(f"Erro ao executar consulta SQL: {e}")
        return pd.DataFrame()
    except Exception as ex:
        logging.error(f"Erro inesperado: {ex}")
        return pd.DataFrame()
