# Mini Redis

> 해시 테이블을 직접 구현하여 만든 인메모리 키-값 저장소 (REST API)

Redis의 핵심 원리(해시 테이블, TTL, 동시성 제어)를 Python dict 없이 밑바닥부터 구현하여,
자료구조의 동작 방식을 깊이 이해하기 위해 만든 프로젝트입니다.

---

## 기술 스택

| 항목 | 내용 |
|------|------|
| Backend | FastAPI + Uvicorn |
| 저장소 | 직접 구현한 HashTable (Python dict 미사용) |
| 동시성 | threading.Lock |
| 만료 처리 | Lazy Deletion |
| 캐싱 전략 | Cache Aside Pattern |
| 영속성 | JSON 스냅샷 (snapshot.json) |
| 테스트 | pytest |
| 프론트엔드 | HTML + Vanilla JS |
| 터널링 | Cloudflare Tunnel |

---

## 아키텍처

### HashTable 구조

배열 + 체이닝(Chaining) 방식으로 충돌 처리.
두 개의 HashTable 인스턴스로 data / TTL 분리 관리.

```
버킷 배열 (크기: 256)
┌───────────┐
│ bucket[0] │ → [(key_a, val_a), (key_b, val_b)]  ← 체이닝으로 충돌 처리
│ bucket[1] │ → [(key_c, val_c)]
│ bucket[2] │ → []
│    ...    │
│bucket[255]│ → [(key_z, val_z)]
└───────────┘
```

```python
hash_table = HashTable()   # key → value
expire_at  = HashTable()   # key → 만료 timestamp
```

### TTL 만료 처리 — Lazy Deletion

- 별도 스케줄러 없이 조회 시점에만 만료 여부 확인
- 만료된 키는 조회 즉시 삭제 후 None 반환

### 동시성 제어

- threading.Lock으로 모든 쓰기 연산 보호 (set, delete, expire, flush)
- 동시에 같은 좌석을 예약하려 해도 1명만 성공

### 캐싱 전략 — Cache Aside Pattern

```
1. 캐시(Mini Redis) 먼저 확인
2. 캐시 미스 → 외부 API 호출
3. 결과를 캐시에 저장
4. 다음 요청부터 캐시에서 반환
```

### 영속성 — JSON 스냅샷

- 서버 시작 시 snapshot.json 자동 복원
- 60초마다 백그라운드 자동 저장 (daemon thread)
- 서버 종료 시 마지막 스냅샷 저장
- 만료된 키는 복원 시 제외

---

## API 명세

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/set` | 키-값 저장 (TTL 선택) |
| GET | `/get/{key}` | 값 조회 |
| DELETE | `/delete/{key}` | 키 삭제 |
| GET | `/exists/{key}` | 키 존재 여부 |
| GET | `/keys` | 전체 키 목록 |
| DELETE | `/flush` | 전체 초기화 |
| POST | `/expire` | TTL 설정 |
| GET | `/ttl/{key}` | 남은 만료 시간 |
| GET | `/health` | 서버 상태 |

---

## 실행 방법

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

외부 접속 (Cloudflare Tunnel):
```bash
cloudflared tunnel --url http://localhost:8000
```

브라우저에서 `http://localhost:8000/docs` 접속 시 Swagger UI 확인 가능

---

## 테스트 실행

```bash
pytest tests/ -v
```

---

## 핵심 구현 포인트 요약

| 포인트 | 구현 방식 |
|--------|----------|
| 해시 충돌 처리 | 체이닝(Chaining) |
| TTL 만료 | Lazy Deletion |
| 동시성 제어 | threading.Lock |
| 캐싱 전략 | Cache Aside Pattern |
| 데이터 영속성 | JSON 스냅샷 자동 저장/복원 |

---

## 성능 비교 결과

| 시나리오 | 응답 시간 |
|----------|----------|
| 외부 API 직접 호출 100회 | ___ ms |
| Mini Redis 캐시 사용 | ___ ms |
| 실제 Redis 캐시 사용 | ___ ms |

> 벤치마크 실행 후 실제 수치로 업데이트 예정
