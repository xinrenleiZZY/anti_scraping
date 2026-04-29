-- 单表存储所有数据
CREATE TABLE amazon_products (
    -- ========== 主键和基础信息 ==========
    id BIGSERIAL PRIMARY KEY,
    search_id VARCHAR(100) NOT NULL,           -- 搜索会话ID
    keyword VARCHAR(200) NOT NULL,              -- 搜索关键词
    search_page INT NOT NULL,                   -- 页码
    data_index INT NOT NULL,                    -- 页面位置索引
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 爬取时间
    
    -- ========== 商品核心信息 ==========
    asin VARCHAR(20),                          -- Amazon标准识别号
    title TEXT,                                 -- 产品标题
    url TEXT,                                   -- 产品链接
    brand_name VARCHAR(200),                    -- 品牌名称
    
    -- ========== 价格信息 ==========
    price_current VARCHAR(20),                  -- 当前价格（保留原始格式 $19.99）
    price_current_numeric NUMERIC(10,2),        -- 当前价格（数值，便于计算）
    price_list VARCHAR(20),                     -- 原价/划线价
    price_list_numeric NUMERIC(10,2),           -- 原价数值
    currency VARCHAR(3) DEFAULT 'USD',          -- 货币类型
    
    -- ========== 评分信息 ==========
    rating_stars NUMERIC(3,2),                  -- 评分星级
    rating_count INT,                           -- 评论数量
    
    -- ========== 排名和广告类型 ==========
    ad_type VARCHAR(20) NOT NULL,               -- 'Organic', 'SP', 'SB', 'SB_Video', 'Title'
    ad_rank INT,                                -- 广告排名
    organic_rank INT,                           -- 自然排名
    
    -- ========== 商品属性 ==========
    is_prime BOOLEAN DEFAULT FALSE,             -- 是否Prime
    has_video BOOLEAN DEFAULT FALSE,            -- 是否有视频
    
    -- ========== 图片链接 ==========
    image_small TEXT,                           -- 小图URL
    image_large TEXT,                           -- 大图URL
    
    -- ========== SB广告特有字段 ==========
    -- 方式1: JSONB存储（推荐）
    inner_products JSONB,                       -- SB广告内的商品列表
    inner_products_count INT,                   -- 内部商品数量（冗余字段，方便查询）
    
    -- 方式2: 文本存储（如果不需查询JSON内容）
    -- inner_products_text TEXT,                -- JSON字符串形式
    
    -- ========== 扩展字段 ==========
    extra_data JSONB,                           -- 其他扩展数据
    notes TEXT,                                 -- 备注信息
    
    -- ========== 创建索引 ==========
    INDEX idx_asin (asin),
    INDEX idx_keyword (keyword),
    INDEX idx_keyword_page (keyword, search_page),
    INDEX idx_ad_type (ad_type),
    INDEX idx_ad_rank (ad_rank),
    INDEX idx_organic_rank (organic_rank),
    INDEX idx_scraped_at (scraped_at),
    INDEX idx_price (price_current_numeric),
    INDEX idx_rating (rating_stars),
    INDEX idx_brand (brand_name),
    INDEX idx_search_id (search_id),
    
    -- GIN索引用于JSONB查询
    INDEX idx_inner_products_gin USING GIN (inner_products),
    
    -- 复合索引（常用查询组合）
    INDEX idx_keyword_adtype (keyword, ad_type),
    INDEX idx_keyword_organic (keyword, organic_rank) WHERE ad_type = 'Organic',
    INDEX idx_keyword_sp (keyword, ad_rank) WHERE ad_type = 'SP'
);

-- 添加注释
COMMENT ON TABLE amazon_products IS '亚马逊搜索结果主表（单表设计）';
COMMENT ON COLUMN amazon_products.inner_products IS 'SB广告内部商品列表，JSONB格式：[{"position":1,"asin":"B001","title":"xxx","price":"$19.99"}]';
COMMENT ON COLUMN amazon_products.ad_type IS '广告类型：Organic(自然)/SP(商品广告)/SB(品牌广告)/SB_Video(视频广告)/Title(标题行)';