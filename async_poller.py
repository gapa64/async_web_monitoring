import aiohttp
import aiopg
import asyncio
from collections import deque
from datetime import datetime
import re

from dbhelper import DBHelper


async def poll(db: DBHelper,
               urls: list,
               web_timeout: int = 4,
               dump_interval: int = 3):
    """
    Main function of web monitoring which asynchronously polls
    the websites and dumps the chunks of results into Postgresql.
    The function gather all the async polling and dumping tasks, and
    pass it to event loop.
    :param db: DBHelper objects contained details of DB connections
    :param urls: List of URL tuples, with input data
    :param web_timeout: int, seconds. Max time to wait response from http
    :param dump_interval: int, seconds. Interval of dumping queue to Database
    :return: None
    """

    result_queue = deque()
    error_queue = deque()

    timeout = aiohttp.ClientTimeout(total=None,
                                    sock_connect=web_timeout,
                                    sock_read=web_timeout)

    async with aiopg.create_pool(db.dsn) as pool:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            polling_tasks = build_tasks(
                urls, session, result_queue, error_queue
            )
            result_dumper = asyncio.create_task(
                bulk_dump(pool,
                          result_queue,
                          db.insert_result_sql,
                          dump_interval)
            )
            error_dumper = asyncio.create_task(
                bulk_dump(pool,
                          error_queue,
                          db.insert_error_sql,
                          dump_interval)
            )
            await asyncio.gather(result_dumper,
                                 error_dumper,
                                 *polling_tasks)


def build_tasks(urldb: list,
                session: aiohttp.client.ClientSession,
                result_queue: deque,
                error_queue: deque) -> list:
    """
    The function required to build atomic async polling tasks.
    Parse the URL tuples with parameters, instatiates them and
    return list of tasks
    :param urldb: list[tuple] Lists containing tuples with initail data
    :param session: aiohttp.client.ClientSession instance for polling,
    passed to task
    :param result_queue: deque to store correct fetched data, passed to task
    :param error_queue: deque to store error events, passed to task
    :return: list of asyincio tasks
    """
    task_list = []
    for entry in urldb:
        if len(entry) > 2:
            regex = re.compile(entry[2], re.DOTALL)
        else:
            regex = None
        task = asyncio.create_task(
            website_poll(session=session,
                         url=entry[0],
                         interval=entry[1],
                         regex=regex,
                         result_queue=result_queue,
                         error_queue=error_queue)
        )
        task_list.append(task)
    return task_list


async def website_poll(interval: int,
                       session: aiohttp.client.ClientSession,
                       url: str,
                       result_queue: deque,
                       error_queue: deque,
                       regex: re.Pattern = None,
                       timeout: int = 4):
    """
    The function implements an asynchoronous periodical polling
    of a single side. Sleep and await data fetching function
    :param session: aiohttp.client.ClientSession, to fetch data,
    passed fetch_page_data
    :param url: str, url to fetch
    :param interval: int, interval of polling
    :param result_queue: deque to store correct fetched data,
    passed to fetch_page_data
    :param error_queue: deque to store error events,
    passed to fetch_page_data
    :param regex: re.Pattern, to validate if persis in webpage
    :param timeout: int, timeout with max wait time from remote web server
    :return:
    """

    while True:
        duration = await fetch_page_data(
            session, url, result_queue,
            error_queue, regex=regex, timeout=timeout
        )
        await asyncio.sleep(max(0.1, interval - duration))


async def fetch_page_data(session: aiohttp.client.ClientSession,
                          url: str,
                          result_queue: deque,
                          error_queue: deque,
                          regex: re.Pattern = None,
                          timeout: int = 4):
    """
    The function asynchronously retrieves data from a remote
    web server, parses result and put parsed data to result queue.
    If an error occurs, the result is damped to error queue.
    :param session: aiohttp.client.ClientSession, to fetch data,
    :param url: str, web url of remote web server
    :param result_queue: deque, the  queue to store fetched data
    :param error_queue: deque, the queue to store error events
    :param regex: re.Pattern, optional to search content on a web page
    :param timeout: int, timeout with max wait time from remote web server
    :return duration: real, seconds. duration of how long request was
    executing. The duration is required by polling function to adjust poll intervals.
    """

    start_timestamp = datetime.now()
    polling_results = {'url': url,
                       'timestamp': start_timestamp}
    try:
        async with session.get(url,
                               allow_redirects=True,
                               timeout=timeout) as response:
            content = await response.read()
        polling_results['duration'] = (
                datetime.now() - start_timestamp
        ).total_seconds()
        polling_results['status_code'] = response.status
        polling_results['regex_found'] = parse_web_page(regex, content)
        result_queue.append(polling_results)
        return polling_results['duration']

    except Exception as error:
        polling_results['error'] = f'{type(error)}--{error}',
        error_queue.append(polling_results)
        return (datetime.now() - start_timestamp).total_seconds()


def parse_web_page(pattern: re.Pattern,
                   data: bytes):
    """
    Get a raw web page content and search pattern occurence
    :param pattern: re.Pattern, pattern to search
    :param data: bytes, string
    :return: Bool or None, True if pattern found,
    False if pattern not found, and None if pattern is not
    specified
    """
    if pattern is None:
        return
    parsed = pattern.search(data.decode('utf'))
    if parsed is None:
        return False
    return True


async def bulk_dump(pool: aiopg.pool.Pool,
                    queue: deque,
                    sql: str,
                    dump_interval: int = 5):
    """
    The function implements asynchronous periodic dump of data to DB.
    The data chunks collected in queue by pollings tasks are extracted,
    the queue is drained, and passed to function.
    :param pool: aiopg.pool.Pool, poll of aiopg connections to database,
    passed to write_to_db function.
    :param queue: deque, queue with data
    :param sql: str, string SQL request, passed to write_to_db function.
    :param dump_interval: int, seconds. Interval of dumping queue to Database
    :return:
    """
    while True:
        await asyncio.sleep(dump_interval)
        dump_list = []
        if not queue:
            continue
        while queue:
            dump_list.append(queue.popleft())
        await write_to_db(pool, dump_list, sql)


async def write_to_db(pool: aiopg.pool.Pool,
                      values_deck: list,
                      sql: str):
    """
    The functions asynchronously writes date to the Database
    :param pool: poaiopg.pool.Pool, pool of connections to DB
    :param values_deck: list, list of dicts with fetched data
    :param sql: str, textual SQL request to insert data int DB.
    :return:
    """
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            for values in values_deck:
                await cur.execute(sql, values)
