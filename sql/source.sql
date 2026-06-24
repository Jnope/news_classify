CREATE TABLE `news_realtime` (
  `item_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '文本id',
  `title` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '标题',
  `content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '文本内容',
  `publish_time` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '发布时间',
  `source` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '来源',
  `insert_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '插入时间',
  `source_url` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'url链接',
  PRIMARY KEY (`item_id`),
  KEY `idx_publish_time` (`publish_time`),
  KEY `idx_source` (`source`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='全市场新闻表';

CREATE TABLE `telegram_realtime` (
  `id` bigint NOT NULL,
  `title` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `source` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `source_url` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `publish_time` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `job_id` int DEFAULT NULL,
  `user_id` int DEFAULT NULL,
  `insert_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '插入时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='财联社内部新闻表';

CREATE TABLE `meta_data.stock_code`(
  `id` int DEFAULT NULL COMMENT ' ',
  `code` string DEFAULT NULL COMMENT ' ',
  `name` string DEFAULT NULL COMMENT ' ',
  `short_name` string DEFAULT NULL COMMENT ' ',
  `category` string DEFAULT NULL COMMENT ' ',
  `exchange` string DEFAULT NULL COMMENT ' ',
  `start_date` string DEFAULT NULL COMMENT ' ',
  `end_date` string DEFAULT NULL COMMENT ' ',
  `company_id` int DEFAULT NULL COMMENT ' ',
  `company_name` string DEFAULT NULL COMMENT ' ',
  `ipo_shares` double DEFAULT NULL COMMENT ' ',
  `book_price` double DEFAULT NULL COMMENT ' ',
  `par_value` double DEFAULT NULL COMMENT ' ',
  `state_id` int DEFAULT NULL COMMENT ' ',
  `state` string DEFAULT NULL COMMENT ' ',
  `type` string DEFAULT NULL COMMENT ' ',
  `fake_datetime` timestamp DEFAULT NULL COMMENT ' '
)
ROW FORMAT SERDE
  'io.transwarp.timelyre.TimeLyreSerde'
STORED BY
  'io.transwarp.timelyre.TimeLyreStorageHandler'
WITH SERDEPROPERTIES (
  'serialization.format'='1')
LOCATION
  'hdfs://nameservice1/quark2/user/hive/warehouse/meta_data.db/admin/stock_code'

TBLPROPERTIES (
  'timelyre.timestamp.col'='fake_datetime',
  'timelyre.shiva.data.types'='Integer,Tag,String,String,String,String,String,String,Integer,String,Float,Float,Float,Integer,String,String,Timestamp',
  'insert.version'='v3',
  'timelyre.shiva.tablename'='meta_data.stock_code_20251209170415302',
  'epoch.engine.enabled'='true',
  'shard.group.duration.seconds'='31536000',
  'timelyre.shiva.cols'='id,code,name,short_name,category,exchange,start_date,end_date,company_id,company_name,ipo_shares,book_price,par_value,state_id,state,type,fake_datetime',
  'timelyre.tag.cols'='code',
  'timelyre.columns.mapping'='{"end_date":"end_date","par_value":"par_value","code":"code","company_id":"company_id","fake_datetime":"fake_datetime","ipo_shares":"ipo_shares","type":"type","book_price":"book_price","company_name":"company_name","name":"name","short_name":"short_name","exchange":"exchange","id":"id","state_id":"state_id","state":"state","category":"category","start_date":"start_date"}')

CREATE TABLE `meta_data.sw_industry`(
  `code` string DEFAULT NULL COMMENT ' ',
  `datetime` timestamp DEFAULT NULL COMMENT ' ',
  `sw_l1_code` string DEFAULT NULL COMMENT ' ',
  `sw_l1_name` string DEFAULT NULL COMMENT ' ',
  `sw_l2_code` string DEFAULT NULL COMMENT ' ',
  `sw_l2_name` string DEFAULT NULL COMMENT ' ',
  `sw_l3_code` string DEFAULT NULL COMMENT ' ',
  `sw_l3_name` string DEFAULT NULL COMMENT ' '
)
ROW FORMAT SERDE
  'io.transwarp.timelyre.TimeLyreSerde'
STORED BY
  'io.transwarp.timelyre.TimeLyreStorageHandler'
WITH SERDEPROPERTIES (
  'serialization.format'='1')
LOCATION
  'hdfs://nameservice1/quark2/user/hive/warehouse/meta_data.db/xwq_test/sw_industry'

TBLPROPERTIES (
  'timelyre.timestamp.col'='datetime',
  'timelyre.shiva.data.types'='Tag,Timestamp,String,String,String,String,String,String',
  'insert.version'='v3',
  'timelyre.shiva.tablename'='meta_data.sw_industry_20251124162153919',
  'epoch.engine.enabled'='true',
  'shard.group.duration.seconds'='63072000',
  'timelyre.shiva.cols'='code,datetime,sw_l1_code,sw_l1_name,sw_l2_code,sw_l2_name,sw_l3_code,sw_l3_name',
  'timelyre.tag.cols'='code',
  'timelyre.columns.mapping'='{"datetime":"datetime","sw_l2_code":"sw_l2_code","code":"code","sw_l1_name":"sw_l1_name","sw_l3_code":"sw_l3_code","sw_l2_name":"sw_l2_name","sw_l1_code":"sw_l1_code","sw_l3_name":"sw_l3_name"}')
