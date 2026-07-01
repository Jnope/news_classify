import logging
import re

import redis
from simhash import Simhash

from src.config.config import settings
from src.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

_FP_SET_KEY = "NEWS:news_fingerprints"

_RE_HTML = re.compile(r"<[^>]+>")
_RE_WHITESPACE = re.compile(r"\s+")


def _clean_text(text: str) -> str:
    text = _RE_HTML.sub("", text)
    text = _RE_WHITESPACE.sub(" ", text)
    return text.strip().lower()


class NewsDedupEngine:
    def __init__(
        self,
        ttl_hours: int = settings.dedup_ttl_hours,
        hamming_threshold: int = settings.dedup_hamming_threshold,
    ):
        self.redis_client = get_redis_client()
        self.ttl_seconds = ttl_hours * 3600
        self.hamming_threshold = hamming_threshold

    def generate_fingerprint(self, text: str) -> int:
        cleaned_text = _clean_text(text)
        return Simhash(cleaned_text).value

    @staticmethod
    def _hamming_distance(fp1: int, fp2: int) -> int:
        return bin(fp1 ^ fp2).count("1")

    def _load_fingerprints(self) -> set[int]:
        fingerprints: set[int] = set()

        cursor = 0
        while True:
            cursor, batch = self.redis_client.sscan(
                name=_FP_SET_KEY,
                cursor=cursor,
                count=500,
            )
            for member in batch:
                try:
                    fingerprints.add(int(member))
                except (TypeError, ValueError):
                    continue
            if cursor == 0:
                break

        return fingerprints

    def is_duplicate(self, new_text: str, fingerprint: int | None = None) -> tuple[bool, int]:
        if fingerprint is None:
            fingerprint = self.generate_fingerprint(new_text)
        try:
            stored_fps = self._load_fingerprints()
        except redis.RedisError as e:
            logger.warning("Redis不可用，跳过去重检查: %s", e)
            return False, fingerprint
        for stored_fp in stored_fps:
            dist = self._hamming_distance(fingerprint, stored_fp)
            if dist <= self.hamming_threshold:
                logger.info("发现相似新闻，海明距离=%d", dist)
                return True, fingerprint
        return False, fingerprint

    def save_fingerprint(self, fingerprint: int) -> None:
        try:
            self.redis_client.sadd(_FP_SET_KEY, str(fingerprint))
            self.redis_client.expire(_FP_SET_KEY, self.ttl_seconds)
        except redis.RedisError as e:
            logger.warning("Redis不可用，指纹未入库: %s", e)

    def process_news(self, news_text: str) -> dict:
        is_dup, fp = self.is_duplicate(news_text)
        if is_dup:
            return {"status": "skipped", "reason": "存在相似新闻"}
        self.save_fingerprint(fp)
        return {"status": "saved"}