"""
Mini Redis API 라우터

팀원들이 각자 맡은 엔드포인트를 이 파일에 구현한다.
SECTION A(CRUD)는 팀원 A가, SECTION B(TTL)는 팀원 B가 담당한다.
각 함수의 body는 비워두었으니, 주석 힌트를 참고해서 로직을 채워넣으면 돼.
"""

import json
from time import time

from fastapi import APIRouter, HTTPException
from app.core.store import store
from app.core.database import get_trains as get_trains_from_db
from app.models.schemas import (
    SetRequest,
    SetNxRequest,
    SetNxResponse,
    ExpireRequest,
    ValueResponse,
    ExistsResponse,
    TTLResponse,
    KeysResponse,
    MessageResponse,
)

# API 엔드포인트들을 모아두는 라우터 객체야.
# 이걸 main.py에서 app.include_router(router)로 등록하면
# 여기에 정의한 경로들이 전부 서버에 연결돼.
router = APIRouter()


# ══════════════════════════════════════════════
# SECTION A: CRUD (팀원 A 작업 구역)
# ══════════════════════════════════════════════


@router.post("/set", response_model=MessageResponse)
async def set_value(request: SetRequest):
    # 키와 값을 Mini Redis에 저장하는 엔드포인트야.
    # 요청 body에서 key, value, ttl을 받아서 store.set()을 호출하면 돼.
    # ttl이 있으면 해당 시간(초) 후에 자동으로 만료돼.

    # Codex 추가 시작: core의 set 메서드에 요청 데이터를 그대로 전달한다.
    # 라우터에는 비즈니스 로직을 두지 않기 위해 저장 처리 자체는 store가 담당한다.
    store.set(request.key, request.value, request.ttl)

    # Codex 추가: 저장이 끝나면 공통 성공 메시지를 응답 모델에 담아 반환한다.
    return MessageResponse(message="OK")
    # Codex 추가 끝


@router.post("/setnx", response_model=SetNxResponse)
async def set_if_not_exists(request: SetNxRequest):
    # 키가 없을 때만 저장하는 엔드포인트야. (Set if Not eXists)
    # 좌석 예약에 사용하며, 동시에 여러 명이 요청해도 1명만 성공해.
    # 성공하면 success: true, 이미 있으면 success: false를 반환해.
    success = store.set_nx(request.key, request.value, request.ttl)
    if success:
        return SetNxResponse(success=True, message="예약 성공")
    return SetNxResponse(success=False, message="이미 예약된 좌석입니다")


@router.get("/get/{key}", response_model=ValueResponse)
async def get_value(key: str):
    # 키에 해당하는 값을 조회하는 엔드포인트야.
    # store.get(key)을 호출해서 값을 가져오면 돼.
    # 값이 None이면 HTTPException(status_code=404)를 발생시켜야 해.

    # Codex 추가 시작: core의 get 메서드로 값을 조회한다.
    # store는 키가 없거나 만료된 경우 None을 반환하므로 그 결과를 그대로 받는다.
    value = store.get(key)

    # Codex 추가: 값이 없으면 API 규칙에 맞게 404를 반환한다.
    # 조회 실패를 명확한 HTTP 상태 코드로 표현해야 클라이언트가 결과를 해석하기 쉽다.
    if value is None:
        raise HTTPException(status_code=404, detail="Key not found")

    # Codex 추가: 조회 성공 시 응답 스키마에 맞춰 value를 감싸서 반환한다.
    return ValueResponse(value=value)
    # Codex 추가 끝


@router.delete("/delete/{key}", response_model=MessageResponse)
async def delete_key(key: str):
    # 키를 삭제하는 엔드포인트야.
    # store.delete(key)를 호출하면 돼.
    # 삭제 성공이면 "OK", 키가 없었으면 "키를 찾을 수 없습니다" 같은 메시지를 반환해.

    # Codex 추가 시작: core의 delete 메서드로 실제 삭제를 시도한다.
    # store는 삭제 성공 여부를 bool로 반환하므로 그 결과를 먼저 받는다.
    result = store.delete(key)

    # Codex 추가: 키가 없으면 API 규칙에 맞게 404를 반환한다.
    # 삭제 실패를 성공 메시지와 구분해야 클라이언트가 상태를 명확히 해석할 수 있다.
    if not result:
        raise HTTPException(status_code=404, detail="Key not found")

    # Codex 추가: 삭제에 성공했을 때만 공통 성공 메시지를 반환한다.
    return MessageResponse(message="OK")
    # Codex 추가 끝


@router.get("/exists/{key}", response_model=ExistsResponse)
async def exists_key(key: str):
    # 키가 존재하는지 확인하는 엔드포인트야.
    # store.exists(key)를 호출해서 True/False를 반환하면 돼.

    # Codex 추가 시작: core의 exists 메서드로 키 존재 여부를 확인한다.
    # store는 만료된 키까지 고려한 True/False를 반환하므로 라우터는 그 결과만 전달하면 된다.
    return ExistsResponse(exists=store.exists(key))
    # Codex 추가 끝


@router.get("/keys", response_model=KeysResponse)
async def get_keys():
    # 저장된 모든 키 목록을 반환하는 엔드포인트야.
    # store.keys()를 호출하면 만료되지 않은 키들의 리스트가 나와.

    # Codex 추가 시작: core의 keys 메서드로 현재 저장된 키 목록을 조회한다.
    # store는 만료된 키를 정리한 뒤 리스트를 반환하므로 라우터는 결과만 응답 스키마에 담으면 된다.
    return KeysResponse(keys=store.keys())
    # Codex 추가 끝


@router.delete("/flush", response_model=MessageResponse)
async def flush_all():
    # 모든 데이터를 삭제하는 엔드포인트야.
    # store.flush()를 호출하면 전체 데이터가 초기화돼.
    # 주의: 되돌릴 수 없으니 신중하게 사용해야 해!

    # Codex 추가 시작: core의 flush 메서드로 저장소 전체를 초기화한다.
    # store가 데이터와 만료 정보를 함께 비우므로 라우터는 호출만 담당하면 된다.
    store.flush()

    # Codex 추가: 전체 삭제가 끝나면 공통 성공 메시지를 반환한다.
    return MessageResponse(message="OK")
    # Codex 추가 끝


# ══════════════════════════════════════════════
# SECTION B: TTL (팀원 B 작업 구역)
# ══════════════════════════════════════════════


@router.post("/expire", response_model=MessageResponse)
async def set_expire(request: ExpireRequest):
    # 이미 저장된 키에 만료 시간을 설정하는 엔드포인트야.
    # store.expire(key, ttl)을 호출하면 돼.
    # 키가 존재하지 않으면 HTTPException(status_code=404)를 발생시켜야 해.

    # Codex 추가 시작: core의 expire 메서드로 기존 키에 TTL 설정을 요청한다.
    # 만료 시점 계산은 store가 이미 담당하므로 라우터는 key와 ttl만 그대로 전달한다.
    result = store.expire(request.key, request.ttl)

    # Codex 추가: 키가 없거나 이미 만료된 경우 store가 False를 돌려주므로 404로 변환한다.
    # 실패를 HTTP 상태 코드로 드러내야 클라이언트가 TTL 설정 실패를 명확히 알 수 있다.
    if not result:
        raise HTTPException(status_code=404, detail="Key not found")

    # Codex 추가: TTL 설정에 성공하면 공통 성공 메시지를 반환한다.
    return MessageResponse(message="OK")
    # Codex 추가 끝


@router.get("/ttl/{key}", response_model=TTLResponse)
async def get_ttl(key: str):
    # 키의 남은 수명(TTL)을 조회하는 엔드포인트야.
    # store.ttl(key)를 호출하면 남은 초가 나와.
    # 반환값: 양수(남은 초), -1(TTL 없음, 영구), -2(키 없음 또는 만료됨)
    # Codex 추가 시작: core의 ttl 메서드로 현재 키의 남은 TTL 값을 조회한다.
    # TTL 계산과 예외 규칙은 store가 이미 구현했으므로 라우터는 결과만 전달하면 된다.
    return TTLResponse(ttl=store.ttl(key))
    # Codex 추가 끝


# ══════════════════════════════════════════════
# SECTION C: 열차 조회 & 벤치마크 (11번 프롬프트)
# ══════════════════════════════════════════════


@router.get("/trains")
async def get_trains(from_station: str, to_station: str):
    """
    DB에서 열차 목록을 직접 조회하는 엔드포인트야.
    캐시를 사용하지 않고 매번 SQLite 파일에서 읽어와.
    벤치마크에서 '캐시 없을 때' 기준으로 사용해.
    """
    start = time()
    result = get_trains_from_db(from_station, to_station)
    elapsed = int((time() - start) * 1000)
    return {"trains": result, "source": "db", "elapsed_ms": elapsed}


@router.get("/trains/cached")
async def get_trains_cached(from_station: str, to_station: str):
    """
    Mini Redis 캐시에서 먼저 조회하는 엔드포인트야.
    캐시에 있으면 바로 반환해 (Cache HIT).
    없으면 DB에서 가져와서 캐시에 저장한 뒤 반환해 (Cache MISS).
    이게 바로 Cache Aside 패턴이야.
    """
    cache_key = f"trains:{from_station}:{to_station}"
    start = time()

    # 캐시에서 먼저 찾아봐
    cached = store.get(cache_key)
    if cached:
        # 캐시 히트! 바로 돌려줘.
        elapsed = int((time() - start) * 1000)
        return {"trains": json.loads(cached), "source": "cache_hit", "elapsed_ms": elapsed}

    # 캐시 미스! DB에서 가져와서 캐시에 저장해.
    result = get_trains_from_db(from_station, to_station)
    store.set(cache_key, json.dumps(result), ttl=60)
    elapsed = int((time() - start) * 1000)
    return {"trains": result, "source": "cache_miss", "elapsed_ms": elapsed}


@router.get("/benchmark/trains")
async def benchmark_trains(n: int = 10, from_station: str = "서울", to_station: str = "부산"):
    """
    DB 직접 조회 vs Mini Redis 캐시 성능을 비교하는 엔드포인트야.
    n번 반복해서 각각의 총 시간을 측정하고 결과를 돌려줘.
    캐시가 얼마나 빠른지 숫자로 확인할 수 있어.
    """
    # 1. 캐시 없이 DB에서 n번 직접 조회
    db_start = time()
    for _ in range(n):
        get_trains_from_db(from_station, to_station)
    db_elapsed = int((time() - db_start) * 1000)

    # 2. Mini Redis 캐시로 n번 조회 (첫 번째는 MISS, 나머지는 HIT)
    cache_key = f"trains:{from_station}:{to_station}"
    store.delete(cache_key)  # 캐시 초기화해서 공정한 테스트
    cache_start = time()
    for _ in range(n):
        cached = store.get(cache_key)
        if not cached:
            result = get_trains_from_db(from_station, to_station)
            store.set(cache_key, json.dumps(result), ttl=60)
    cache_elapsed = int((time() - cache_start) * 1000)

    return {
        "iterations": n,
        "db_only_ms": db_elapsed,
        "mini_redis_ms": cache_elapsed,
        "real_redis_ms": None,  # 13번에서 채움
        "speedup": round(db_elapsed / max(cache_elapsed, 1), 1)
    }