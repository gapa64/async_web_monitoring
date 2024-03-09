"""
DBhelper implemeents the class which simplifies work
with Postgresql for Async MOn
"""
import psycopg2
import psycopg2.extras


class DBHelper:
    """
    Class  simplifies operations with PostgresSQL.
    Instatiates tables in PostgresSQL for Async Web Monitoring,
    and renders all the required SQL request for data dumping.
    """

    ERROR_FIELDS = (
        'id bigserial PRIMARY KEY, '
        'url text, '
        'error text, '
        'timestamp timestamp'
    )
    RESULT_FIELDS = (
        'id bigserial PRIMARY KEY, '
        'url text, '
        'status_code int, '
        'timestamp timestamp, '
        'duration real, '
        'regex_found bool'
    )

    RESULT_SQL = (
        'INSERT INTO {table} ' 
        '(url, status_code, regex_found, timestamp, duration) '
        'VALUES '
        '(%(url)s, %(status_code)s, %(regex_found)s, '
        '%(timestamp)s, %(duration)s) '
    )

    ERROR_SQL = (
        'INSERT INTO {table} ' 
        '(url, error, timestamp) '
        'VALUES (%(url)s, %(error)s, %(timestamp)s) '
    )

    CREATE_TABLE_SQL = (
        'CREATE TABLE IF NOT EXISTS '
        '{table_name} ({fields}) '
     )

    DROP_TABLE_SQL = (
        'DROP TABLE IF EXISTS {table_name}'
    )

    DSN_TEMPLATE = (
        'dbname={db_name} user={user} password={password} '
        'host={db_host} port={port}'
    )

    def __init__(self,
                 user: str,
                 password: str,
                 db_host: str,
                 db_name: str,
                 port: int,
                 result_table: str,
                 error_table: str):

        self.user = user
        self.password = password
        self.db_host = db_host
        self.port = port
        self.db_name = db_name
        self.result_table = result_table
        self.error_table = error_table
        self.init_tables(result_table, error_table)
        self.insert_result_sql = self.RESULT_SQL.format(
            table=self.result_table
        )
        self.insert_error_sql = self.ERROR_SQL.format(
            table=self.error_table
        )

    def execute_many(self, *sql_requests: str) -> list:
        """
        Connects to PostgresDB and execute set of requests
        :param sql_requests: str, packing with multiple requests
        :return: list of psycopg.Row fetched after request
        """
        with psycopg2.connect(user=self.user,
                              password=self.password,
                              host=self.db_host,
                              database=self.db_name,
                              port=self.port) as con:
            cursor = con.cursor(
                cursor_factory=psycopg2.extras.DictCursor
            )
            for request in sql_requests:
                cursor.execute(request)
            try:
                result = cursor.fetchall()
                return result
            except psycopg2.ProgrammingError:
                return []

    def insert_many(self, sql: str, values_deck: list):
        """
        Connects to Postgresql and insert multiple entries
        :param sql: str, SQL requests executed for insertion
        :param values_deck: list of dicts with values to be inserted
        :return:
        """
        with psycopg2.connect(user=self.user,
                              password=self.password,
                              host=self.db_host,
                              database=self.db_name,
                              port=self.port) as con:
            cursor = con.cursor()
            for values in values_deck:
                cursor.execute(sql, values)

    def init_tables(self, result_table: str, error_table: str):
        """
        Generates SQL request for creation of result and error tables
        and triggers table creation
        :param result_table: str, name of table to store results
        :param error_table: str, name of table to store errors
        :return:
        """

        result_table_sql = self.CREATE_TABLE_SQL.format(
            table_name=result_table,
            fields=self.RESULT_FIELDS
        )
        error_table_sql = self.CREATE_TABLE_SQL.format(
            table_name=error_table,
            fields=self.ERROR_FIELDS
        )
        self.execute_many(result_table_sql, error_table_sql)

    def flush(self):
        """
        Drop result and error tables.
        :return:
        """
        self.execute_many(
            self.DROP_TABLE_SQL.format(table_name=self.result_table),
            self.DROP_TABLE_SQL.format(table_name=self.error_table)
        )

    @property
    def dsn(self) -> str:
        return self.DSN_TEMPLATE.format(**self.__dict__)
