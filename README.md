# 🔴 Mini Redis

> Redis의 핵심 원리를 Python으로 직접 구현한 인메모리 키-값 저장소

Python dict를 사용하지 않고 **배열 + 체이닝 HashTable**을 직접 구현하여
Redis의 핵심 동작 원리(TTL, Lazy Deletion, 동시성 제어, 캐싱, 영속성)를 학습하고 시연하는 프로젝트입니다.

---

## 🎯 핵심 구현 포인트

| 포인트 | 구현 방식 | 의미 |
|--------|----------|------|
| 🗃️ 자료구조 | 배열 + 체이닝 HashTable (256 buckets) | Python dict 미사용, 직접 구현 |
| ⏰ TTL 만료 | Lazy Deletion | 조회 시점에 만료 확인 후 삭제 |
| 🔒 동시성 | threading.Lock + setnx | 1명만 예약 성공 보장 |
| 🗄️ 캐싱 전략 | Cache Aside Pattern | DB 부하 감소 |
| 💾 영속성 | JSON 스냅샷 (자동/수동) | 서버 재시작 후 데이터 복구 |

---

## 🛠️ 기술 스택

```
Backend      FastAPI + Uvicorn
Database     SQLite (파일 기반 디스크 I/O)
Cache        직접 구현한 Mini Redis (HashTable)
Real Redis   Docker Redis (성능 비교용)
Test         pytest (43개 전체 통과)
Frontend     Vanilla HTML/JS (단일 파일)
```

---

## 🏗️ 아키텍처

### HashTable 구조

```
buckets = [[], [], [], ...]  ← 256개 배열
              ↓
         체이닝으로 충돌 처리
         [(key1, val1), (key2, val2)]
```

### 두 개의 HashTable로 데이터/TTL 분리

```python
hash_table = HashTable()   # key → value       (데이터 저장)
expire_at  = HashTable()   # key → timestamp   (만료 시각 저장)
```

### Cache Aside Pattern

```
조회 요청
    ↓
Mini Redis 확인
    ├── HIT  → 즉시 반환 (DB 조회 없음)
    └── MISS → DB 조회 → Mini Redis 저장 → 반환
```

### Lazy Deletion

```
GET 호출
    ↓
expire_at 확인
    ├── 만료 안 됨 → 값 반환
    └── 만료됨 → 키 삭제 → None 반환 (TTL = -2)
```

### 동시성 제어

```
5명이 동시에 같은 좌석 예약 시도
    ↓
threading.Lock → 1명만 setnx 성공
    ↓
나머지 4명 → "이미 예약됨"
```

### 영속성 (JSON 스냅샷)

```
서버 실행 중
    ├── 60초마다 snapshot.json 자동 저장
    └── 서버 종료 시 마지막 저장

서버 재시작
    └── snapshot.json 복원 (만료 키 제외)
```

### Mini Redis vs 실제 Redis 비교

| 항목 | Mini Redis (우리 구현) | 실제 Redis |
|------|----------------------|-----------|
| 구현 언어 | Python | C |
| 통신 프로토콜 | HTTP/REST | TCP/RESP |
| 자료구조 | 직접 구현한 HashTable | 최적화된 내장 구조 |
| 동시성 | threading.Lock | 단일 스레드 이벤트 루프 |
| TTL 처리 | Lazy Deletion | Lazy + Active 병행 |
| 영속성 | JSON 스냅샷 | RDB / AOF |
| 자료구조 종류 | String만 지원 | String, List, Hash, Set, ZSet |
| 메모리 관리 | Python GC | jemalloc |
| 로컬 성능 | 1.11ms / 1,801,802 ops/sec | 558ms / 3,578 ops/sec (Docker 오버헤드) |
| 프로덕션 성능 | 수ms | 1ms 이하 |

---

## 📡 API 명세

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
| POST | `/setnx` | 없을 때만 저장 (동시성 핵심) |
| POST | `/hold` | 임시 선점 (TTL 5초) |
| POST | `/confirm` | 예약 확정 |
| GET | `/trains/cached` | Cache Aside 열차 조회 |
| GET | `/benchmark/trains` | DB vs Mini Redis 성능 비교 |
| GET | `/benchmark/redis-compare` | Mini Redis vs 실제 Redis 비교 |
| POST | `/benchmark/concurrent` | 동시 예약 시뮬레이션 |
| POST | `/snapshot/save` | 수동 스냅샷 저장 |
| DELETE | `/snapshot/clear` | 스냅샷 삭제 |
| GET | `/snapshot/status` | 스냅샷 상태 확인 |

---

## 🚀 실행 방법

```bash
# 패키지 설치
pip install -r requirements.txt

# 서버 실행
uvicorn app.main:app --reload

# Docker Redis (비교용)
docker run -d --name redis-test -p 6379:6379 redis:latest

# 테스트 실행
pytest tests/ -v
```

---

## ✅ 테스트 결과

```
총 43개 테스트 전체 통과

단위 테스트  (11개): HashTable, MiniRedis 핵심 로직
통합 테스트  (32개): 전체 API 엔드포인트

커버 범위:
✅ CRUD          ✅ TTL/만료
✅ SETNX         ✅ 임시 선점
✅ Cache Aside   ✅ 동시성
✅ 벤치마크      ✅ 스냅샷
✅ 헬스체크
```

---

## 📊 성능 비교 결과

### DB vs 캐시 비교 (1,000회 반복)

| 시나리오 | 응답 시간 | 비고 |
|----------|---------|------|
| DB 직접 조회 | 140 ms | SQLite 디스크 I/O |
| Mini Redis 캐시 | 4 ms | 인메모리 직접 호출 |
| **속도 향상** | **35배** | |

### Mini Redis vs 실제 Redis (1,000회 set+get)

| | 응답 시간 | ops/sec |
|---|---------|---------|
| Mini Redis | 1.11 ms | 1,801,802 |
| 실제 Redis | 558.96 ms | 3,578 |

**🔍 로컬 환경에서 Mini Redis가 빠른 이유:**
- Mini Redis: 같은 프로세스 내 직접 함수 호출
- 실제 Redis: Docker 네트워크 → TCP 소켓 왕복 오버헤드

**🚀 프로덕션에서 실제 Redis가 강력한 이유:**
- C 언어로 구현된 최적화된 자료구조
- 단일 스레드 이벤트 루프 (GIL 없음)
- 전용 서버 + 최적화된 네트워크
- 메모리 최적화 (jemalloc 사용)

---

## 🎬 데모 시연 순서 (발표자 참고)

```
① 열차 노선 조회
   → Cache MISS 확인 (오른쪽 패널 로그)
   → 재조회 → Cache HIT 확인

② 좌석 임시 선점
   → TTL 5초 카운트다운
   → TTL 로그: 5→4→3→2→1→-2
   → Lazy Deletion 발동 확인

③ 동시 예약 시뮬레이션
   → 좌석 우클릭 선택 → 인원 설정 → 동시 시도
   → 1명만 성공 확인

④ 벤치마크 실행
   → DB vs Mini Redis 수치 비교
   → Mini Redis vs 실제 Redis 비교

⑤ 스냅샷 시연
   → 좌석 예약 후 [지금 저장]
   → 서버 종료 (Ctrl+C)
   → 재시작 → 데이터 유지 확인
```

---

## 💬 QnA 대비

**Q. 해시 충돌을 어떻게 처리했나요?**
배열 + 체이닝 방식. 같은 버킷에 `(key, value)` 리스트로 연결합니다.

**Q. TTL 만료를 어떻게 처리했나요?**
Lazy Deletion. 별도 스케줄러 없이 조회 시점에 만료 확인 후 삭제합니다.

**Q. 동시성 문제를 어떻게 해결했나요?**
`threading.Lock`으로 모든 쓰기 연산 보호. `setnx`로 중복 예약 방지합니다.

**Q. 서버 다운 시 데이터는요?**
60초마다 JSON 스냅샷 자동 저장. 재시작 시 자동 복원됩니다.

**Q. 실제 Redis와 차이점은요?**
Mini Redis는 HTTP/REST, 실제 Redis는 TCP/RESP 프로토콜.
로컬에서는 Mini Redis가 빠르지만 프로덕션에서는 실제 Redis가 우위입니다.
