"""
SQLite 기반 열차 데이터베이스 모듈

이 파일은 SQLite 파일(trains.db)로 열차 데이터를 관리해.
파일 모드로 저장해서 매번 디스크에서 읽어오는 '느린 조회'를 만들어.
이걸 Mini Redis 캐시와 비교하면 캐시가 얼마나 빠른지 체감할 수 있어.
"""

import sqlite3
import json
import os

# 데이터베이스 파일 경로 (프로젝트 루트에 생성)
DB_PATH = "trains.db"

# 열차 목업 데이터
# 서울에서 부산, 대전, 대구로 가는 KTX와 SRT 열차 정보야.
TRAIN_DATA = [
    # 서울 <-> 부산
    {"id": "KTX-101", "type": "KTX", "from": "서울", "to": "부산", "depart": "06:00", "arrive": "08:30", "price": 59800},
    {"id": "KTX-103", "type": "KTX", "from": "서울", "to": "부산", "depart": "08:00", "arrive": "10:30", "price": 59800},
    {"id": "SRT-201", "type": "SRT", "from": "서울", "to": "부산", "depart": "07:00", "arrive": "09:20", "price": 52600},
    {"id": "SRT-203", "type": "SRT", "from": "서울", "to": "부산", "depart": "09:00", "arrive": "11:20", "price": 52600},
    # 서울 <-> 대전
    {"id": "KTX-301", "type": "KTX", "from": "서울", "to": "대전", "depart": "07:30", "arrive": "08:20", "price": 23700},
    {"id": "SRT-401", "type": "SRT", "from": "서울", "to": "대전", "depart": "08:30", "arrive": "09:15", "price": 20900},
    # 서울 <-> 대구
    {"id": "KTX-501", "type": "KTX", "from": "서울", "to": "대구", "depart": "07:00", "arrive": "08:50", "price": 43500},
    {"id": "SRT-601", "type": "SRT", "from": "서울", "to": "대구", "depart": "09:00", "arrive": "10:45", "price": 38400},
]


def init_db() -> None:
    """
    데이터베이스를 초기화하는 함수야.
    trains.db 파일을 만들고, 테이블을 생성하고, 목업 데이터를 넣어.
    이미 데이터가 있으면 중복으로 넣지 않고 넘어가.
    서버가 시작될 때 자동으로 호출돼.
    """
    # SQLite 파일에 연결해. 파일이 없으면 자동으로 만들어져.
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # trains 테이블을 만들어. 이미 있으면 무시해.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trains (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            from_station TEXT NOT NULL,
            to_station TEXT NOT NULL,
            depart TEXT NOT NULL,
            arrive TEXT NOT NULL,
            price INTEGER NOT NULL
        )
    """)

    # 이미 데이터가 있는지 확인해. 있으면 넣지 않아.
    cursor.execute("SELECT COUNT(*) FROM trains")
    count = cursor.fetchone()[0]

    if count == 0:
        # 데이터가 없으면 목업 데이터를 전부 넣어.
        for train in TRAIN_DATA:
            cursor.execute(
                "INSERT INTO trains (id, type, from_station, to_station, depart, arrive, price) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (train["id"], train["type"], train["from"], train["to"], train["depart"], train["arrive"], train["price"])
            )
        conn.commit()
        print("[DB] trains.db 초기화 완료 - 열차 데이터 삽입됨")
    else:
        print("[DB] trains.db 이미 데이터 있음 - 스킵")

    conn.close()


def get_trains(from_station: str, to_station: str) -> list:
    """
    SQLite 파일에서 열차 목록을 직접 조회하는 함수야.
    매번 디스크에서 파일을 열고 읽어오기 때문에 캐시보다 느려.
    출발지와 도착지로 필터링해서 해당하는 열차만 돌려줘.

    예: get_trains("서울", "부산") -> 서울에서 부산으로 가는 열차 리스트
    """
    # SQLite 파일에 연결해서 조회해. (매번 디스크 I/O 발생)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 출발지와 도착지가 일치하는 열차만 가져와.
    cursor.execute(
        "SELECT id, type, from_station, to_station, depart, arrive, price FROM trains WHERE from_station = ? AND to_station = ?",
        (from_station, to_station)
    )
    rows = cursor.fetchall()
    conn.close()

    # 조회 결과를 딕셔너리 리스트로 변환해서 돌려줘.
    # API 응답으로 보내기 좋은 형태야.
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "type": row[1],
            "from": row[2],
            "to": row[3],
            "depart": row[4],
            "arrive": row[5],
            "price": row[6],
        })

    return result
