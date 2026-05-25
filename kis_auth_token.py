import os
import json
import requests
from dotenv import load_dotenv

# env 파일 로드
load_dotenv("kis_key.env")

APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")

print(APP_KEY)
print(APP_SECRET)

# 환경변수
APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")

# URL 설정
REAL_BASE_URL = "https://openapi.koreainvestment.com:9443"
PAPER_BASE_URL = "https://openapivts.koreainvestment.com:29443"

TOKEN_ENDPOINT = "/oauth2/tokenP"

# 모의투자 여부
USE_PAPER = True

BASE_URL = PAPER_BASE_URL if USE_PAPER else REAL_BASE_URL

# 최종 URL
url = f"{BASE_URL}{TOKEN_ENDPOINT}"

headers = {
    "content-type": "application/json"
}

body = {
    "grant_type": "client_credentials",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET
}

response = requests.post(
    url,
    headers=headers,
    data=json.dumps(body)
)

result = response.json()

print("STATUS :", response.status_code)
print(json.dumps(result, indent=2, ensure_ascii=False))

if response.status_code == 200:
    access_token = result["access_token"]

    print("\n=== ACCESS TOKEN ===")
    print(access_token)

else:
    print("\n토큰 발급 실패")