import logging
import threading

import pandas as pd

from src.config.config import settings

logger = logging.getLogger(__name__)

_db_conn = None
_db_init_lock = threading.Lock()
_db_query_lock = threading.Lock()


def _get_db_conn():
    """获取/创建 DatabaseConn 单例（线程安全）"""
    global _db_conn
    if _db_conn is not None:
        return _db_conn

    with _db_init_lock:
        if _db_conn is not None:
            return _db_conn

        try:
            from transwarp.timelyre.timelyre_public import DatabaseConn
        except ImportError:
            raise ImportError(
                "transwarp-timelyre 未安装，无法连接内部数据库。"
                "请联系管理员安装或切换到其他数据源。"
            )

        jdbc_http_proxy = settings.tm_jdbc_http_proxy
        real_conn = settings.tm_real_conn
        db_name = settings.tm_db_name
        db_user = settings.tm_db_user
        password = settings.tm_db_password
        token = settings.tm_guardian_token
        session_timeout = settings.tm_session_timeout
        login_timeout = settings.tm_login_timeout

        try:
            _db_conn = DatabaseConn(
                jdbc_http_proxy=jdbc_http_proxy,
                real_conn=real_conn,
                db=db_name,
                auth_type="ldap",
                username=db_user,
                password=password,
                token=token,
                disable_cancel=True,
                session_timeout=session_timeout,
                login_timeout=login_timeout,
            )
            logger.info("TransMatrix DatabaseConn 初始化成功")
            return _db_conn
        except Exception as e:
            logger.error("DatabaseConn初始化失败: %s", e)
            raise


def query_as_df(
    table: str,
    query: str = "",
    select_cols: str | None = None,
    condition: str | None = None,
    **kwargs,
) -> pd.DataFrame:
    """查询 TimeLyre 表并返回 DataFrame（线程安全）

    Args:
        table: 表名，如 meta_data.stock_code
        query: 过滤条件，如 code='000001'
        select_cols: 查询列
        condition: 额外条件
    """
    with _db_query_lock:
        conn = _get_db_conn()
        df = conn.query_as_df(
            tbl=table,
            query=query or None,
            select_cols=select_cols,
            condition=condition,
            **kwargs,
        )
        return df


def insert(table: str, values: list[dict], batch: int = 2000) -> None:
    """批量写入 TimeLyre 表（线程安全）

    Args:
        table: 表名
        values: 行数据列表，每行为 {列名: 值}
        batch: 每批写入行数
    """
    if not values:
        return
    with _db_query_lock:
        conn = _get_db_conn()
        conn.insert(table=table, values=values, batch=batch)