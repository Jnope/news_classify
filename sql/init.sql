CREATE TABLE IF NOT EXIST NEWS_AI_INFO (
    news_id          VARCHAR(64)   NOT NULL COMMENT '原始新闻唯一ID',
    source_type      INT           NOT NULL COMMENT '来源: 1-财联社内部, 2-全市场',
    ai_summary       TEXT          NOT NULL COMMENT '全局摘要',
    sentiment        INT           NOT NULL COMMENT '全文整体情感: 1-正面/积极/宽松, 0-中性, -1-负面/紧缩/风险',
--    macro_category   VARCHAR(50)   DEFAULT NULL COMMENT '宏观分类: 如货币政策/财政政策/地缘政治/宏观经济数据',
    model_version    VARCHAR(32)   NOT NULL COMMENT '处理该条的AI模型版本号',
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'AI处理完成时间',
    PRIMARY KEY (news_id),
    INDEX IDX_SOURCE_CREATED (source_type, created_at DESC),
--    INDEX IDX_CATEGORY_CREATED (macro_category, created_at DESC)
    INDEX IDX_CREATED (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻AI分析结果';

CREATE TABLE IF NOT EXIST NEWS_AI_CATEGORY (
    news_id          VARCHAR(64)   NOT NULL COMMENT '原始新闻唯一ID',
    macro_category   VARCHAR(20)   DEFAULT NULL COMMENT '货币政策与流动性、财政与产业政策、宏观经济数据、地缘政治与国际宏观、跨行业监管与合规、资本市场顶层设计、突发公共事件与自然灾害、其他',
    PRIMARY KEY (news_id),
    INDEX IDX_CATEGORY (macro_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻AI分类';

CREATE TABLE IF NOT EXIST NEWS_STOCK_RELATION (
    id              BIGINT        NOT NULL AUTO_INCREMENT,
    news_id         VARCHAR(64)   NOT NULL COMMENT '新闻id',
    stock_code      VARCHAR(20)   NOT NULL COMMENT '标准股票代码(如 600519.SH)',
    stock_name      VARCHAR(50)   NOT NULL COMMENT '冗余股票名称',
    relevance_score DECIMAL(4,3)  NOT NULL COMMENT '该股与本文关联置信度(0.000~1.000)',
    sentiment       INT       NOT NULL COMMENT '该股专属情感：1-正面, 0-中性, -1-负面',
    link_reason     VARCHAR(255)  DEFAULT NULL COMMENT '关联依据/原文片段',
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY UNIQ_NEWS_STOCK (news_id, stock_code),
    INDEX IDX_STOCK_CREATED (stock_code, created_at DESC),
    INDEX IDX_NEWS (news_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻-股票关联关系';

--CREATE TABLE IF NOT EXIST NEWS_INDUSTRY_RELATION (
--    id              BIGINT        NOT NULL AUTO_INCREMENT,
--    news_id         VARCHAR(64)   NOT NULL COMMENT '新闻id',
--    industry_l1_code   VARCHAR(100)   NOT NULL COMMENT '申万一级行业代码',
--    industry_l1_name   VARCHAR(200)   NOT NULL COMMENT '冗余一级行业名称',
--    industry_l2_code   VARCHAR(100)   NOT NULL COMMENT '申万二级行业代码',
--    industry_l2_name   VARCHAR(200)   NOT NULL COMMENT '冗余二级行业名称',
--    industry_l3_code   VARCHAR(100)   NOT NULL COMMENT '申万三级行业代码',
--    industry_l3_name   VARCHAR(200)   NOT NULL COMMENT '冗余三级行业名称',
--    relevance_score DECIMAL(4,3)  NOT NULL COMMENT '行业与本文关联置信度',
--    link_reason     VARCHAR(255)  DEFAULT NULL COMMENT '关联依据',
--    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
--    PRIMARY KEY (id),
--    UNIQUE KEY UNIQ_NEWS_INDUSTRY (news_id, industry_code),
--    INDEX IDX_INDUSTRY_1_CREATED (industry_code, created_at DESC),
--    INDEX IDX_INDUSTRY_2_CREATED (industry_code, created_at DESC),
--    INDEX IDX_INDUSTRY_3_CREATED (industry_code, created_at DESC),
--    INDEX IDX_NEWS (news_id)
--) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻-行业关联关系;
