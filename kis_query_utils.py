from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
import os
import time
import sys

# =========================================================
# 1. 방어적 패키지 로드
# =========================================================
try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("❌ [오류] 필수 패키지가 없습니다. 터미널에 아래 명령어를 입력하세요:")
    print("pip install requests python-dotenv")
    sys.exit(1)


# =========================================================
# 2. 글로벌 상수 및 엔드포인트
# =========================================================
REAL_BASE_URL = "https://openapi.koreainvestment.com:9443"
PAPER_BASE_URL = "https://openapivts.koreainvestment.com:29443"

TOKEN_ENDPOINT = "/oauth2/tokenP"
PRICE_ENDPOINT = "/uapi/domestic-stock/v1/quotations/inquire-price"

PRICE_TR_ID = "FHKST01010100"

# 캐시 파일 위치 (이 파이썬 파일과 같은 폴더에 숨김 파일로 생성)
CACHE_FILE = Path(__file__).parent / ".kis_token_cache.json"


# =========================================================
# 3. 환경 세팅 유틸리티
# =========================================================
def load_env_safely(env_filename: str = "kis_key.env") -> bool:
    """env 파일을 안전하게 로드합니다. (캐시 무시 덮어쓰기 적용)"""
    env_path = Path(__file__).parent / env_filename
    if not env_path.exists():
        return False
        
    load_dotenv(env_path, override=True)
    return True

def get_env_values() -> dict:
    """환경변수 값을 딕셔너리로 깔끔하게 반환합니다."""
    return {
        "app_key": os.getenv("KIS_APP_KEY"),
        "app_secret": os.getenv("KIS_APP_SECRET"),
        "account_no": os.getenv("KIS_ACCOUNT_NO"),
        "product_code": os.getenv("KIS_ACCOUNT_PRODUCT_CODE", "01"),
    }


# =========================================================
# 4. 스마트 토큰 캐싱 시스템 (핵심 장점 결합)
# =========================================================
def _read_cached_token(is_paper: bool) -> str | None:
    """로컬 캐시 파일에서 유효한 토큰을 찾아 반환합니다."""
    if not CACHE_FILE.exists():
        return None

    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    token = data.get("access_token")
    expires_at = data.get("expires_at")
    cached_mode = data.get("is_paper")

    # 1. 값이 없거나, 2. 모의/실전 모드가 바뀌었거나, 3. 만료 1분 전이면 캐시 폐기
    if not token or not expires_at or cached_mode is None:
        return None
    if cached_mode != is_paper:
        return None
    if time.time() >= float(expires_at) - 60:
        return None

    return token

def _write_cached_token(is_paper: bool, token: str, expires_in: int) -> None:
    """새로 발급받은 토큰을 디스크에 저장합니다."""
    payload = {
        "is_paper": is_paper,
        "access_token": token,
        "expires_at": time.time() + expires_in,
    }
    CACHE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def request_access_token(app_key: str, app_secret: str, is_paper: bool = True) -> str:
    """캐시를 우선 확인하고, 없을 때만 한투 서버로 토큰을 요청합니다."""
    cached = _read_cached_token(is_paper)
    if cached:
        return cached  # 살아있는 토큰 재사용 (속도 극대화)

    base_url = PAPER_BASE_URL if is_paper else REAL_BASE_URL
    url = f"{base_url}{TOKEN_ENDPOINT}"
    
    headers = {"Content-Type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
    
    # [방어적 통신] 서버 에러 발생 시 숨김 없이 원인을 파악해 출력
    if response.status_code >= 400:
        raise RuntimeError(f"[토큰 발급 오류] HTTP {response.status_code} / 응답내용: {response.text}")

    data = response.json()
    token = data["access_token"]
    expires_in = int(data.get("expires_in") or 86400)  # 기본 24시간
    
    _write_cached_token(is_paper, token, expires_in)
    return token


# =========================================================
# 5. 공통 API 통신 프레임워크 (확장성 극대화)
# =========================================================
def build_headers(app_key: str, app_secret: str, access_token: str, tr_id: str) -> dict[str, str]:
    """모든 KIS API에 공통으로 들어가는 인증 헤더를 조립합니다."""
    return {
        "Content-Type": "application/json",
        "authorization": f"Bearer {access_token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "custtype": "P",
    }

def send_get_request(endpoint: str, tr_id: str, params: dict, app_key: str, app_secret: str, access_token: str, is_paper: bool = True) -> dict:
    """GET 요청(조회성)을 처리하는 공통 뼈대 함수입니다."""
    base_url = PAPER_BASE_URL if is_paper else REAL_BASE_URL
    url = f"{base_url}{endpoint}"
    headers = build_headers(app_key, app_secret, access_token, tr_id)
    
    response = requests.get(url, headers=headers, params=params, timeout=10)
    
    if response.status_code >= 400:
        raise RuntimeError(f"[GET 통신 오류 ({tr_id})] HTTP {response.status_code} / 응답: {response.text}")
        
    return response.json()

def send_post_request(endpoint: str, tr_id: str, body: dict, app_key: str, app_secret: str, access_token: str, is_paper: bool = True) -> dict:
    """POST 요청(주문/실행성)을 처리하는 공통 뼈대 함수입니다."""
    base_url = PAPER_BASE_URL if is_paper else REAL_BASE_URL
    url = f"{base_url}{endpoint}"
    headers = build_headers(app_key, app_secret, access_token, tr_id)
    
    response = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
    
    if response.status_code >= 400:
        raise RuntimeError(f"[POST 통신 오류 ({tr_id})] HTTP {response.status_code} / 응답: {response.text}")
        
    return response.json()


# =========================================================
# 6. 비즈니스 래퍼(Wrapper) 함수 예제
# =========================================================
def inquire_price(stock_code: str, app_key: str, app_secret: str, access_token: str, is_paper: bool = True) -> dict:
    """특정 종목의 현재가를 조회합니다. (GET 공통 함수 활용 예시)"""
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
    }
    return send_get_request(PRICE_ENDPOINT, PRICE_TR_ID, params, app_key, app_secret, access_token, is_paper)

def today_yyyymmdd() -> str:
    """조회 파라미터에 자주 쓰이는 오늘 날짜(YYYYMMDD) 반환 유틸"""
    return datetime.now().strftime("%Y%m%d")