import aiohttp
import aiopg
import asyncio
import datetime
from collections import deque
import pytest
import re

from async_poller import fetch_page_data, write_to_db

correct_url = ('https://python.org',
               3,
               re.compile(r'Python\s+is\s+a\s+programming'))
wrong_url = ('https://blablabla.org', 3)


@pytest.mark.asyncio
async def test_data_fetch(db):
    """
    Test the data fetching and queue population
    :param db: pytest fixture, loads the DBHelper instance
    :return:
    """
    result_queue = deque()
    error_queue = deque()
    global_timeout = 3

    session_timeout = aiohttp.ClientTimeout(total=None,
                                            sock_connect=global_timeout,
                                            sock_read=global_timeout)

    async with aiohttp.ClientSession(timeout=session_timeout) as session:
        url, interval, regex = correct_url
        for _ in range(3):
            delta = await fetch_page_data(
                session, url, result_queue, error_queue, regex, timeout=3
            )
            await asyncio.sleep(max(0.1, interval - delta))

        assert len(result_queue) == 3, "Improper result queue length"
        assert len(error_queue) == 0, "Improper error queue length"

        url, interval = wrong_url
        for _ in range(3):
            delta = await fetch_page_data(
                session, url, result_queue, error_queue, timeout=5
            )
            await asyncio.sleep(max(0.1, interval-delta))
        assert len(result_queue) == 3, "Improper result queue length"
        assert len(error_queue) == 3, "Improper error queue length"

    result_list = [result_queue.popleft() for _ in range(3)]
    error_list = [error_queue.popleft() for _ in range(3)]
    async with aiopg.create_pool(db.dsn) as pool:
        await write_to_db(pool, result_list, db.insert_result_sql)
        await write_to_db(pool, error_list, db.insert_error_sql)


def test_results(db):
    """
    validate the correctness of fetched results
    :param db: pytest fixture, loads the DBHelper instance
    :return: 
    """

    url, interval, _ = correct_url
    result_table = db.execute_many(f'SELECT * FROM {db.result_table}')
    assert len(result_table) == 3

    start_timestamp = result_table[1]['timestamp']
    end_timestamp = result_table[2]['timestamp']
    actual_interval = int((end_timestamp-start_timestamp).total_seconds())
    assert actual_interval == interval

    for entry in result_table:
        assert entry['url'] == url, 'Wrong url entry'
        assert entry['status_code'] == 200, 'Wrong status code'
        assert entry['regex_found'], 'Improper regex flag'
        assert 0 < entry['duration'] < 3
        assert isinstance(entry['timestamp'], datetime.datetime)


def test_errors(db):
    """
    Test the the correctness of fetched errors
    :param db: pytest fixture, loads the DBHelper instance
    :return:
    """
    error_table = db.execute_many(f'SELECT * FROM {db.error_table}')
    url, interval = wrong_url

    start_timestamp = error_table[1]['timestamp']
    end_timestamp = error_table[2]['timestamp']
    actual_interval = int((end_timestamp-start_timestamp).total_seconds())
    assert actual_interval == interval

    for entry in error_table:
        assert entry['url'] == url, 'Wrong url entry'
        assert entry['error'].startswith('Cannot connect to host')
        assert isinstance(entry['timestamp'], datetime.datetime)
