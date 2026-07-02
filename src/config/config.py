import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


def _pop_proxy():
    for _key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(_key, None)
    os.environ.setdefault("NO_PROXY", "*")


_pop_proxy()


class _Paths(BaseSettings):
    model_config = {"arbitrary_types_allowed": True}
    root: Path = Path(__file__).resolve().parent.parent.parent
    source: Path = root / "source"


_paths = _Paths()


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Paths
    root: Path = _paths.root
    source: Path = _paths.source

    # LLM
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "openai/deepseek-v4-flash"
    llm_temperature: float = 0.3

    # Redis 主从高可用
    redis_master_url: str = "redis://localhost:6379"
    redis_slave_urls: str = ""
    redis_password: str = ""
    redis_db: int = 0
    redis_decode_responses: bool = True
    redis_health_check_interval: int = 30

    # TimeLyre 数据库
    tm_jdbc_http_proxy: str = "172.18.192.74:9998"
    tm_real_conn: str = "jdbc:hive2://172.18.192.75:10006"
    tm_db_name: str = "meta_data"
    tm_db_user: str = "admin"
    tm_db_password: str = "admin"
    tm_guardian_token: str = "UgJRRGe7qMAKcirOQ017-TDH"
    tm_session_timeout: int = 60000
    tm_login_timeout: int = 15000

    # Stock data
    stock_refresh_interval: int = 3600 * 12

    # Dedup
    dedup_ttl_hours: int = 24
    dedup_hamming_threshold: int = 3

    # Logging
    log_level: str = "WARNING"
    log_dir: str = "/var/log/.news/"

# Kafka（空配置表示禁用流式消费）
    kafka_bootstrap_servers: str = ""
    kafka_topic: str = ""
    kafka_group_id: str = "news-classify"
    kafka_security_protocol: str = "SASL_SSL"
    kafka_sasl_mechanism: str = "PLAIN"
    kafka_sasl_username: str = ""
    kafka_sasl_password: str = ""
    kafka_poll_timeout: float = 5.0
    kafka_max_records: int = 500
    kafka_worker_count: int = 8

    # MySQL
    mysql_host: str = "rm-uf6c66e2638x57rl83o.mysql.rds.aliyuncs.com"
    mysql_port: int = 3306
    mysql_user: str = "xh_yuq_sys"
    mysql_password: str = "Hy2YvbEZxZw2AMQW"
    mysql_db: str = "xh_out_db"

    # Constants
    macro_categories: list[str] = Field(default=[
        "货币政策与流动性",
        "财政与产业政策",
        "宏观经济数据",
        "地缘政治与国际宏观",
        "跨行业监管与合规",
        "资本市场顶层设计",
        "突发公共事件与自然灾害",
        "其他",
    ])
    industry_category: list[str] = Field(default=[
        "计算机I", "通信I", "汽车I",
        "机械设备I", "煤炭I", "医药生物I",
        "化工I", "交通运输I", "食品饮料I",
        "轻工制造I", "家用电器I", "电气设备I",
        "建筑材料I", "国防军工I", "公用事业I",
        "传媒I", "房地产I", "电子I",
        "环保I", "非银金融I", "纺织服装I",
        "建筑装饰I", "商业贸易I", "有色金属I",
        "休闲服务I", "综合I", "钢铁I",
        "美容护理I", "银行I", "农林牧渔I",
        "石油石化I",
    ])

    @property
    def redis_slave_url_list(self) -> list[str]:
        return [u.strip() for u in self.redis_slave_urls.split(",") if u.strip()]


settings = Settings()