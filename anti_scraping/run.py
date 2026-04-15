# start_original_scraper.py - 放在项目根目录

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接运行原始爬虫（假设你的原始文件在根目录叫 run_amazon_scraper.py）
# 如果你的原始文件在其他位置，修改路径
exec(open("run_amazon_scraper.py", encoding="utf-8").read())