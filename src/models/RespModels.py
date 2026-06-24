from typing import List

from pydantic import BaseModel, Field


class MacroInfo(BaseModel):
    is_macro: bool = Field(description="是否属于宏观范畴")
    macro_category: List[str] = Field(description="宏观分类列表")
    sentiment: int = Field(description="1: 积极, 0: 中性, -1: 紧缩/风险")
    ai_summary: str = Field(description="100字以内的宏观要点概括")

class StockRelation(BaseModel):
    code: str = Field(description="股票代码")
    relevance: float = Field(description="关联度 0.0-1.0")
    sentiment: int = Field(description="1: 积极, 0: 中性, -1: 负面")
    link_reason: str = Field(description="关联依据/原文片段")

class IndustryRelation(BaseModel):
    code: str = Field(description="行业代码")
    relevance: float = Field(description="关联度 0.0-1.0")
    sentiment: int = Field(description="1: 积极, 0: 中性, -1: 负面")
    link_reason: str = Field(description="关联依据/原文片段")

class FinalOutput(BaseModel):
    macro: MacroInfo
    stock_relations: List[StockRelation] = Field(default_factory=list)
    # industry_relations: List[IndustryRelation] = Field(default_factory=list)
