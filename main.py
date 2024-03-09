"""
This is a main file of Async Web Monitoring.
The solution is base on a concept of asynchronous web monitoring
with asyncio and aiohttp, and periodic dumping to Postgresql with aiopg
"""
import asyncio
from dotenv import load_dotenv
import os

from dbhelper import DBHelper
from async_poller import poll
from urls import URLS_DB


def main():
    """
    Main function, load environment variables,
    instantiate databases, and starts monitoring
    :return:
    """
    load_dotenv()
    db_host = os.getenv('DB_HOST')
    db_port = int(os.getenv('DB_PORT'))
    db_user = os.getenv('POSTGRES_USER')
    db_password = os.getenv('POSTGRES_PASSWORD')
    db_name = os.getenv('DB_NAME')
    result_table = os.getenv('RESULT_TABLE')
    error_table = os.getenv('ERROR_TABLE')

    DUMP_INTERVAL = 3
    WEB_TIMEOUT = 3

    db = DBHelper(user=db_user,
                  password=db_password,
                  db_name=db_name,
                  port=db_port,
                  db_host=db_host,
                  result_table=result_table,
                  error_table=error_table)

    asyncio.run(poll(db, URLS_DB, WEB_TIMEOUT, DUMP_INTERVAL))


if __name__ == "__main__":
    main()
