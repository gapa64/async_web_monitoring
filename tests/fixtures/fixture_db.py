import pytest
import os

from dbhelper import DBHelper
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture(scope='module')
def db() -> DBHelper:
    """
    initialize database for tests
    :yield: database helper object
    remove tables after tests
    """
    db = DBHelper(
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'postgres'),
        db_name=os.getenv('DB_NAME', 'postgres'),
        port=int(os.getenv('DB_PORT', 5433)),
        db_host=os.getenv('DB_HOST', '127.0.0.1'),
        result_table='test_result_table',
        error_table='test_error_table'
    )
    yield db
    db.flush()
