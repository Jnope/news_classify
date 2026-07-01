import logging
import threading

import pymysql
from pymysql.cursors import DictCursor

from src.config.config import settings

logger = logging.getLogger(__name__)

_conn = None
_lock = threading.Lock()


def _get_conn():
    global _conn
    if _conn is not None:
        return _conn
    with _lock:
        if _conn is not None:
            return _conn
        _conn = pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_db,
            charset="utf8mb4",
            cursorclass=DictCursor,
        )
        logger.info("MySQL 连接成功: %s:%s/%s", settings.mysql_host, settings.mysql_port, settings.mysql_db)
        return _conn


def query(sql: str, params: tuple | None = None) -> list[dict]:
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def execute(sql: str, params: tuple | None = None) -> int:
    conn = _get_conn()
    with conn.cursor() as cur:
        affected = cur.execute(sql, params)
    conn.commit()
    return affected


def close():
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
        logger.info("MySQL 连接已关闭")