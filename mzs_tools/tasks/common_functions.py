from ..tasks.access_db_connection import AccessDbConnection


def setup_mdb_connection(mdb_path, password=None):
    connected = False
    mdb_conn = None
    try:
        mdb_conn = AccessDbConnection(mdb_path, password=password)
        connected = mdb_conn.open()
    except Exception as e:
        raise e

    return connected, mdb_conn
