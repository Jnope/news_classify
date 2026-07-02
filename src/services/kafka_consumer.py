import json
import logging

from src.config.config import settings
from src.services.news_fetcher import NewsItem

logger = logging.getLogger(__name__)


class KafkaNewsConsumer:
    def __init__(self):
        self._consumer = None

    @property
    def enabled(self) -> bool:
        return bool(settings.kafka_bootstrap_servers and settings.kafka_topic)

    def _ensure_consumer(self):
        if self._consumer is not None:
            return
        if not self.enabled:
            raise RuntimeError("Kafka 未配置，无法启动消费者")
        from kafka import KafkaConsumer

        self._consumer = KafkaConsumer(
            settings.kafka_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers.split(",") if "," in settings.kafka_bootstrap_servers else [settings.kafka_bootstrap_servers],
            group_id=settings.kafka_group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            key_deserializer=lambda m: m.decode("utf-8") if m else None,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            security_protocol=settings.kafka_security_protocol,
            sasl_mechanism=settings.kafka_sasl_mechanism,
            sasl_plain_username=settings.kafka_sasl_username,
            sasl_plain_password=settings.kafka_sasl_password,
        )
        logger.info(
            "Kafka 消费者初始化成功: %s / %s",
            settings.kafka_bootstrap_servers,
            settings.kafka_topic,
        )

    def poll(self) -> list[NewsItem]:
        if not self.enabled:
            return []
        self._ensure_consumer()

        items: list[NewsItem] = []
        raw = self._consumer.poll(
            timeout_ms=int(settings.kafka_poll_timeout * 1000),
            max_records=settings.kafka_max_records,
        )
        for tp, messages in raw.items():
            for msg in messages:
                try:
                    value = msg.value
                    if not isinstance(value, dict):
                        logger.warning("Kafka 消息格式异常，跳过: %s", type(value))
                        continue
                    items.append(
                        NewsItem(
                            item_id=str(value.get("item_id", msg.key or "")),
                            title=str(value.get("title", "")),
                            content=str(value.get("content", "")),
                            publish_time=str(value.get("publish_time", "")),
                            source=str(value.get("source", "")),
                            source_url=str(value.get("source_url", "")),
                            source_type=int(value.get("source_type", 0)),
                        )
                    )
                except Exception as e:
                    logger.warning("Kafka 消息解析失败: %s", e)
                    continue
        return items

    def close(self):
        if self._consumer is not None:
            self._consumer.close()
            self._consumer = None
            logger.info("Kafka 消费者已关闭")


kafka_consumer = KafkaNewsConsumer()