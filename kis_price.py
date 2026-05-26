"""
파일명: kis_price.py
설명: 한국투자증권 OpenAPI 현재가 조회 (통합 유틸리티 적용)
"""

import sys
from kis_query_utils import (
    load_env_safely,
    get_env_values,
    request_access_token,
    inquire_price
)

if __name__ == "__main__":
    print("========== 📈 KIS 현재가 조회 시작 ==========\n")
    
    # 1. 환경변수 안전 로드
    load_env_safely("kis_key.env")
    env_values = get_env_values()
    
    if not all([env_values["app_key"], env_values["app_secret"]]):
        print("❌ [오류] 환경변수가 누락되었습니다.")
        sys.exit(1)

    STOCK_CODE = "009150"  # 삼성전기
    IS_PAPER = True 

    try:
        # 💡 핵심: 이제 서버에 떼쓰지 않고, 캐시된 토큰을 우선적으로 찾아옵니다. (403 에러 방지)
        print("🔑 1. 토큰 확인 중 (캐시 우선)...")
        access_token = request_access_token(
            app_key=env_values["app_key"], 
            app_secret=env_values["app_secret"], 
            is_paper=IS_PAPER
        )

        # 💡 유틸리티에 이미 만들어둔 inquire_price 래퍼 함수를 활용해 단 한 줄로 조회를 끝냅니다.
        print("\n📥 2. 현재가 서버 요청 중...")
        data = inquire_price(
            stock_code=STOCK_CODE,
            app_key=env_values["app_key"],
            app_secret=env_values["app_secret"],
            access_token=access_token,
            is_paper=IS_PAPER
        )
        
        if data.get("rt_cd") == "0":
            output = data.get("output", {})
            # 응답 데이터 파싱
            stock_name = output.get("hts_kor_isnm") or output.get("prdt_name", "이름없음")
            current_price = output.get("stck_prpr", "0")
            
            print(f"✅ 조회 성공: {stock_name} ({STOCK_CODE})")
            print(f"💰 현재가: {int(current_price):,}원")
        else:
            print(f"⚠️ [조회 실패] {data.get('msg1')}")

    except Exception as e:
        print(f"\n🚨 [시스템 에러 발생] 원인: {e}")