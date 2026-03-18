"""
실제 Redis 클라이언트 모듈

Docker로 실행한 실제 Redis 서버와 통신하는 함수들이야.
Mini Redis(우리가 만든 것)와 실제 Redis의 성능을 비교하기 위해 사용해.
redis-py 라이브러리를 통해 Redis 서버에 명령을 보내.
"""

import redis

# 실제 Redis 연결 (로컬 Docker)
# 연결 실패해도 서버가 죽지 않도록 예외 처리 필수
try:
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    r.ping()
    REDIS_AVAILABLE = True
except Exception:
    r = None
    REDIS_AVAILABLE = False


def redis_set(key: str, value: str, ttl: int = None) -> bool:
    """
    실제 Redis에 키-값을 저장하는 함수야.
    ttl이 있으면 만료 시간도 함께 설정해.
    Redis가 연결되지 않았으면 False를 반환해.
    """
    if r is None:
        return False
    try:
        if ttl is not None:
            r.set(key, value, ex=ttl)
        else:
            r.set(key, value)
        return True
    except Exception:
        return False


def redis_get(key: str) -> str | None:
    """
    실제 Redis에서 키에 해당하는 값을 가져오는 함수야.
    키가 없거나 Redis가 없으면 None을 반환해.
    """
    if r is None:
        return None
    try:
        return r.get(key)
    except Exception:
        return None


def redis_delete(key: str) -> bool:
    """
    실제 Redis에서 키를 삭제하는 함수야.
    삭제 성공하면 True, 실패하면 False를 반환해.
    """
    if r is None:
        return False
    try:
        r.delete(key)
        return True
    except Exception:
        return False


def redis_flush() -> bool:
    """
    실제 Redis의 모든 데이터를 삭제하는 함수야.
    테스트 전에 깨끗한 상태로 만들 때 사용해.
    """
    if r is None:
        return False
    try:
        r.flushdb()
        return True
    except Exception:
        return False


def redis_ping() -> bool:
    """
    Redis 연결 상태를 확인하는 함수야.
    연결되어 있으면 True, 아니면 False를 반환해.
    """
    if r is None:
        return False
    try:
        return r.ping()
    except Exception:
        return False
