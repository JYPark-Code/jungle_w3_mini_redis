"""
Mini Redis 영속성(Persistence) 모듈

서버가 꺼져도 데이터가 사라지지 않도록 JSON 파일로 스냅샷을 저장하고 불러오는 파일이야.
마치 게임의 '세이브/로드' 기능처럼, 서버가 꺼지기 전에 데이터를 파일로 저장해두고
다시 켜질 때 그 파일을 읽어서 데이터를 복원해줘.
"""

import json
import threading
from datetime import datetime
from time import time, sleep
from pathlib import Path

# 스냅샷 파일 경로: 프로젝트 루트의 snapshot.json
# Path(__file__)은 이 파일(persistence.py)의 위치이고,
# .parent.parent.parent로 프로젝트 루트까지 올라간다.
# app/core/persistence.py → app/core → app → 프로젝트 루트
SNAPSHOT_PATH = Path(__file__).parent.parent.parent / "snapshot.json"


def save_snapshot(store) -> None:
    """
    지금 Mini Redis에 저장된 모든 데이터를 JSON 파일로 저장해.
    마치 게임을 세이브하는 것처럼, 서버가 꺼져도 데이터가 남아있게 해줘.
    파일 저장에 실패해도 서버는 계속 돌아가야 하니까 에러만 출력하고 넘어가.

    저장 형태:
    {
      "data": { "user:1": "jiyong", ... },
      "expire_at": { "user:1": 1700000000.0, ... },
      "saved_at": "2024-01-01T00:00:00"
    }
    """
    try:
        # store에서 현재 데이터와 만료 정보를 가져온다.
        all_data = store.get_all_data()

        # 저장 시각을 함께 기록해서 언제 저장했는지 알 수 있게 한다.
        snapshot = {
            "data": all_data["data"],
            "expire_at": all_data["expire_at"],
            "saved_at": datetime.now().isoformat(),
        }

        # JSON 파일로 저장한다.
        # ensure_ascii=False를 쓰면 한글이 깨지지 않고 그대로 저장돼.
        # indent=2를 쓰면 사람이 읽기 좋은 형태로 저장돼.
        with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

        print(f"[Persistence] 스냅샷 저장 완료: {SNAPSHOT_PATH}")

    except Exception as e:
        # 파일 저장에 실패해도 서버는 계속 돌아가야 해.
        # 에러 메시지만 출력하고 넘어간다.
        print(f"[Persistence] 스냅샷 저장 실패: {e}")


def load_snapshot(store) -> None:
    """
    snapshot.json 파일이 있으면 읽어서 store에 데이터를 복원해.
    마치 게임을 로드하는 것처럼, 이전에 저장해둔 데이터를 다시 불러와.

    주의사항:
    - 이미 만료된 키는 복원하지 않아. (현재 시간과 비교해서 걸러냄)
    - 파일이 없으면 조용히 넘어가. (처음 실행할 때는 파일이 없으니까)
    - 파일이 손상되어도 조용히 넘어가. (서버 정상 시작이 최우선)
    """
    try:
        # 스냅샷 파일이 없으면 복원할 게 없으니 그냥 넘어간다.
        if not SNAPSHOT_PATH.exists():
            print("[Persistence] 스냅샷 파일 없음 — 빈 상태로 시작")
            return

        with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
            snapshot = json.load(f)

        data = snapshot.get("data", {})
        expire_at = snapshot.get("expire_at", {})

        # 만료된 키를 걸러낸다.
        # 현재 시간보다 만료 시간이 이미 지난 키는 복원할 필요가 없어.
        now = time()
        expired_keys = [
            key for key, exp in expire_at.items()
            if exp <= now
        ]

        # 만료된 키는 data와 expire_at 양쪽에서 제거한다.
        for key in expired_keys:
            data.pop(key, None)
            expire_at.pop(key, None)

        # 걸러진 데이터를 store에 주입한다.
        store.load_data(data, expire_at)

        saved_at = snapshot.get("saved_at", "알 수 없음")
        print(f"[Persistence] 스냅샷 복원 완료 (저장 시각: {saved_at}, "
              f"복원 키: {len(data)}개, 만료 제외: {len(expired_keys)}개)")

    except Exception as e:
        # 파일이 손상되었거나 읽기에 실패해도 서버는 정상 시작해야 해.
        print(f"[Persistence] 스냅샷 복원 실패 (무시하고 빈 상태로 시작): {e}")


def start_auto_snapshot(store, interval: int = 60) -> None:
    """
    백그라운드에서 일정 간격(기본 60초)마다 자동으로 스냅샷을 저장해.
    마치 게임의 '자동 저장' 기능처럼, 주기적으로 데이터를 파일에 백업해줘.

    daemon=True로 설정해서 서버가 종료되면 이 스레드도 자동으로 같이 꺼져.
    별도로 스레드를 멈추는 코드를 작성할 필요가 없어.
    """
    def _auto_save():
        # 무한 루프로 interval초마다 스냅샷을 저장한다.
        while True:
            sleep(interval)
            save_snapshot(store)

    # 데몬 스레드: 메인 프로그램(서버)이 종료되면 자동으로 같이 종료된다.
    # 이렇게 하면 서버가 꺼질 때 이 스레드 때문에 멈추지 않아.
    thread = threading.Thread(target=_auto_save, daemon=True)
    thread.start()
    print(f"[Persistence] 자동 스냅샷 시작 (매 {interval}초마다 저장)")
