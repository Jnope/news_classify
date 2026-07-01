import logging

from src.config.config import settings
from src.services.ai_analyzer import get_ai_analyzer
from src.services.news_fetcher import news_fetcher
from src.services.result_store import result_store
from src.services.stock_data import stock_data_service
from src.utils.dedup import NewsDedupEngine

logger = logging.getLogger(__name__)


class NewsAnalysisPipeline:
    def __init__(self):
        self._analyzer = get_ai_analyzer()
        self._fetcher = news_fetcher
        self._store = result_store
        self._dedup = NewsDedupEngine()

    def run(self, keyword_filter: str | None = None):
        all_news = self._fetcher.fetch_all()
        if keyword_filter:
            all_news = [n for n in all_news if keyword_filter in n.content]

        logger.info("开始处理 %d 条新闻", len(all_news))
        results: list[dict] = []
        skipped = 0

        for i, news in enumerate(all_news, 1):
            dedup_result = self._dedup.process_news(news.content)
            if dedup_result["status"] == "skipped":
                skipped += 1
                logger.info("[%d/%d] 跳过重复新闻: %s", i, len(all_news), news.title)
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
            logger.info("[%d/%d] 分析完毕: %s", i, len(all_news), news.title)

        self._store.flush()
        processed = len(all_news) - skipped
        logger.info("处理完成: 共 %d 条, 去重跳过 %d 条, 分析 %d 条", len(all_news), skipped, processed)
        return results


def run_pipeline(keyword_filter: str | None = None):
    pipeline = NewsAnalysisPipeline()
    return pipeline.run(keyword_filter=keyword_filter)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run_pipeline()
