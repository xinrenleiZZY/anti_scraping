## 项目技术总览

### 定位

亚马逊商品排名监控系统 — 关键词管理、爬取数据、ASIN分析、数据管控的全栈工具。

### 技术栈

| 层级         | 技术                      |                 版本/说明                  |
| ------------ | ------------------------- | :----------------------------------------: |
| **后端框架** | FastAPI (Python)          |                   3.11+                    |
| **数据库**   | PostgreSQL                |              15，64GB内存调优              |
| **前端**     | HTML + CSS + JS           |           Bootstrap 5.1，纯静态            |
| **反向代理** | Nginx（双层）             | Windows Nginx(:8880) → Docker Nginx(:8881) |
| **爬虫引擎** | curl_cffi + BeautifulSoup |               模拟浏览器指纹               |
| **容器化**   | Docker Compose            |  3 个容器：postgres / backend / frontend   |
| **任务调度** | APScheduler               |                Cron定时爬取                |
| **推送**     | 飞书机器人                |              ASIN监控报告推送              |

### 数据流

```
亚马逊搜索结果
    ↓ [爬虫 curl_cffi]
原始 JSON/CSV → amazon_data/
    ↓ [dataprocess.py]
预处理数据 → processed_data/
    ↓ [data_processor.py清洗入库]
PostgreSQL ←→ scraper_config.json（关键词属性双向同步）
    ↓ [data_control/]
备份 → data_control/backups/ → NAS
```

### 核心功能

- **关键词管理**：增删改查 + 标签/节日/热卖期属性 + 按人分配 + 批量导入导出
- **爬取控制**：单次/每日/每周定时爬取，Cron配置管理
- **数据查询**：10+维度筛选，ASIN分析，CSV导出
- **ASIN重点监控**：设定ASIN+排名类型，定时检测异常，飞书推送报告
- **数据管控**：DB↔JSON同步，全量备份/恢复/校验
- **访客记录**：IP自动识别，PV统计

### 部署架构

```
局域网设备
    │ :8880（Windows Nginx，记录真实IP）
    ▼
Windows Nginx → Docker Nginx(:8881) → FastAPI(:8888) → PostgreSQL(:5432)
```

### 关键数据规模

| 数据         |        规模         |
| ------------ | :-----------------: |
| 商品记录     |      ~8.2万条       |
| 爬虫原始数据 | ~924 MB / 8655 文件 |
| 预处理数据   | ~632 MB / 2599 文件 |
| 关键词       |        按需         |
| 人员         |        按需         |
