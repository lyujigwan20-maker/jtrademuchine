"""
파일명: order_history_check.py
설명: 한국투자증권 OpenAPI 당일 주문/체결 내역 조회 (실전/모의 지원)
"""

import json
import sys

# 앞서 만든 궁극의 유틸리티에서 필요한 무기들을 가져옵니다.
from kis_query_utils import (
    load_env_safely,
    get_env_values,
    request_access_token,
    send_get_request,
    today_yyyymmdd
)

# =========================================================
# 1. 엔드포인트 및 TR ID 설정
# =========================================================
ORDER_HISTORY_ENDPOINT = "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"

# 실전/모의 TR ID 분리
TR_ID_REAL = "TTTC0081R"
TR_ID_DEMO = "VTTC0081R"

def get_tr_id(is_paper: bool) -> str:
    """모의투자 여부에 따라 올바른 TR ID를 반환합니다."""
    return TR_ID_DEMO if is_paper else TR_ID_REAL

# =========================================================
# 2. 메인 비즈니스 로직 함수
# =========================================================
def inquire_order_history(env_values: dict, access_token: str, is_paper: bool = True) -> dict:
    """당일 주식 주문 및 체결 내역을 조회합니다."""
    
    tr_id = get_tr_id(is_paper)
    today = today_yyyymmdd()
    
    # Code B의 디테일한 파라미터 양식 적용
# 한국투자증권 국내주식 잔고조회 올바른 필수 파라미터 세팅
# 💡 주문 체결 내역 조회용 올바른 파라미터로 복구
    params = {
        "CANO": env_values["account_no"],
        "ACNT_PRDT_CD": env_values["product_code"],
        "INQR_STRT_DT": today,            # 조회 시작일 (오늘)
        "INQR_END_DT": today,             # 조회 종료일 (오늘)
        "SLL_BUY_DVSN_CD": "00",          # 00: 전체, 01: 매도, 02: 매수
        "INQR_DVSN": "00",                # 00: 역순정렬
        "PDNO": "",                       # 공란이면 전종목 조회
        "CCLD_DVSN": "00",                # 00: 전체, 01: 체결, 02: 미체결
        "ORD_GNO_BRNO": "",
        "ODNO": "",
        "INQR_DVSN_3": "00",
        "INQR_DVSN_1": "",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
        "EXCG_ID_DVSN_CD": "KRX",
    }
    
    # 궁극의 유틸리티에 있는 공통 GET 함수를 호출하여 코드를 한 줄로 끝냅니다!
    return send_get_request(
        endpoint=ORDER_HISTORY_ENDPOINT,
        tr_id=tr_id,
        params=params,
        app_key=env_values["app_key"],
        app_secret=env_values["app_secret"],
        access_token=access_token,
        is_paper=is_paper
    )

# =========================================================
# 3. 실제 실행부 (안전 장치 적용)
# =========================================================
if __name__ == "__main__":
    print("========== 당일 주문/체결 내역 조회 시작 ==========\n")
    
    # 1) 환경변수 안전 로드
    load_env_safely("kis_key.env")
    env_values = get_env_values()
    
    # 방어적 프로그래밍: 설정값 누락 확인
    if not all([env_values["app_key"], env_values["app_secret"], env_values["account_no"], env_values["product_code"]]):
        print("❌ [오류] 환경변수가 누락되었습니다. kis_key.env 파일을 확인하세요.")
        sys.exit(1)

    # ※ 현재는 모의투자 테스트 중이므로 True로 고정합니다. 실전 전환 시 False로 변경하세요.
    IS_PAPER = True  
    
    print(f"📌 [조회 정보] 일자: {today_yyyymmdd()} / 모의투자 여부: {IS_PAPER}\n")

    try:
        # 2) 토큰 발급 (캐시가 있으면 0.01초 만에 파일에서 불러옴)
        print("🔑 1. 토큰 확인 중...")
        access_token = request_access_token(
            app_key=env_values["app_key"], 
            app_secret=env_values["app_secret"], 
            is_paper=IS_PAPER
        )
        print("✅ 토큰 준비 완료")

        # 3) 주문 내역 API 통신
        print("\n📥 2. 당일 주문 내역 서버 요청 중...")
        result_data = inquire_order_history(env_values, access_token, IS_PAPER)
        
        print(f"✅ 조회 응답 코드: {result_data.get('rt_cd')} / 메시지: {result_data.get('msg1')}\n")
        
        # 4) 결과 예쁘게 출력하기 (Code B의 요약 방식을 약간 개량)
        order_list = result_data.get("output1", [])
        print(f"📊 총 조회 건수: {len(order_list)}건")
        
        if not order_list:
            print("👉 오늘 체결 또는 미체결된 주문 내역이 없습니다.")
        else:
            print("-" * 60)
            for order in order_list:
                ord_tmd = order.get('ord_tmd') # 153000 형태의 시간
                formatted_time = f"{ord_tmd[:2]}:{ord_tmd[2:4]}:{ord_tmd[4:]}" if ord_tmd else "-"
                
                print(f"[{formatted_time}] {order.get('prdt_name')} ({order.get('sll_buy_dvsn_cd_name')})")
                print(f" └ 주문수량: {order.get('ord_qty')}주 | 주문단가: {order.get('ord_unpr')}원")
                print(f" └ 체결수량: {order.get('tot_ccld_qty')}주 | 미체결수량: {order.get('rmn_qty')}주")
                print("-" * 60)

    except Exception as e:
        print(f"\n❌ [통신 오류 발생] {e}")

    print("\n========== 조회 작업이 완료되었습니다 ==========")