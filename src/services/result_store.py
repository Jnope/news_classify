import logging
import threading
import time

from src.utils.timelyre_client import insert

logger = logging.getLogger(__name__)

_TABLE_AI_INFO = "NEWS_AI_INFO"
_TABLE_AI_CATEGORY = "NEWS_AI_CATEGORY"
_TABLE_STOCK_RELATION = "NEWS_STOCK_RELATION"


class ResultStore:
    def __init__(self, flush_interval: float = 10.0, batch_size: int = 50):
        self._flush_interval = flush_interval
        self._batch_size = batch_size

        self._ai_info_rows: list[dict] = []
        self._category_rows: list[dict] = []
        self._stock_rows: list[dict] = []
        self._lock = threading.Lock()
        self._last_flush = time.time()

    def save(self, results: list[dict]):
        for r in results:
            self.save_one(r)

    def save_one(self, result: dict):
        extracted = result.get("extracted") or {}
        macro = extracted.get("macro") or {}
        stock_relations = extracted.get("stock_relations") or []

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        with self._lock:
            self._ai_info_rows.append({
                "news_id": result.get("news_id", ""),
                "source_type": result.get("source_type", 0),
                "ai_summary": macro.get("ai_summary", ""),
                "sentiment": macro.get("sentiment", 0),
                "model_version": result.get("model_version", "unknown"),
                "created_at": now_str,
            })

            if macro.get("macro_category"):
                self._category_rows.append({
                    "news_id": result.get("news_id", ""),
                    "macro_category": ",".join(macro["macro_category"]),
                })

            for sr in stock_relations:
                self._stock_rows.append({
                    "news_id": result.get("news_id", ""),
                    "stock_code": sr.get("code", ""),
                    "stock_name": sr.get("stock_name", ""),
                    "relevance_score": sr.get("relevance", 0),
                    "sentiment": sr.get("sentiment", 0),
                    "link_reason": sr.get("link_reason", ""),
                    "created_at": now_str,
                })

            should_flush = len(self._ai_info_rows) >= self._batch_size

        if should_flush:
            self.flush()

    def flush(self):
        with self._lock:
            self._flush()

    def _flush(self):
        if not self._ai_info_rows:
            self._last_flush = time.time()
            return

        try:
            insert(_TABLE_AI_INFO, self._ai_info_rows)
            logger.info("写入 NEWS_AI_INFO %d 条", len(self._ai_info_rows))
        except Exception as e:
            logger.error("写入 NEWS_AI_INFO 失败: %s", e)

        if self._category_rows:
            try:
                insert(_TABLE_AI_CATEGORY, self._category_rows)
                logger.info("写入 NEWS_AI_CATEGORY %d 条", len(self._category_rows))
            except Exception as e:
                logger.error("写入 NEWS_AI_CATEGORY 失败: %s", e)

        if self._stock_rows:
            try:
                insert(_TABLE_STOCK_RELATION, self._stock_rows)
                logger.info("写入 NEWS_STOCK_RELATION %d 条", len(self._stock_rows))
            except Exception as e:
                logger.error("写入 NEWS_STOCK_RELATION 失败: %s", e)

        self._ai_info_rows.clear()
        self._category_rows.clear()
        self._stock_rows.clear()
        self._last_flush = time.time()

    @property
    def buffered_count(self) -> int:
        return len(self._ai_info_rows)


result_store = ResultStore()