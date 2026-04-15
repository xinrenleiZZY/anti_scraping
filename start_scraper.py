# start_scraper.py - 放在 E:\ZY2026\运营-准生产级爬虫\ 目录下

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接运行爬虫
from anti_scraping.run_amazon_scraper import main

if __name__ == "__main__":
    main()

