import requests
import json
import time
import csv
from urllib.parse import unquote

# ===== 配置：从浏览器复制你的 Cookie 和 auth-token =====
AUTH_TOKEN = "7980gteAjnEK03pI+6bH5a42Mmuyi9OYeSz++dVigVyLdlRgxyogOQNZ/m//tFpCw35D5fGvrEdNJBBqaB40E7SgvffC9Fr+saunH+gYcdqVm5NU8kv+h4LuQDSWbduEdLT6ISuHU5dEIUhjTOsatJcsLK8"
COOKIE = "sajssdk_2015_cross_new_user=1; __wpkreporterwid_=85e390b0-128d-484c-8a9e-ae604d340d80; _gcl_au=1.1.1494075047.1776407104; _ga=GA1.1.41507306.1776407105; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%22900665-1%22%2C%22first_id%22%3A%2219d9a1d02b62d9-0dc81ca7b784f38-4c657b58-2073600-19d9a1d02b7134a%22%2C%22props%22%3A%7B%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTlkOWExZDAyYjYyZDktMGRjODFjYTdiNzg0ZjM4LTRjNjU3YjU4LTIwNzM2MDAtMTlkOWExZDAyYjcxMzRhIiwiJGlkZW50aXR5X2xvZ2luX2lkIjoiOTAwNjY1LTEifQ%3D%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%24identity_login_id%22%2C%22value%22%3A%22900665-1%22%7D%2C%22%24device_id%22%3A%2219d9a1d02b62d9-0dc81ca7b784f38-4c657b58-2073600-19d9a1d02b7134a%22%7D; company_id=90136117059997696; envKey=huizhixin; env_key=huizhixin; authToken=7980gteAjnEK03pI%2B6bH5a42Mmuyi9OYeSz%2B%2BdVigVyLdlRgxyogOQNZ%2Fm%2F%2FtFpCw35D5fGvrEdNJBBqaB40E7SgvffC9Fr%2BsaunH%2BgYcdqVm5NU8kv%2Bh4LuQDSWbduEdLT6ISuHU5dEIUhjTOsatJcsLK8; auth-token=7980gteAjnEK03pI%2B6bH5a42Mmuyi9OYeSz%2B%2BdVigVyLdlRgxyogOQNZ%2Fm%2F%2FtFpCw35D5fGvrEdNJBBqaB40E7SgvffC9Fr%2BsaunH%2BgYcdqVm5NU8kv%2Bh4LuQDSWbduEdLT6ISuHU5dEIUhjTOsatJcsLK8; uid=11091042; seller-auth-erp-url=https%3A%2F%2Fhuizhixin.lingxing.com%2Fapi%2Fseller%2FoauthRedirect; isNeedReset=0; isUpdatePwd=0; isLogin=true; zid=1; _ga_YG2XNMH0EE=GS2.1.s1776407104$o1$g1$t1776407385$j60$l0$h1640973912; is_sellerAuth=1; info=%7B%22uid%22%3A%2211091042%22%2C%22zid%22%3A%221%22%2C%22username%22%3A%22HZXyuting%22%2C%22siteUsername%22%3A%22%22%2C%22realname%22%3A%22%E5%BB%96%E5%96%BB%E5%A9%B7%22%2C%22mobile%22%3A%22%22%2C%22nationCode%22%3A%2286%22%2C%22adminNationCode%22%3A%22%22%2C%22mealInfo%22%3A%7B%22recharge_num%22%3A0%7D%2C%22loginGuide%22%3Afalse%2C%22loginEnv%22%3A1%2C%22isPartner%22%3A0%2C%22email%22%3A%22%22%2C%22deviceRecords%22%3A%5B%5D%2C%22sysSubAdminFlag%22%3A0%2C%22editFlag%22%3A1%2C%22isDisableResetPwd%22%3A0%2C%22is_mobile_verified%22%3A0%2C%22is_master%22%3A0%2C%22is_email_verified%22%3A0%2C%22hide_init_guide%22%3A0%2C%22mp_hide_init_guide%22%3A0%2C%22has_bind_oauth_center%22%3A0%2C%22has_bind_jst%22%3A0%2C%22feature_info%22%3A%7B%7D%2C%22customer_id%22%3A%22900665%22%2C%22show_zid%22%3A%22900665%22%2C%22available_env%22%3A%5B%22amazon%22%2C%22multi%22%5D%2C%22api_info%22%3A%5B%5D%7D; sensor-distinace-id=900665-1; token=7980gteAjnEK03pI%2B6bH5a42Mmuyi9OYeSz%2B%2BdVigVyLdlRgxyogOQNZ%2Fm%2F%2FtFpCw35D5fGvrEdNJBBqaB40E7SgvffC9Fr%2BsaunH%2BgYcdqVm5NU8kv%2Bh4LuQDSWbduEdLT6ISuHU5dEIUhjTOsatJcsLK8; udesk_info_90136117059997696=%7B%22level%22%3A%22B%22%2C%22klevel%22%3A%22%E5%90%A6%22%2C%22company_id%22%3A%2290136117059997696%22%2C%22customer_id%22%3A%22900665%22%2C%22cs_group%22%3A%22CSG2-005%22%7D; _ga_89WN60ZK2E=GS2.1.s1776407485$o1$g1$t1776407929$j60$l0$h0"

BASE_URL = "https://huizhixin.lingxing.com/api/product/lists"
PAGE_SIZE = 500

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9",
    "ak-client-type": "web",
    "ak-origin": "https://huizhixin.lingxing.com",
    "auth-token": AUTH_TOKEN,
    "content-type": "application/json;charset=UTF-8",
    "origin": "https://huizhixin.lingxing.com",
    "referer": "https://huizhixin.lingxing.com/erp/productManage",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0",
    "x-ak-company-id": "90136117059997696",
    "x-ak-env-key": "huizhixin",
    "x-ak-language": "zh",
    "x-ak-platform": "1",
    "x-ak-request-source": "erp",
    "x-ak-uid": "11091042",
    "x-ak-version": "3.8.1.3.0.074",
    "x-ak-zid": "1",
    "cookie": COOKIE,
}


def fetch_page(offset: int) -> dict:
    payload = {
        "search_field_time": "create_time",
        "product_creator_uid": [130],
        "product_developer_uid": [],
        "permission_uid": [],
        "cg_opt_uid": [],
        "supplier_id": [],
        "sort_field": "create_time",
        "sort_type": "desc",
        "search_field": "sku",
        "attribute": [],
        "status": [],
        "open_status": "",
        "gtag_ids": "",
        "senior_search_list": "[]",
        "single_product_id": [],
        "is_matched_listing": "",
        "is_matched_alibaba": "",
        "relation_aux": "",
        "is_have_pic": "",
        "cg_package": "",
        "cg_product_gross_weight": {"left": "", "right": "", "symbol": "gt"},
        "cg_price": {"left": "", "right": "", "symbol": "gt"},
        "cg_transport_costs": {"left": "", "right": "", "symbol": "gt", "country_code": "US"},
        "offset": offset,
        "is_combo": "",
        "length": PAGE_SIZE,
        "is_aux": 0,
        "product_type": [1, 2],
        "selected_product_ids": "",
        "req_time_sequence": f"/api/product/lists$$1",
    }
    resp = requests.post(BASE_URL, headers=HEADERS, json=payload, timeout=30)
    print(f"HTTP {resp.status_code}")
    print(f"响应前200字符: {resp.text[:200]}")
    resp.raise_for_status()
    return resp.json()


def scrape_all():
    all_products = []

    # 第一页，获取总数
    data = fetch_page(0)
    total = data.get("total", 0)
    all_products.extend(data.get("list", []))
    print(f"总计 {total} 条，已获取 {len(all_products)} 条")

    offset = PAGE_SIZE
    while offset < total:
        time.sleep(0.5)
        data = fetch_page(offset)
        batch = data.get("list", [])
        if not batch:
            break
        all_products.extend(batch)
        print(f"已获取 {len(all_products)}/{total} 条")
        offset += PAGE_SIZE

    return all_products


def save(products: list):
    # 保存完整 JSON
    with open("lingxing_products.json", "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    # 保存 CSV（核心字段）
    fields = ["id", "sku", "product_name", "product_type", "is_combo",
              "status_text", "cg_price", "category_name", "create_time",
              "update_time", "product_developer", "product_creator_realname",
              "supplier_name", "sonProductStr", "comboProductStr"]
    with open("lingxing_products.csv", "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(products)

    print(f"已保存 {len(products)} 条 -> lingxing_products.json / lingxing_products.csv")


if __name__ == "__main__":
    products = scrape_all()
    save(products)
