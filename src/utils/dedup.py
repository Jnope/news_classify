import time
import redis
from simhash import Simhash

class NewsDedupEngine:
    def __init__(self, redis_host='localhost', redis_port=6379, ttl_hours=24):
        """
        初始化去重引擎
        :param ttl_hours: 指纹在缓存中的存活时间（默认24小时）
        """
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        self.ttl_seconds = ttl_hours * 3600
        self.hamming_threshold = 3  # 海明距离阈值，<=3 视为相似/重复

    def generate_fingerprint(self, text: str) -> int:
        """
        1. 预处理与生成指纹：清洗文本并生成64位SimHash指纹
        """
        # 实际业务中建议在此处加入 jieba分词、去除停用词、去HTML标签等预处理逻辑
        cleaned_text = text.strip().lower()
        return Simhash(cleaned_text).value

    def _calculate_hamming_distance(self, fp1: int, fp2: int) -> int:
        """计算两个指纹之间的海明距离"""
        xor = fp1 ^ fp2
        return bin(xor).count('1')

    def is_duplicate(self, news_text: str) -> bool:
        """
        2. 查重比对：判断该新闻在24小时内是否已处理过
        """
        current_fp = self.generate_fingerprint(news_text)

        # 获取 Redis 中所有未过期的指纹（实际生产环境建议使用 LSH 或分桶索引优化，避免全量遍历）
        # 这里为了演示核心逻辑，获取所有 key
        all_keys = self.redis_client.keys("news_fp:*")

        for key in all_keys:
            stored_fp = int(self.redis_client.get(key))
            # 计算海明距离
            if self._calculate_hamming_distance(current_fp, stored_fp) <= self.hamming_threshold:
                print(f"⚠️ 发现相似新闻，命中缓存 Key: {key}")
                return True

        return False

    def save_fingerprint(self, news_text: str, news_id: str = None) -> str:
        """
        3. 决策与入库：如果不重复，将SimHash结果存入Redis，并设置24h自动过期
        """
        current_fp = self.generate_fingerprint(news_text)

        # 使用 news_id 或 时间戳+指纹 作为 Redis 的 Key
        if not news_id:
            news_id = str(int(time.time() * 1000))

        cache_key = f"news_fp:{news_id}"

        # 存入 Redis，并设置 TTL（24小时后自动删除）
        self.redis_client.setex(cache_key, self.ttl_seconds, str(current_fp))

        print(f"✅ 新闻为原创/新事件，指纹已入库: {cache_key} (TTL: {self.ttl_seconds}s)")
        return cache_key

    def process_news(self, news_text: str, news_id: str = None):
        """
        完整的新闻去重流水线
        """
        if self.is_duplicate(news_text):
            return {"status": "skipped", "reason": "24小时内存在相似新闻"}
        else:
            key = self.save_fingerprint(news_text, news_id)
            return {"status": "saved", "cache_key": key}

# --- 模拟运行测试 ---
if __name__ == "__main__":
    engine = NewsDedupEngine()

    # 模拟第一条突发新闻
    news_1 = "某科技公司今日发布革命性AI大模型，引发行业震动。"
    print(engine.process_news(news_1, "news_001"))

    # 模拟2小时后，另一家媒体转载或改写的相同新闻
    news_2 = "今日，某科技巨头发布了颠覆性的AI大模型，整个行业为之震动。"
    print(engine.process_news(news_2, "news_002"))

    # 模拟一条完全不同的新闻
    news_3 = "明日天气预报显示，上海将有暴雨，市民请注意防范。"
    print(engine.process_news(news_3, "news_003"))