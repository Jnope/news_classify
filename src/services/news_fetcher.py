import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.config.config import settings

logger = logging.getLogger(__name__)


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

    def fetch_all(self) -> list[NewsItem]:
        news = self.fetch_from_csv("macro.csv", source_type=2)
        news.extend(self.fetch_from_csv("eastmoney.csv", source_type=2))
        logger.info("共获取 %d 条新闻", len(news))
        return news


news_fetcher = NewsFetcher()