import itertools
import logging
import threading
import time

import redis

from src.config.config import settings

logger = logging.getLogger(__name__)

_READ_COMMANDS = frozenset({
    "get", "mget", "exists", "scan", "sscan", "keys", "type", "ttl", "pttl",
    "hget", "hgetall", "hmget", "hkeys", "hvals", "hlen",
    "smembers", "sismember", "scard",
    "lrange", "llen", "lindex",
    "zrange", "zrangebyscore", "zscore", "zcard",
    "info", "dbsize", "ping",
})


class MasterSlaveRedis:
    """Redis 主从客户端：读操作走 slave（轮询），写操作走 master，带健康检查与故障转移。

    - 读命令自动路由到健康的 slave，全部 slave 不可用时回退到 master。
    - 写命令路由到 master；master 不可用时尝试用可写的 slave 顶替。
    - pipeline 默认绑定读客户端（适用于只读批量场景）。
    """

    def __init__(
        self,
        master_url: str,
        slave_urls: list[str],
        password: str = "",
        db: int = 0,
        decode_responses: bool = True,
        health_check_interval: int = 30,
    ):
        self._password = password or None
        self._db = db
        self._decode_responses = decode_responses
        self._health_check_interval = health_check_interval

        self._master_url = master_url
        self._slave_urls = slave_urls or []

        self._master = self._create_client(master_url)
        self._slaves = [self._create_client(url) for url in self._slave_urls]

        self._master_healthy = True
        self._slave_healthy = [True] * len(self._slaves)
        self._slave_cycle = itertools.cycle(range(len(self._slaves))) if self._slaves else None
        self._lock = threading.Lock()
        self._last_check = 0.0

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _create_client(self, url: str) -> redis.Redis:
        return redis.Redis.from_url(
            url,
            password=self._password,
            db=self._db,
            decode_responses=self._decode_responses,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )

    def _health_check(self):
        now = time.time()
        if now - self._last_check < self._health_check_interval:
            return
        self._last_check = now

        try:
            self._master.ping()
            self._master_healthy = True
        except redis.RedisError:
            self._master_healthy = False
            logger.warning("Redis master 不可用: %s", self._master_url)

        for i, slave in enumerate(self._slaves):
            try:
                slave.ping()
                self._slave_healthy[i] = True
            except redis.RedisError:
                self._slave_healthy[i] = False
                logger.warning("Redis slave 不可用: %s", self._slave_urls[i])

    def _get_read_client(self) -> redis.Redis:
        self._health_check()

        if self._slave_cycle:
            with self._lock:
                for _ in range(len(self._slaves)):
                    idx = next(self._slave_cycle)
                    if self._slave_healthy[idx]:
                        return self._slaves[idx]

        if self._master_healthy:
            return self._master

        logger.warning("无可用读节点，回退到 master")
        return self._master

    def _get_write_client(self) -> redis.Redis:
        self._health_check()

        if self._master_healthy:
            return self._master

        logger.warning("Redis master 不可用，尝试使用 slave 写入")
        for i, slave in enumerate(self._slaves):
            if not self._slave_healthy[i]:
                continue
            try:
                slave.ping()
                slave.set("__ha_probe__", "1", ex=1)
                slave.delete("__ha_probe__")
                logger.warning("已切换写入到 slave: %s", self._slave_urls[i])
                return slave
            except redis.RedisError:
                continue

        logger.error("所有 Redis 节点不可用")
        return self._master

    # ------------------------------------------------------------------
    # 显式读方法
    # ------------------------------------------------------------------
    def get(self, name):
        return self._get_read_client().get(name)

    def scan(self, cursor=0, **kwargs):
        return self._get_read_client().scan(cursor=cursor, **kwargs)

    def exists(self, *names):
        return self._get_read_client().exists(*names)

    # ------------------------------------------------------------------
    # 显式写方法
    # ------------------------------------------------------------------
    def set(self, name, value, **kwargs):
        return self._get_write_client().set(name, value, **kwargs)

    def setex(self, name, time, value):
        return self._get_write_client().setex(name, time, value)

    def delete(self, *names):
        return self._get_write_client().delete(*names)

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------
    def pipeline(self, transaction=True, shard_hint=None):
        return self._get_read_client().pipeline(transaction=transaction, shard_hint=shard_hint)

    def master_pipeline(self, transaction=True, shard_hint=None):
        return self._get_write_client().pipeline(transaction=transaction, shard_hint=shard_hint)

    # ------------------------------------------------------------------
    # 兜底
    # ------------------------------------------------------------------
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        if name in _READ_COMMANDS:
            return getattr(self._get_read_client(), name)
        return getattr(self._get_write_client(), name)


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------
_client: MasterSlaveRedis | None = None


def get_redis_client() -> MasterSlaveRedis:
    global _client
    if _client is None:
        _client = MasterSlaveRedis(
            master_url=settings.redis_master_url,
            slave_urls=settings.redis_slave_url_list,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=settings.redis_decode_responses,
            health_check_interval=settings.redis_health_check_interval,
        )
    return _client