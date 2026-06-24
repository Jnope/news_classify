import os
from pathlib import Path
import re

import pandas as pd
from langchain.agents.middleware import ToolCallLimitMiddleware

from langchain.agents.structured_output import ToolStrategy
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from src.models.RespModels import FinalOutput

os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.setdefault('NO_PROXY', "*")

industry_category = ['计算机I', '通信I', '汽车I',
            '机械设备I', '煤炭I', '医药生物I',
            '化工I', '交通运输I', '食品饮料I',
            '轻工制造I', '家用电器I', '电气设备I',
            '建筑材料I', '国防军工I', '公用事业I',
            '传媒I', '房地产I', '电子I',
            '环保I', '非银金融I', '纺织服装I',
            '建筑装饰I', '商业贸易I', '有色金属I',
            '休闲服务I', '综合I', '钢铁I',
            '美容护理I', '银行I', '农林牧渔I',
            '石油石化I']

ROOT = Path(__file__).parent.parent
SOURCE = ROOT / "source"

MACRO_CATEGORIES = [
    "货币政策与流动性",
    "财政与产业政策",
    "宏观经济数据",
    "地缘政治与国际宏观",
    "跨行业监管与合规",
    "资本市场顶层设计",
    "突发公共事件与自然灾害",
    "其他",
]

llm = ChatOpenAI(
    api_key="llmops-zhenjiang-368c5e8878cf7b0f55b02401fab49aec",
    base_url="https://llmops.transwarp.io/vibecoding/v1",
    model="openai/deepseek-v4-flash", # 对应你的 model 参数
    temperature=0.3
)

# 加载股票/行业基准数据 (MVP阶段全量放入Prompt)
stock_df: pd.DataFrame = pd.read_csv(SOURCE / "stock_code.csv", encoding='utf-8-sig')[[
    'code', 'name', 'short_name'
    # 'category', 'exchange', 'company_id', 'company_name', 'state'
]]

"""
## 2. 行业维度分析 (industry_relations)
- 返回一个数组，如果新闻不涉及任何行业，返回空数组 []。
- 包含字段：code (行业代码：**行业数据**的sw_l1_code列，如 801750), relevance (关联度 0.0-1.0), sentiment (1/0/-1), link_reason (关联依据/原文片段)。
"""

FINAL_PROMPT = f"""# Role
你是一名资深金融投研专家与量化数据分析师。你的核心能力是从复杂的财经新闻文本中，精准提取宏观维度及个股维度的结构化信息。

# Task
请阅读用户提供的新闻，并严格按照以下逻辑进行多维度分析

# 核心分析逻辑

## 1. 宏观维度分析 (macro: MacroInfo)
- is_macro (bool): 判断该新闻是否属于宏观范畴。
- macro_category (list[str]): 非宏观为空数组 []，宏观从以下列表中选择一个或多个分类，：{",".join(MACRO_CATEGORIES)}。
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
    """
    将新闻中提及的所有公司、股票批量转换为标准股票代码和名称。

    输入参数 company_keywords:
    一个字符串列表，包含新闻中提取出的公司名称、简称、别名或股票代码。
    例如：["茅台", "300750.SZ", "比亚迪"]
    """
    cleaned_keywords = list(set([k.strip() for k in company_keywords if k and k.strip()]))
    if not cleaned_keywords:
        return  [{
            "keyword": None,
            "stocks": [],
            "error": "传入为空，无匹配的股票"
        }]

    results = []

    for keyword in cleaned_keywords:
        escaped_keyword = re.escape(keyword)
        try:
            mask = (
                    stock_df['name'].str.contains(escaped_keyword, na=False, case=False, regex=True) |
                    stock_df['code'].str.contains(escaped_keyword, na=False, case=False, regex=True) |
                    stock_df['short_name'].str.contains(escaped_keyword, na=False, case=False, regex=True)
            )
            matched_stocks = stock_df[mask]
        except Exception as e:
            # 兜底异常处理，防止工具崩溃导致 Agent 终止
            results.append({
                "keyword": keyword,
                "stocks": [],
                "error": f"该关键词系统匹配异常: {str(e)}"
            })
            continue
        if not matched_stocks.empty:
            # 去重
            unique_matches = matched_stocks.drop_duplicates(subset=['code'])
            results.append({
                "keyword": keyword,
                "stocks": unique_matches[['code', 'name']].to_dict(orient='records')
            })
        else:
            results.append({
                "keyword": keyword,
                "stocks": [],
                "info": "该关键词未找到匹配的股票"
            })

    return results

agent = create_agent(
    model=llm,
    tools=[batch_search_stock_codes],
    system_prompt=FINAL_PROMPT,
    response_format=ToolStrategy(FinalOutput),
    middleware=[
        ToolCallLimitMiddleware(
            tool_name="batch_search_stock_codes",
            thread_limit=5,
            run_limit=3,
        )
    ]
)

def evaluate_all():
    all_news = pd.read_csv(SOURCE / "macro.csv").to_dict("records")
    all_news.extend(pd.read_csv(SOURCE / "eastmoney.csv").to_dict("records"))
    results = []

    index = 1

    for news in all_news:
        if not news["content"].__contains__("比亚迪"):
            continue
        try:
            resp = agent.invoke(
                {"messages": [{"role": "user", "content": f"新闻标题: {news['title']}\n新闻内容: {news['content']}"}]},
            )
            extracted = resp["structured_response"].model_dump()
            results.append({"news_id": news["item_id"],  "title": news.get("title"), "extracted": extracted})
        except Exception as e:
            print(e)
            results.append({"news_id": news["item_id"], "title": news.get("title"), "error": "调用错误"})
        print(f"{index} 分析完毕：{news["title"]}")
        index += 1

    df = pd.DataFrame(results)
    df_extracted = pd.DataFrame(df['extracted'].apply(lambda x: x if isinstance(x, dict) else {}).tolist())
    df_final = pd.concat([df[['news_id', 'title']].reset_index(drop=True),
                          df_extracted.reset_index(drop=True)], axis=1)
    target_path = SOURCE / 'all_out.csv'

    if os.path.isfile(target_path):
        df_old = pd.read_csv(target_path, encoding='utf-8-sig')

        df_combined = pd.concat([df_old, df_final], ignore_index=True)
        df_merged = df_combined.drop_duplicates(subset=['news_id'], keep='last')
        df_merged.to_csv(target_path, index=False, encoding='utf-8-sig')
    else:
        df_final.to_csv(target_path, index=False, encoding='utf-8-sig')

    print(f"评估完成，共处理 {len(results)} 条新闻，结果已保存至 source/all_out.json")


if __name__ == "__main__":
    evaluate_all()
