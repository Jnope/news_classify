import logging
import re
import threading
import time

import pandas as pd

from src.config.config import settings
from src.utils.timelyre_client import query_as_df

logger = logging.getLogger(__name__)

_STOCK_COLUMNS = ["code", "name", "short_name"]


class StockDataService:
    def __init__(self, refresh_interval: int = settings.stock_refresh_interval):
        self._refresh_interval = refresh_interval
        self._df: pd.DataFrame | None = None
        self._last_load: float = 0.0
        self._lock = threading.Lock()

    def _load(self) -> pd.DataFrame:
        df = None
        try:
            df = self._load_from_db()
            missing = [c for c in _STOCK_COLUMNS if c not in df.columns]
            if missing:
                logger.warning("数据库数据缺少列 %s，实际列: %s", missing, list(df.columns))
                df = None
        except Exception as e:
            logger.warning("从数据库加载股票数据失败，从 CSV 兜底: %s", e)

        if df is not None:
            self._save_to_local(df)
        else:
            df = self._load_from_local()

        df = df[_STOCK_COLUMNS].copy()
        for col in _STOCK_COLUMNS:
            df[col] = df[col].astype(str)
        return df

    def _load_from_db(self) -> pd.DataFrame:
        logger.info("从 TimeLyre 数据库加载股票数据")
        return query_as_df(table="stock_code", query="select * from stock_code")

    def _save_to_local(self, df: pd.DataFrame):
        path = settings.source / "stock_code.csv"
        logger.info("写入股票数据到本地 CSV: %s", path)
        df.to_csv(path, index=False, encoding="utf-8-sig")

    def _load_from_local(self) -> pd.DataFrame:
        path = settings.source / "stock_code.csv"
        logger.info("从本地加载股票数据: %s", path)
        return pd.read_csv(path, encoding="utf-8-sig")

    def _ensure_fresh(self):
        now = time.time()
        if self._df is None or (now - self._last_load) >= self._refresh_interval:
            with self._lock:
                if self._df is None or (time.time() - self._last_load) >= self._refresh_interval:
                    logger.info("加载/刷新股票数据")
                    self._df = self._load()
                    self._last_load = time.time()

    @property
    def df(self) -> pd.DataFrame:
        self._ensure_fresh()
        return self._df

    def force_refresh(self):
        with self._lock:
            logger.info("强制刷新股票数据")
            self._df = self._load()
            self._last_load = time.time()

    def search(self, keyword: str) -> list[dict]:
        keyword = keyword.strip()
        if not keyword:
            return []
        escaped = re.escape(keyword)
        mask = (
            self.df["name"].str.contains(escaped, na=False, case=False, regex=True)
            | self.df["code"].str.contains(escaped, na=False, case=False, regex=True)
            | self.df["short_name"].str.contains(escaped, na=False, case=False, regex=True)
        )
        matched = self.df[mask].drop_duplicates(subset=["code"])
        if matched.empty:
            return []
        return matched[["code", "name"]].to_dict(orient="records")


stock_data_service = StockDataService()