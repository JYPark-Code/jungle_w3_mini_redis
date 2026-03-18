"""
Mini Redis API 요청/응답 스키마

FastAPI에서 클라이언트가 보내는 데이터(요청)와
서버가 돌려주는 데이터(응답)의 형태를 미리 정의해두는 파일이야.
Pydantic의 BaseModel을 상속받으면 FastAPI가 자동으로
데이터 검증(타입 체크)과 JSON 변환을 해준다.
"""

from pydantic import BaseModel


# ──────────────────────────────────────────────
# Request 모델 (클라이언트 → 서버)
# ──────────────────────────────────────────────

class SetRequest(BaseModel):
    # 값을 저장할 때 클라이언트가 보내는 데이터 형태야.
    # key는 저장할 이름, value는 저장할 값이야.
    # ttl은 몇 초 후에 자동으로 사라질지 설정하는 선택 항목이야. 없으면 영구 저장돼.
    key: str       # 저장할 키 이름 (예: "user:1")
    value: str     # 저장할 값 (예: "jiyong")
    ttl: int | None = None  # 만료 시간(초). None이면 영구 저장


class SetNxRequest(BaseModel):
    # 키가 없을 때만 저장할 때 보내는 데이터 형태야. (Set if Not eXists)
    # 좌석 예약처럼 "먼저 온 1명만 성공"해야 할 때 사용해.
    # SetRequest와 같은 필드지만, 동작이 다르기 때문에 별도 모델로 분리했어.
    key: str                    # 저장할 키 이름
    value: str                  # 저장할 값
    ttl: int | None = None      # 만료 시간(초). None이면 영구 저장


class ExpireRequest(BaseModel):
    # 이미 저장된 키에 만료 시간을 설정할 때 보내는 데이터 형태야.
    # key는 만료 시간을 설정할 대상, ttl은 몇 초 후에 사라질지야.
    key: str   # 만료 시간을 설정할 키 이름
    ttl: int   # 몇 초 후에 만료시킬지 (필수)


# ──────────────────────────────────────────────
# Response 모델 (서버 → 클라이언트)
# ──────────────────────────────────────────────

class ValueResponse(BaseModel):
    # GET 요청의 응답이야. 키에 해당하는 값을 돌려준다.
    # 키가 없거나 만료되었으면 value가 None이 된다.
    value: str | None  # 조회된 값. 없으면 None


class ExistsResponse(BaseModel):
    # 키가 존재하는지 확인하는 요청의 응답이야.
    # 존재하면 True, 없거나 만료되었으면 False를 돌려준다.
    exists: bool  # 키 존재 여부 (True / False)


class TTLResponse(BaseModel):
    # 키의 남은 수명을 알려주는 응답이야.
    # 양수: 남은 초, -1: TTL 없음(영구), -2: 키 없음 또는 만료됨
    ttl: int  # 남은 수명(초)


class KeysResponse(BaseModel):
    # 저장된 모든 키 목록을 돌려주는 응답이야.
    # 만료된 키는 제외하고 살아있는 키만 포함한다.
    keys: list[str]  # 키 이름들의 리스트


class MessageResponse(BaseModel):
    # 단순한 성공/실패 메시지를 돌려주는 응답이야.
    # 예: "OK", "삭제 완료", "키를 찾을 수 없습니다" 등
    message: str  # 결과 메시지


class SetNxResponse(BaseModel):
    # set_nx 요청의 응답이야.
    # success가 True면 저장(예약) 성공, False면 이미 누군가 먼저 저장한 것이야.
    success: bool  # 저장 성공 여부
    message: str   # 결과 메시지 (예: "예약 성공", "이미 예약된 좌석입니다")
