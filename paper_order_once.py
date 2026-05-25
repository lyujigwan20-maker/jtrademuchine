"""
한국투자증권 OpenAPI - 모의투자 매수/매도 예제
(상세 에러 추적 및 지연 방지 모드 적용)
"""

import sys
from pathlib import Path
import json
import os

# =========================================================
# 1. 패키지 예외 처리
# =========================================================
try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("❌ [오류] 필수 패키지가 없습니다. 터미널에 아래 명령어를 입력하세요:")
    print("pip install requests python-dotenv")
    sys.exit(1)


# =========================================================
# 2. 글로벌 상수 (URL 및 TR ID)
# =========================================================
PAPER_BASE_URL = "https://openapivts.koreainvestment.com:29443"
TOKEN_ENDPOINT = "/oauth2/tokenP"
ORDER_ENDPOINT = "/uapi/domestic-stock/v1/trading/order-cash"

PAPER_BUY_TR_ID = "VTTC0012U"   # 매수
PAPER_SELL_TR_ID = "VTTC0011U"  # 매도


# =========================================================
# 3. 유틸리티 함수
# =========================================================
def load_env_safely(env_filename: str) -> bool:
    """환경변수 파일을 안전하게 로드합니다."""
    base_dir = Path(__file__).parent
    env_path = base_dir / env_filename
    
    if not env_path.exists():
        return False
        
    load_dotenv(env_path, override=True)
    return True

def build_order_request_data(account_no: str, product_code: str, stock_code: str, quantity: int, price: int) -> dict[str, str]:
    """서버에 보낼 주문 데이터를 조립합니다."""
    return {
        "CANO": account_no,
        "ACNT_PRDT_CD": product_code,
        "PDNO": stock_code,
        "ORD_DVSN": "00",             # 지정가
        "ORD_QTY": str(quantity),
        "ORD_UNPR": str(price),
        "EXCG_ID_DVSN_CD": "KRX",
        "SLL_TYPE": "",
        "CNDT_PRIC": "",
    }


# =========================================================
# 4. API 통신 함수 (🚨 디버그 로직 추가됨)
# =========================================================
def request_access_token(app_key: str, app_secret: str) -> str:
    url = f"{PAPER_BASE_URL}{TOKEN_ENDPOINT}"
    headers = {"Content-Type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
    
    if response.status_code >= 400:
        raise RuntimeError(f"[토큰 발급 실패] HTTP {response.status_code} / 서버 응답: {response.text}")
        
    return response.json()["access_token"]

def request_order(tr_id: str, app_key: str, app_secret: str, access_token: str, order_data: dict) -> dict:
    url = f"{PAPER_BASE_URL}{ORDER_ENDPOINT}"
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {access_token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "custtype": "P",
    }
    
    # 💡 1. 모의투자 서버 지연을 대비해 기다리는 시간을 20초로 늘렸습니다.
    response = requests.post(url, headers=headers, data=json.dumps(order_data), timeout=20)
    
    # 💡 2. 서버 에러 발생 시 숨겨진 진짜 메시지를 터미널에 강력하게 출력합니다.
    if response.status_code >= 400:
        error_msg = f"[API 에러] HTTP 상태코드: {response.status_code}\n서버 응답 내용: {response.text}"
        print(f"\n❌ {error_msg}") 
        raise RuntimeError("서버에서 주문을 거절했습니다.")
        
    return response.json()

def paper_buy(app_key: str, app_secret: str, access_token: str, order_data: dict) -> dict:
    return request_order(PAPER_BUY_TR_ID, app_key, app_secret, access_token, order_data)

def paper_sell(app_key: str, app_secret: str, access_token: str, order_data: dict) -> dict:
    return request_order(PAPER_SELL_TR_ID, app_key, app_secret, access_token, order_data)


# =========================================================
# 5. 메인 실행부
# =========================================================
if __name__ == "__main__":
    print("========== 한국투자 모의투자 자동주문 시작 ==========\n")
    
    env_file = "kis_key.env"
    if not load_env_safely(env_file):
        print(f"⚠️ [경고] '{env_file}' 파일을 찾을 수 없습니다.")

    APP_KEY = os.getenv("KIS_APP_KEY")
    APP_SECRET = os.getenv("KIS_APP_SECRET")
    ACCOUNT_NO = os.getenv("KIS_ACCOUNT_NO")
    PRODUCT_CODE = os.getenv("KIS_ACCOUNT_PRODUCT_CODE", "01")
    
    if not all([APP_KEY, APP_SECRET, ACCOUNT_NO, PRODUCT_CODE]):
        print("❌ [오류] 환경변수가 누락되었습니다.")
        sys.exit(1)

    STOCK_CODE = "005930"  # 삼성전자
    QUANTITY = 1           # 1주
    PRICE = 186900         # 주문가격 (지정가)
    
    print(f"📌 [주문 대상] 종목코드: {STOCK_CODE} / 수량: {QUANTITY}주 / 가격: {PRICE:,}원\n")

    order_data = build_order_request_data(ACCOUNT_NO, PRODUCT_CODE, STOCK_CODE, QUANTITY, PRICE)
    
    try:
        print("🔑 1. 접근 토큰 발급 요청 중...")
        access_token = request_access_token(APP_KEY, APP_SECRET)
        print("✅ 토큰 발급 완료")

        print("\n📈 2. 매수 주문(Buy) 요청 중...")
        buy_result = paper_buy(APP_KEY, APP_SECRET, access_token, order_data)
        print(f"✅ 매수 응답 코드: {buy_result.get('rt_cd')} / 메시지: {buy_result.get('msg1')}")
        
        print("\n📉 3. 매도 주문(Sell) 요청 중...")
        sell_result = paper_sell(APP_KEY, APP_SECRET, access_token, order_data)
        print(f"✅ 매도 응답 코드: {sell_result.get('rt_cd')} / 메시지: {sell_result.get('msg1')}")

    except Exception as e:
        # 강제 종료나 에러 발생 시 여기서 안내를 남깁니다.
        print(f"\n⚠️ [프로그램 중단] {e}")
    
    print("\n========== 모든 작업이 완료되었습니다 ==========")