"""
파일명: paper_order_once.py
설명: 한국투자증권 OpenAPI 모의투자 매수/매도 (통합 유틸리티 캐시 적용)
"""

import sys
import time
import json
import requests

# 💡 [수정됨] 없는 함수 대신, 유틸리티에 있는 모의/실전 URL 변수를 직접 가져옵니다.
from kis_query_utils import (
    load_env_safely,
    get_env_values,
    request_access_token,
    PAPER_BASE_URL,
    REAL_BASE_URL
)

# =========================================================
# 1. 글로벌 상수 (주문 전용)
# =========================================================
ORDER_ENDPOINT = "/uapi/domestic-stock/v1/trading/order-cash"
PAPER_BUY_TR_ID = "VTTC0012U"   # 매수
PAPER_SELL_TR_ID = "VTTC0011U"  # 매도

# =========================================================
# 2. 주문 전용 함수
# =========================================================
def build_order_request_data(account_no: str, product_code: str, stock_code: str, quantity: int, price: int) -> dict:
    return {
        "CANO": account_no,
        "ACNT_PRDT_CD": product_code,
        "PDNO": stock_code,
        "ORD_DVSN": "00",             
        "ORD_QTY": str(quantity),
        "ORD_UNPR": str(price),
        "EXCG_ID_DVSN_CD": "KRX",
        "SLL_TYPE": "",
        "CNDT_PRIC": "",
    }

def request_order(tr_id: str, app_key: str, app_secret: str, access_token: str, order_data: dict, is_paper: bool = True) -> dict:
    """주문 특화 통신 함수 (서버 지연 대비 20초 타임아웃 유지)"""
    # 💡 [수정됨] 가져온 URL 변수를 활용해 최종 주소를 조립합니다.
    base_url = PAPER_BASE_URL if is_paper else REAL_BASE_URL
    url = f"{base_url}{ORDER_ENDPOINT}"
    
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {access_token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "custtype": "P",
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(order_data), timeout=20)
    
    if response.status_code >= 400:
        error_msg = f"[API 에러] HTTP {response.status_code}\n서버 응답: {response.text}"
        print(f"\n❌ {error_msg}") 
        raise RuntimeError("서버에서 주문을 거절했습니다.")
        
    return response.json()

# =========================================================
# 3. 메인 실행부
# =========================================================
if __name__ == "__main__":
    print("========== 한국투자 모의투자 자동주문 시작 ==========\n")
    
    load_env_safely("kis_key.env")
    env_values = get_env_values()
    
    if not all([env_values["app_key"], env_values["app_secret"], env_values["account_no"], env_values["product_code"]]):
        print("❌ [오류] 환경변수가 누락되었습니다.")
        sys.exit(1)

    STOCK_CODE = "009150"  # 삼성전기
    QUANTITY = 1           # 1주
    PRICE = 1583000         # 주문가격
    IS_PAPER = True        # 모의투자 모드
    
    print(f"📌 [주문 대상] 종목코드: {STOCK_CODE} / 수량: {QUANTITY}주 / 가격: {PRICE:,}원\n")

    order_data = build_order_request_data(
        env_values["account_no"], 
        env_values["product_code"], 
        STOCK_CODE, 
        QUANTITY, 
        PRICE
    )
    
    try:
        print("🔑 1. 토큰 확인 중 (캐시 우선)...")
        access_token = request_access_token(
            app_key=env_values["app_key"], 
            app_secret=env_values["app_secret"],
            is_paper=IS_PAPER
        )
        print("✅ 토큰 준비 완료")

        print("\n📈 2. 매수 주문(Buy) 요청 중...")
        buy_result = request_order(PAPER_BUY_TR_ID, env_values["app_key"], env_values["app_secret"], access_token, order_data, IS_PAPER)
        print(f"✅ 매수 응답 코드: {buy_result.get('rt_cd')} / 메시지: {buy_result.get('msg1')}")
        
        print("\n⏳ 서버 안정을 위해 1초 대기...")
        time.sleep(1) 
        
        print("\n📉 3. 매도 주문(Sell) 요청 중...")
        sell_result = request_order(PAPER_SELL_TR_ID, env_values["app_key"], env_values["app_secret"], access_token, order_data, IS_PAPER)
        print(f"✅ 매도 응답 코드: {sell_result.get('rt_cd')} / 메시지: {sell_result.get('msg1')}")

    except Exception as e:
        print(f"\n⚠️ [프로그램 중단] {e}")
    
    print("\n========== 모든 작업이 완료되었습니다 ==========")