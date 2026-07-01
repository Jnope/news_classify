import logging
import signal
import time

from src.config.config import settings
from src.services.ai_analyzer import get_ai_analyzer
from src.services.kafka_consumer import kafka_consumer
from src.services.news_fetcher import news_fetcher
from src.services.result_store import result_store
from src.services.stock_data import stock_data_service
from src.utils.dedup import NewsDedupEngine
from src.utils.log_setter import setup_logging

logger = logging.getLogger(__name__)


class NewsAnalysisPipeline:
    def __init__(self):
        self._analyzer = get_ai_analyzer()
        self._fetcher = news_fetcher
        self._store = result_store
        self._dedup = NewsDedupEngine()
        self._running = False

    def run(self, keyword_filter: str | None = None):
        all_news = self._fetcher.fetch_all()

        logger.info("开始处理新闻（流式）")
        results: list[dict] = []
        skipped = 0
        total = 0

        for i, news in enumerate(all_news, 1):
            total = i
            if keyword_filter and keyword_filter not in news.content:
                continue

            dedup_result = self._dedup.process_news(news.content)
            if dedup_result["status"] == "skipped":
                skipped += 1
                logger.info("[%d] 跳过重复新闻: %s", i, news.title)
                continue

            extracted = self._analyzer.analyze(news.title, news.content)
            if extracted is not None:
                self._store.save_one({
                    "news_id": news.item_id,
                    "title": news.title,
                    "source_type": news.source_type,
                    "model_version": settings.llm_model,
                    "extracted": extracted,
                })
            else:
                self._store.save_one({
                    "news_id": news.item_id,
                    "title": news.title,
                    "source_type": news.source_type,
                    "model_version": settings.llm_model,
                    "extracted": {
                        "macro": {"is_macro": False, "macro_category": [], "sentiment": 0, "ai_summary": ""},
                        "stock_relations": [],
                    },
                })
            logger.info("[%d] 分析完毕: %s", i, news.title)

        self._store.flush()
        processed = total - skipped
        logger.info("处理完成: 共 %d 条, 去重跳过 %d 条, 分析 %d 条", total, skipped, processed)
        return results

    def run_streaming(self):
        if not kafka_consumer.enabled:
            logger.warning("Kafka 未配置，跳过流式消费")
            return

        self._running = True
        idle_rounds = 0
        logger.info("流式消费启动，等待 Kafka 消息...")

        def _stop(signum, frame):
            logger.info("收到停止信号，准备退出...")
            self._running = False

        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)

        while self._running:
            try:
                batch = kafka_consumer.poll()
            except Exception as e:
                logger.error("Kafka poll 异常: %s", e)
                time.sleep(5)
                continue

            if not batch:
                if idle_rounds % 60 == 0:
                    logger.debug("等待消息中... (缓冲池: %d 条)", self._store.buffered_count)
                idle_rounds += 1
                continue

            idle_rounds = 0
            logger.info("收到 %d 条 Kafka 消息", len(batch))

            for news in batch:
                dedup_result = self._dedup.process_news(news.content)
                if dedup_result["status"] == "skipped":
                    logger.info("跳过重复新闻: %s", news.title)
                    continue

                extracted = self._analyzer.analyze(news.title, news.content)
                if extracted is not None:
                    self._store.save_one({
                        "news_id": news.item_id,
                        "title": news.title,
                        "source_type": news.source_type,
                        "model_version": settings.llm_model,
                        "extracted": extracted,
                    })
                else:
                    self._store.save_one({
                        "news_id": news.item_id,
                        "title": news.title,
                        "source_type": news.source_type,
                        "model_version": settings.llm_model,
                        "extracted": {
                            "macro": {"is_macro": False, "macro_category": [], "sentiment": 0, "ai_summary": ""},
                            "stock_relations": [],
                        },
                    })
                logger.info("分析完毕: %s", news.title)

        self._store.flush()
        kafka_consumer.close()
        logger.info("流式消费已停止, 缓冲池已刷新")


def run_pipeline(keyword_filter: str | None = None):
    pipeline = NewsAnalysisPipeline()
    return pipeline.run(keyword_filter=keyword_filter)


if __name__ == "__main__":
    setup_logging()
    run_pipeline()
