# Amazon Scraper System

亚马逊商品数据爬取系统 - 支持关键词搜索、数据采集、可视化展示、数据管控的全栈解决方案。

## 🏗️ 系统架构

```
amazon_scraper_system/
│
├── backend/                          # 后端服务（FastAPI）
│   ├── app/
│   │   ├── main.py                   # FastAPI入口，注册路由，启动服务
│   │   ├── config.py                 # 配置管理（读取.env环境变量）
│   │   ├── database.py               # PostgreSQL连接池、会话管理
│   │   ├── models.py                 # SQLAlchemy数据表定义（ORM映射）
│   │   ├── schemas.py                # Pydantic模型（API请求/响应格式）
│   │   ├── crud.py                   # 数据库操作函数
│   │   │
│   │   ├── api/                      # API路由
│   │   │   ├── data.py               # 数据查询API（产品列表、分析报告）
│   │   │   ├── scraping.py           # 爬取任务API（启动爬取、Cron管理）
│   │   │   ├── keywords.py           # 关键词管理API（增删改查+属性）
│   │   │   ├── users.py              # 人员管理API
│   │   │   ├── asin_monitor.py       # ASIN重点监控API（飞书推送）
│   │   │   ├── distributed.py        # 分布式爬取API
│   │   │   ├── data_control.py       # 数据管控API（备份/恢复/校验）
│   │   │   ├── visitors.py           # 访客记录API（追踪/统计）
│   │   │   ├── logs.py              # 日志查询API
│   │   │
│   │   ├── scraper/                  # 爬虫模块
│   │   │   ├── auto_amazon_scraper.py  # 核心爬虫
│   │   │   ├── dataprocess.py        # 数据预处理
│   │   │   ├── pipeline.py           # 完整流程编排（爬取→处理→存储）
│   │   │   ├── scraper.py            # curl_cffi + BeautifulSoup实现
│   │   │   ├── headers_manager.py    # 请求头管理
│   │   │   ├── anti_scraping_config.py  # 反爬配置
│   │   │   ├── data_processor.py     # 数据处理器（清洗入库）
│   │   │   ├── schedule_config.py    # 定时任务配置
│   │   │   ├── scraper_config.json   # 关键词配置（关键词+标签/节日/热卖期）
│   │   │   ├── schedule_config.json  # 定时任务配置
│   │   │   ├── amazon_data/          # 爬虫原始数据（JSON/CSV）
│   │   │   └── processed_data/       # 预处理后数据（_processed.json）
│   │   │
│   │   └── distributed/              # 分布式任务模块
│   │       └── task_manager.py       # 分布式任务调度管理
│   │
│   ├── requirements.txt              # Python依赖
│   ├── Dockerfile                    # 后端容器构建
│   └── asin_monitor_config.json      # ASIN监控配置
│
├── frontend/                         # 前端界面（Nginx静态文件）
│   ├── index.html                    # 仪表盘首页
│   ├── keywords.html                 # 关键词管理（完整版）
│   ├── keywords_overview.html        # 关键词总览（精简版）
│   ├── data.html                     # 数据查询
│   ├── data_danxuan.html             # 数据查询（单选项版）
│   ├── data_独立测试.html             # 数据查询（独立测试版）
│   ├── scrape.html                   # 爬取控制
│   ├── tasks.html                    # 任务监控
│   ├── users.html                    # 人员管理
│   ├── asin_monitor.html             # ASIN监控
│   ├── visitors.html                 # 访客记录
│   ├── dashboard_asin.html           # ASIN分析大屏
│   ├── dashboard_asin_enhanced.html  # ASIN分析大屏（增强版）
│   ├── hzx.html                      # 测试页
│   ├── 测试模版页面（忽略）.html
│   ├── data表格样式1.html
│   ├── data copy.html / data copy 2.html / data copy 3.html / data copy 4.html
│   ├── css/
│   │   └── style.css                # 全局样式
│   ├── js/
│   │   ├── common.js                 # 公共函数（API封装）
│   │   ├── sidebar.js                # 侧边栏
│   │   ├── dashboard.js              # 仪表盘
│   │   ├── keywords.js               # 关键词管理逻辑
│   │   ├── keywords_overview.js      # 关键词总览逻辑
│   │   ├── data.js                   # 数据查询逻辑
│   │   ├── scrape.js                 # 爬取控制逻辑
│   │   ├── tasks.js                  # 任务监控逻辑
│   │   ├── users.js                  # 人员管理逻辑
│   │   ├── asin_monitor.js           # ASIN监控逻辑
│   │   ├── visitors.js               # 访客记录逻辑
│   │   ├── dashboard_asin.js         # ASIN分析大屏
│   │   ├── dashboard_asin_enhanced.js # 增强ASIN分析
│   │   ├── app.js                    # 旧版
│   │   ├── mascot.js / particles.js  # 特效
│   ├── nginx.conf                    # Nginx配置
│   └── Dockerfile                    # 前端容器构建
│
├── data_control/                     # 数据管控模块
│   ├── config.py                     # 公共路径配置
│   ├── sync.py                       # DB ↔ JSON 双向同步
│   ├── backup.py                     # 全量备份脚本
│   ├── recover.py                    # 数据恢复脚本
│   ├── verify.py                     # 数据完整性校验
│   ├── api.py                        # 数据管控API路由
│   ├── sync_to_nas.ps1               # 备份同步到NAS脚本
│   ├── users.json                    # 人员表JSON备份
│   ├── user_keywords.json            # 人员关键词关联JSON备份
│   └── backups/                      # 本地备份目录
│
├── docs/
│   ├── API.md                        # 完整API文档
│   └── files_structure.txt           # 文件结构清单
│
├── docker-compose.yml                # 主编排（postgres + backend + frontend）
├── docker-compose.worker.yml         # Worker编排
├── .env.example                      # 环境变量模板
├── .env.worker.example               # Worker环境变量模板
├── init.sql                          # 数据库初始化SQL（5张表）
├── start.bat                         # Windows快捷启动
├── start.sh                          # Linux快捷启动
├── recover_data.py                   # 旧版恢复脚本
├── README.md                         # 本文件
└── 文件解析.md / 项目总览.md / 调度总览.md
```

## 🚀 快速启动

### 前置要求

- Docker & Docker Compose
- Python 3.11+

### 使用 Docker Compose 启动

```bash
docker-compose up -d
```

### 网络架构

```
局域网访客 → Windows Nginx (:8880) → 记录真实IP → Docker Nginx (:8881) → FastAPI
```

| 服务                  | 端口 | 访问地址              | 说明                            |
| --------------------- | :--: | --------------------- | ------------------------------- |
| 前端（Windows Nginx） | 8880 | http://localhost:8880 | ✅ 推荐入口，记录访客真实IP     |
| 前端（Docker直连）    | 8881 | http://localhost:8881 | ⚠️ 不推荐，只能看到Docker内网IP |
| 后端API               | 8888 | http://localhost:8888 | 直接调API用                     |
| PostgreSQL            | 5200 | Navicat连接           | 数据库直连                      |

### 数据库连接（Navicat）

| 配置项 | 值             |
| ------ | -------------- |
| 主机   | localhost      |
| 端口   | 5200           |
| 数据库 | amazon_scraper |
| 用户   | admin          |
| 密码   | 123456         |

## 💾 数据库表结构

| 表                   | 说明                                       | 备份方式                                  |
| -------------------- | ------------------------------------------ | ----------------------------------------- |
| `raw_search_results` | 商品数据（ASIN、价格、排名、标题、评分等） | ✅ 可从 processed_data/ 恢复              |
| `scraping_tasks`     | 爬取任务记录                               | ❌ 无备份                                 |
| `users`              | 人员名单                                   | ✅ 同步到 data_control/users.json         |
| `user_keywords`      | 人员-关键词关联                            | ✅ 同步到 data_control/user_keywords.json |
| `keyword_attributes` | 关键词属性（标签/节日/热卖期）             | ✅ 同步到 scraper_config.json             |
| `visitor_logs`       | 访客记录（IP/页面/时间/UA/来源）           | ❌ 无备份                                 |

## 🔌 API 接口速览

完整文档：`docs/API.md`

### 数据查询

| 方法 | 路径                         | 说明                        |
| ---- | ---------------------------- | --------------------------- |
| GET  | `/api/results`               | 查询数据（支持10+筛选参数） |
| GET  | `/api/tasks`                 | 任务列表                    |
| GET  | `/api/stats`                 | 统计数据                    |
| GET  | `/api/asins`                 | ASIN列表                    |
| GET  | `/api/results/export`        | 导出CSV                     |
| GET  | `/api/results/asin-analysis` | ASIN分析                    |

### 爬取控制

| 方法                | 路径                   | 说明                   |
| ------------------- | ---------------------- | ---------------------- |
| POST                | `/api/scrape`          | 启动爬取               |
| POST                | `/api/scrape/daily`    | 每日任务               |
| POST                | `/api/scrape/weekly`   | 每周任务               |
| GET                 | `/api/tasks/running`   | 运行中任务             |
| POST                | `/api/tasks/{id}/stop` | 停止任务（X-Password） |
| GET/POST/PUT/DELETE | `/api/schedule/jobs*`  | Cron定时任务管理       |

### 关键词管理

| 方法                | 路径                               | 说明          |
| ------------------- | ---------------------------------- | ------------- |
| GET/POST/DELETE/PUT | `/api/keywords`                    | 关键词CRUD    |
| GET/PUT             | `/api/keywords/{kw}/tags`          | 标签管理      |
| GET/PUT             | `/api/keywords/{kw}/festival`      | 节日管理      |
| GET/PUT             | `/api/keywords/{kw}/festival-type` | 节日类型      |
| GET/PUT             | `/api/keywords/{kw}/hot-season`    | 热卖期        |
| POST                | `/api/keywords/import-with-user`   | 批量导入Excel |

### 人员管理

| 方法                | 路径                       | 说明            |
| ------------------- | -------------------------- | --------------- |
| GET/POST/PUT/DELETE | `/api/users`               | 人员CRUD        |
| POST/DELETE         | `/api/users/{id}/keywords` | 分配/移除关键词 |

### ASIN监控

| 方法                | 路径                               | 说明         |
| ------------------- | ---------------------------------- | ------------ |
| GET/POST/PUT/DELETE | `/api/asin-monitor/tasks`          | 监控任务CRUD |
| POST                | `/api/asin-monitor/tasks/{id}/run` | 立即执行     |

### 分布式爬取

| 方法     | 路径                 | 说明          |
| -------- | -------------------- | ------------- |
| POST/GET | `/api/distributed/*` | 任务分发/心跳 |

### 日志

| 方法 | 路径        | 说明     |
| ---- | ----------- | -------- |
| GET  | `/api/logs` | 获取日志 |

### 访客记录

| 方法 | 路径                  | 说明                                              |
| ---- | --------------------- | ------------------------------------------------- |
| POST | `/api/visitor/track`  | 记录页面访问（自动，页面加载时触发）              |
| GET  | `/api/visitor/stats`  | 访客统计（今日/本周/总量/热门页面TOP10/每日趋势） |
| GET  | `/api/visitor/recent` | 最近访客列表（含IP、页面、UA、来源）              |

### 数据管控

| 方法 | 路径                   | 说明                   |
| ---- | ---------------------- | ---------------------- |
| POST | `/api/backup/run`      | 后台异步备份           |
| POST | `/api/backup/run-sync` | 同步备份（等完成返回） |
| GET  | `/api/backup/status`   | 备份状态               |
| POST | `/api/recover/run`     | 执行恢复               |
| GET  | `/api/recover/backups` | 列出备份               |
| GET  | `/api/verify`          | 完整性校验             |
| POST | `/api/sync/run`        | DB → JSON同步          |

## 🧰 数据管控

### 数据流

```
前端操作 → 写DB → 自动调 sync → JSON备份文件
                                     ↓
                           backup.py → NAS/本地
                                     ↓
                           recover.py ← 灾难恢复
```

### 定时备份

- **系统内**：`POST /api/backup/run`（Docker内调用）
- **Windows**：`data_control\sync_to_nas.ps1` 复制到NAS
- **推荐**：Windows任务计划每天凌晨3点执行

### 恢复命令

```bash
python data_control/recover.py                    # 全部恢复
python data_control/recover.py db_users           # 只恢复人员
python data_control/recover.py config data        # 恢复配置+数据目录
python data_control/recover.py --list-backups     # 列出可用备份
```

## 🖥️ 前端页面

| 页面       | 地址                      | 功能                                                 |
| ---------- | ------------------------- | ---------------------------------------------------- |
| 仪表盘     | `/index.html`             | 总览统计、关键词趋势                                 |
| 关键词管理 | `/keywords.html`          | 完整关键词管理（标签/节日/负责人/批量删除/批量导出） |
| 关键词总览 | `/keywords_overview.html` | 精简版关键词管理                                     |
| 数据查询   | `/data.html`              | 商品数据查询、筛选、导出                             |
| 爬取控制   | `/scrape.html`            | 启动爬取、管理定时任务                               |
| 任务监控   | `/tasks.html`             | 查看任务状态                                         |
| 人员管理   | `/users.html`             | 人员CRUD、关键词分配                                 |
| ASIN监控   | `/asin_monitor.html`      | 重点ASIN排名监控、飞书推送                           |
| ASIN分析   | `/dashboard_asin.html`    | ASIN排名趋势大屏                                     |
| 访客记录   | `/visitors.html`          | 访客统计（今日/本周/总览/热门页面/最近访客）         |

## � 密码

| 用途                   | 密码      |
| ---------------------- | --------- |
| 终止任务（X-Password） | HZX123456 |

## 📍 Windows Nginx 管理

Windows Nginx 安装在 `C:\nginx`，用于捕获访客真实IP。

### 启动/停止

```powershell
# 启动
Start-Process -NoNewWindow -FilePath "C:\nginx\nginx.exe" -ArgumentList "-p C:\nginx"

# 停止
taskkill /f /im nginx.exe

# 重载配置
C:\nginx\nginx.exe -s reload -p C:\nginx
```

### 配置位置

- `C:\nginx\conf\nginx.conf` — 反向代理配置
- 监听 8880 端口 → 转发到 Docker Nginx 8881
- 访客通过 `http://192.168.0.193:8880` 访问即可记录真实IP
