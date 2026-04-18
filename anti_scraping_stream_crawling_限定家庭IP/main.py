# main.py - 完整工作流
if __name__ == "__main__":
    # 初始化会话（带代理）
    session_mgr = SessionManager(proxy="http://127.0.0.1:7890")
    
    # 创建协调器
    coordinator = AmazonScrapingCoordinator(session_mgr)
    
    # 任务1: 分析整个类目
    coordinator.analyze_category(
        "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics",
        max_depth=3
    )
    
    # 任务2: 搜索关键词并获取详情
    search_results = coordinator.search_spider.scrape_search("yoga mat", pages=5)
    asins = [item.asin for item in search_results if item.asin]
    coordinator._batch_get_details(asins)