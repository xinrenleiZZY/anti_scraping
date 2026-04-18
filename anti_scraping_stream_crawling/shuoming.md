想改代理配置 → 修改 config.py

想改请求头策略 → 修改 headers_manager.py

想改重试逻辑 → 修改 retry_handler.py

想添加验证码服务 → 修改 captcha_solver.py


Amazon 定位逻辑：

IP + Cookie + Address API

下一步就是：

✅ 多ZIP轮换（不同州价格）
✅ IP + ZIP 绑定
✅ 防503策略
✅ 批量并发
👉 多ZIP轮换（纽约/加州/德州价格对比）
👉 IP + ZIP 强绑定策略
👉 自动判断是否被风控
👉 并发调度系统

页面解析逻辑（专业 👍）：

按 Amazon DOM 做了分类：

类型	判断方式
自然商品	有 asin + 非 sponsored
SP广告	sponsored 标签
SB广告	AdHolder
SB视频	video 标签
标题行	无 asin

| 技术点            | 影响    |
| -------------- | ----- |
| Cookie 写入      | ⭐⭐⭐⭐  |
| glow API       | ⭐⭐⭐⭐⭐ |
| fallback retry | ⭐⭐⭐   |
| referer正确      | ⭐⭐⭐⭐  |
| session预热      | ⭐⭐⭐   |
| header一致性      | ⭐⭐⭐⭐⭐ |
