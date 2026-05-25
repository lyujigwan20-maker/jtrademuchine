from pathlib import Path
import json
import os
import requests


REAL_BASE_URL = "https://openapi.koreainvestment.com:9443"
PAPER_BASE_URL = "https://openapivts.koreainvestment.com:29443"
TOKEN_ENDPOINT = "/oauth2/tokenP" 

PRICE_ENDPOINT = "/uapi/domestic-stock/v1/quotations/inquire-price"
PRICE_TR_ID = "FHKST01010100" 


def load_env_if_exists(env_path: Path) -> bool:
    if not env_path.exists():
        return False
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False
    load_dotenv(env_path)
    return True


def get_base_url(env_name: str) -> str:
    if env_name == "real":
        return REAL_BASE_URL
    return PAPER_BASE_URL


def request_access_token(env_name: str, app_key: str, app_secret: str) -> str:
    url = f"{get_base_url(env_name)}{TOKEN_ENDPOINT}"
    headers = {"Content-Type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }
    response = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
    response.raise_for_status()
    return response.json()["access_token"]


def inquire_price(env_name: str, app_key: str, app_secret: str, access_token: str, stock_code: str) -> dict:
    url = f"{get_base_url(env_name)}{PRICE_ENDPOINT}"
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {access_token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": PRICE_TR_ID,
        "custtype": "P",
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
    }
    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


base_dir = Path(__file__).parent
load_env_if_exists(base_dir / "kis_key.env")

env_name = os.getenv("KIS_ENV", "demo")
app_key = os.getenv("KIS_APP_KEY")
app_secret = os.getenv("KIS_APP_SECRET")
stock_code = "000660"

print("KIS 현재가 조회: 요청 흐름 확인")
print(f"TR ID: {PRICE_TR_ID}")
print(f"Endpoint: {PRICE_ENDPOINT}")
print(f"기본 종목코드: {stock_code}")

if not app_key or not app_secret:
    print()
    print("KIS_APP_KEY 또는 KIS_APP_SECRET이 없습니다.")
    print("지금은 '요청 흐름'까지만 확인하고 다음 단계로 넘어가도 됩니다.")
else:
    try:
        import requests
    except ImportError:
        print()
        print("requests 패키지가 없어 실제 현재가 조회 요청을 보내지 못했습니다.")
        print("지금은 '요청 흐름'까지만 확인하고 다음 단계로 넘어가도 됩니다.")
        raise SystemExit(0)

    print()
    print("1) 접근 토큰 발급")
    access_token = request_access_token(env_name, app_key, app_secret)

    print("2) 현재가 조회 요청")
    data = inquire_price(env_name, app_key, app_secret, access_token, stock_code)

    print()
    print(f"응답 코드: {data.get('rt_cd')}")
    print(f"메시지: {data.get('msg1')}")

    if data.get("rt_cd") == "0":
        output = data.get("output", {})
        stock_name = output.get("hts_kor_isnm") or output.get("prdt_name")
        if stock_name:
            print(f"종목명: {stock_name}")
        print(f"종목코드: {output.get('stck_shrn_iscd', stock_code)}")
        print(f"현재가: {output.get('stck_prpr', '확인 필요')}원")
