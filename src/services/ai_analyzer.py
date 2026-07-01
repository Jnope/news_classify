import logging

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from src.config.config import settings
from src.models.RespModels import FinalOutput
from src.services.stock_data import stock_data_service

logger = logging.getLogger(__name__)

FINAL_PROMPT = f"""# Role
你是一名资深金融投研专家与量化数据分析师。你的核心能力是从复杂的财经新闻文本中，精准提取宏观维度及个股维度的结构化信息。

# Task
请阅读用户提供的新闻，并严格按照以下逻辑进行多维度分析

# 核心分析逻辑

## 1. 宏观维度分析 (macro: MacroInfo)
- is_macro (bool): 判断该新闻是否属于宏观范畴。
- macro_category (list[str]): 非宏观为空数组 []，宏观从以下列表中选择一个或多个分类，：{",".join(settings.macro_categories)}。
- sentiment (int): 宏观新闻评估其对资本市场的整体影响, 1: 积极/宽松, 0: 中性, -1: 紧缩/风险；非宏观新闻，设为 0。
- ai_summary (str): 用 100 字以内高度概括新闻的核心宏观要点，必须客观、精炼。

## 2. 个股维度分析 (stock_relations: list[StockRelation])
- 对于宏观新闻，不再分析，stock_relations 直接返回空数组 []。
- 对于非宏观新闻，按照以下顺序执行：
  - 提取出新闻中所有提及的公司名称、股票， 作为company_keywords: list[str]；
  - 单次调用search_stock_code工具，获取股票信息列表，无论返回结果如何，不重复调用，若未匹配任何股票，则stock_relations 直接返回空数组 []。
- StockRelation 中：code (股票代码：股票信息的code属性，如 600036.SH), relevance (关联度 0.0-1.0), sentiment (1: 积极, 0: 中性, -1: 负面), link_reason (关联依据/原文片段)。
"""


@tool(description="一次性接收将新闻中提及的所有公司、股票，并批量转换为标准股票代码和名称")
def batch_search_stock_codes(company_keywords: list[str]) -> list[dict]:
    cleaned_keywords = list(set(k.strip() for k in company_keywords if k and k.strip()))
    if not cleaned_keywords:
        return [{"keyword": None, "stocks": [], "error": "传入为空，无匹配的股票"}]

    results = []
    for keyword in cleaned_keywords:
        try:
            matched = stock_data_service.search(keyword)
        except Exception as e:
            results.append({"keyword": keyword, "stocks": [], "error": f"匹配异常: {e}"})
            continue
        if matched:
            results.append({"keyword": keyword, "stocks": matched})
        else:
            results.append({"keyword": keyword, "stocks": [], "info": "未找到匹配的股票"})
    return results


class AIAnalyzer:
    def __init__(self):
        self._llm = ChatOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
        )
        self._agent = create_agent(
            model=self._llm,
            tools=[batch_search_stock_codes],
            system_prompt=FINAL_PROMPT,
            response_format=ToolStrategy(FinalOutput),
            middleware=[
                ToolCallLimitMiddleware(
                    tool_name="batch_search_stock_codes",
                    thread_limit=5,
                    run_limit=3,
                )
            ],
        )

    def analyze(self, title: str, content: str) -> dict | None:
        try:
            resp = self._agent.invoke(
                {"messages": [{"role": "user", "content": f"新闻标题: {title}\n新闻内容: {content}"}]},
            )
            return resp["structured_response"].model_dump()
        except Exception as e:
            logger.error("AI分析失败: %s", e)
            return None


_instance: "AIAnalyzer | None" = None


def get_ai_analyzer() -> "AIAnalyzer":
    global _instance
    if _instance is None:
        _instance = AIAnalyzer()
    return _instance