import time
import requests
import hashlib
import base64
import hmac

# 官方原版签名函数
def gen_sign(timestamp, secret):
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return sign

def send_feishu_msg(text):
    # ========= 这里改成你自己的 =========
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/6021c485-797a-48eb-91e5-f0b4cf144b3e"
    bot_secret = "K0MnbNq9KiF6tjgGNnkZ1c"
    # ==================================

    timestamp = str(int(time.time()))
    sign = gen_sign(timestamp, bot_secret)

    payload = {
        "timestamp": timestamp,
        "sign": sign,
        "msg_type": "text",
        "content": {
            "text": text
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    res = requests.post(webhook_url, json=payload, headers=headers)
    print(res.text)
    
if __name__ == "__main__":
    a = "同步所有任务表"
    send_feishu_msg(f"<at user_id=\"openclaw配置\">@openclaw配置</at> {a}")