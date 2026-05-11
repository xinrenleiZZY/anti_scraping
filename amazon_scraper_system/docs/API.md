# Amazon Scraper System API 文档

> 基础地址: `http://localhost:8888`

---

## 系统

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 存活检查 |
| GET | `/health` | 健康检查 |

---

## 数据查询 `/api`

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/results` | `keyword`, `keywords`, `asin`, `ad_type`, `date_from`, `date_to`, `page`, `limit`, `tags`, `festival`, `festival_type`, `hot_season`, `user_id` | 查询爬取结果 |
| GET | `/tasks` | `status`, `keyword`, `page`, `limit` | 查询任务列表 |
| GET | `/tasks/{task_id}` | — | 任务详情 |
| GET | `/stats` | — | 统计数据（关键词数、总商品等） |
| GET | `/asins` | `keyword` | 不重复 ASIN 列表 |
| GET | `/results/export` | `keyword`, `asin`, `ad_type`, `tags`, `festival`, `festival_type`, `hot_season` | 导出 CSV |
| GET | `/results/asin-analysis` | `asin`(必填), `days`, `keywords` | ASIN 分析（排名趋势、价格变化） |

---

## 爬取控制 `/api`

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/tasks/running` | — | 获取正在运行的任务 |
| POST | `/scrape` | `?keyword=xxx&pages=3` | 启动爬取 |
| POST | `/scrape/daily` | — | 触发每日任务 |
| POST | `/scrape/weekly` | — | 触发每周任务 |
| POST | `/tasks/{task_id}/stop` | Header: `X-Password: HZX123456` | 终止单任务 |
| POST | `/tasks/stop-all` | Header: `X-Password: HZX123456` | 终止全部任务 |
| GET | `/schedule/jobs` | — | 查询所有定时任务 |
| POST | `/schedule/jobs` | Body: `{"name":"","cron":"","keywords":[],"pages":null,"enabled":true}` | 创建定时任务 |
| PUT | `/schedule/jobs/{job_id}` | Body: 同创建 | 更新定时任务 |
| DELETE | `/schedule/jobs/{job_id}` | — | 删除定时任务 |
| POST | `/schedule/reload` | — | 重新加载定时任务 |
| GET | `/schedule/jobs/{job_id}/runs` | — | 任务运行记录 |
| POST | `/schedule/jobs/{job_id}/run-record` | `?status=success&note=xxx` | 记录任务运行 |

---

## 关键词管理 `/api`

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/keywords` | — | 获取关键词列表 |
| POST | `/keywords` | `?keyword=xxx` | 添加关键词 |
| DELETE | `/keywords` | `?keyword=xxx` | 删除关键词 |
| PUT | `/keywords` | Body: `["kw1","kw2"]` | 批量更新关键词 |
| GET | `/keywords/{keyword}/tags` | — | 获取标签 |
| PUT | `/keywords/{keyword}/tags` | Body: `["标签1","标签2"]` | 更新标签 |
| GET | `/keywords/{keyword}/festival` | — | 获取节日 |
| PUT | `/keywords/{keyword}/festival` | Body: `"圣诞节"` | 更新节日 |
| GET | `/keywords/{keyword}/festival-type` | — | 获取大/小节日 |
| PUT | `/keywords/{keyword}/festival-type` | Body: `"大节日"` | 更新大/小节日 |
| GET | `/keywords/{keyword}/hot-season` | — | 获取热卖期 |
| PUT | `/keywords/{keyword}/hot-season` | Body: `"高峰期"` | 更新热卖期 |
| GET | `/keywords/tags` | `?keyword=xxx` | 获取标签（Query 版） |
| PUT | `/keywords/tags` | `?keyword=xxx` + Body: `["标签"]` | 更新标签（Query 版） |
| GET | `/keywords/festival` | `?keyword=xxx` | 获取节日（Query 版） |
| PUT | `/keywords/festival` | `?keyword=xxx` + Body: `"xxx"` | 更新节日（Query 版） |
| GET | `/keywords/festival-type` | `?keyword=xxx` | 获取类型（Query 版） |
| PUT | `/keywords/festival-type` | `?keyword=xxx` + Body: `"xxx"` | 更新类型（Query 版） |
| GET | `/keywords/hot-season` | `?keyword=xxx` | 获取热卖期（Query 版） |
| PUT | `/keywords/hot-season` | `?keyword=xxx` + Body: `"xxx"` | 更新热卖期（Query 版） |
| POST | `/keywords/import-with-user` | Excel 文件上传 | 批量导入关键词+人员 |

---

## 人员管理 `/api`

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/users` | — | 获取人员列表 |
| POST | `/users` | Body: `{"name":"张三"}` | 创建人员 |
| PUT | `/users/{user_id}` | Body: `{"name":"新名称"}` | 修改人员名称 |
| DELETE | `/users/{user_id}` | — | 删除人员 |
| POST | `/users/{user_id}/keywords` | Body: `{"keyword":"xxx"}` | 给人员分配关键词 |
| DELETE | `/users/{user_id}/keywords` | `?keyword=xxx` | 移除人员关键词 |

---

## ASIN 监控 `/api`

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/asin-monitor/tasks` | — | 查询所有监控任务 |
| POST | `/asin-monitor/tasks` | Body: `{"asin":"B0xxx","monitor_name":"张三","rank_types":["organic_rank","ad_rank_sp"],"interval_hours":4,"days":30}` | 创建监控任务 |
| PUT | `/asin-monitor/tasks/{task_id}` | Body: 同创建（部分字段） | 更新监控任务 |
| DELETE | `/asin-monitor/tasks/{task_id}` | — | 删除监控任务 |
| POST | `/asin-monitor/tasks/{task_id}/run` | — | 立即执行一次监控 |

---

## 分布式爬取 `/api`

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| POST | `/distributed/task` | Body: `{"keyword":"xxx","pages":null,"worker_id":"worker001"}` | 创建分布式任务 |
| GET | `/distributed/pending` | `?worker_id=xxx` | 获取待处理任务 |
| GET | `/distributed/dashboard` | — | 分布式监控面板 |
| POST | `/distributed/result` | `?task_id=xxx&result_file=xxx` | Worker 提交结果 |
| POST | `/distributed/heartbeat` | Body: `{"worker_id":"xxx","ip":"x.x.x.x"}` | Worker 心跳 |

---

## 日志 `/api`

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/logs` | `?lines=500` | 获取最近日志 |

---

## 数据管控 `/api`

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| POST | `/backup/run` | — | 后台异步备份 |
| POST | `/backup/run-sync` | — | 同步备份（等完成返回） |
| GET | `/backup/status` | — | 查看备份状态 + 备份列表 |
| POST | `/recover/run` | Body: `{"targets":["all"],"source":null}` | 执行数据恢复 |
| GET | `/recover/backups` | — | 列出 NAS 上所有备份 |
| GET | `/verify` | — | 数据完整性校验 |
| POST | `/sync/run` | — | DB → JSON 双向同步 |

### 恢复目标 `targets` 可选值

| 值 | 说明 |
|------|------|
| `all` | 恢复全部 5 张表 |
| `db` | 同 `all` |
| `db_raw` | 仅 `raw_search_results` 表 |
| `db_tasks` | 仅 `scraping_tasks` 表 |
| `db_kwattrs` | 仅 `keyword_attributes` 表 |
| `db_users` | 仅 `users` + `user_keywords` 表 |
| `db_user_kw` | 仅 `user_keywords` 表 |
| `config` | 恢复配置文件到本地 |
| `data` | 恢复 `processed_data/` + `amazon_data/` 目录 |
| `logs` | 恢复日志文件 |

### 恢复请求示例

```json
// 恢复全部
{"targets": ["all"], "source": null}

// 从指定备份恢复用户
{"targets": ["db_users"], "source": "backup_20260511_120000"}

// 恢复配置+数据目录
{"targets": ["config", "data"], "source": "backup_20260511_120000"}
```
