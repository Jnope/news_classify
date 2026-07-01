import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

import pandas as pd

from src.config.config import settings
from src.utils.mysql_client import query

logger = logging.getLogger(__name__)

_SOURCES_NEWS = [
    "经济日报", "人民日报", "21世纪经济报道", "东方财富", "百度热搜"
]

_TABLE_NEWS = "news_realtime"
_TABLE_TELEGRAM = "telegram_realtime"


@dataclass
class NewsItem:
    item_id: str
    title: str
    content: str
    publish_time: str
    source: str
    source_url: str
    source_type: int  # 1-财联社内部, 2-全市场


class NewsFetcher:
    def __init__(self, source_dir: Path = settings.source):
        self._source_dir = source_dir

    def fetch_from_csv(self, filename: str, source_type: int) -> list[NewsItem]:
        path = self._source_dir / filename
        if not path.exists():
            logger.warning("新闻源文件不存在: %s", path)
            return []
        df = pd.read_csv(path, encoding="utf-8-sig")
        items: list[NewsItem] = []
        for _, row in df.iterrows():
            items.append(
                NewsItem(
                    item_id=str(row.get("item_id", "")),
                    title=str(row.get("title", "")),
                    content=str(row.get("content", "")),
                    publish_time=str(row.get("publish_time", "")),
                    source=str(row.get("source", "")),
                    source_url=str(row.get("source_url", "")),
                    source_type=source_type,
                )
            )
        return items

    def fetch_from_mysql_news(self) -> list[NewsItem]:
        return list(self._iter_mysql_news())

    def _iter_mysql_news(self, batch_size: int = 2000) -> Generator[NewsItem, None, None]:
        placeholders = ",".join("%s" for _ in _SOURCES_NEWS)
        since = "DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 MONTH), '%%Y-%%m-%%d 00:00:00')"
        last_time = ""
        while True:
            if last_time:
                sql = (
                    f"SELECT item_id, title, content, publish_time, source, source_url "
                    f"FROM {_TABLE_NEWS} "
                    f"WHERE source IN ({placeholders}) "
                    f"AND publish_time >= %s "
                    f"ORDER BY publish_time "
                    f"LIMIT {batch_size}"
                )
                rows = query(sql, tuple(_SOURCES_NEWS) + (last_time,))
            else:
                sql = (
                    f"SELECT item_id, title, content, publish_time, source, source_url "
                    f"FROM {_TABLE_NEWS} "
                    f"WHERE source IN ({placeholders}) "
                    f"AND publish_time >= {since} "
                    f"ORDER BY publish_time "
                    f"LIMIT {batch_size}"
                )
                rows = query(sql, tuple(_SOURCES_NEWS))
            if not rows:
                break
            for r in rows:
                last_time = str(r.get("publish_time", "") or "")
                yield NewsItem(
                    item_id=str(r["item_id"]),
                    title=str(r.get("title", "") or ""),
                    content=str(r.get("content", "") or ""),
                    publish_time=last_time,
                    source=str(r.get("source", "") or ""),
                    source_url=str(r.get("source_url", "") or ""),
                    source_type=2,
                )
        logger.info("从 MySQL %s 获取完毕", _TABLE_NEWS)

    def fetch_from_mysql_telegram(self) -> list[NewsItem]:
        return list(self._iter_mysql_telegram())

    def _iter_mysql_telegram(self, batch_size: int = 2000) -> Generator[NewsItem, None, None]:
        last_id = 0
        while True:
            sql = (
                f"SELECT id, title, content, publish_time, source, source_url "
                f"FROM {_TABLE_TELEGRAM} "
                f"WHERE publish_time >= DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 MONTH), '%%Y-%%m-%%d 00:00:00')"
                f"AND id > %s "
                f"ORDER BY id "
                f"LIMIT {batch_size}"
            )
            rows = query(sql, (last_id,))
            if not rows:
                break
            for r in rows:
                last_id = int(r["id"])
                yield NewsItem(
                    item_id=str(last_id),
                    title=str(r.get("title", "") or ""),
                    content=str(r.get("content", "") or ""),
                    publish_time=str(r.get("publish_time", "") or ""),
                    source=str(r.get("source", "") or ""),
                    source_url=str(r.get("source_url", "") or ""),
                    source_type=1,
                )
        logger.info("从 MySQL %s 获取完毕", _TABLE_TELEGRAM)

def fetch_all(self) -> Generator[NewsItem, None, None]:
        # yield from self.fetch_from_csv("macro.csv", source_type=2)
        # yield from self.fetch_from_csv("eastmoney.csv", source_type=2)
        count = 0
        for item in self._iter_mysql_news():
            yield item
            count += 1
        for item in self._iter_mysql_telegram():
            yield item
            count += 1
        logger.info("从 MySQL 共获取 %d 条新闻", count)


news_fetcher = NewsFetcher()