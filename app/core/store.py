"""
Mini Redis 코어 모듈

이 파일은 Mini Redis의 핵심인 해시 테이블과 키-값 저장소를 구현한다.
Python의 내장 dict를 사용하지 않고, 직접 해시 테이블을 만들어서
해시 충돌 처리(체이닝)와 동작 원리를 이해할 수 있도록 설계했다.
"""

import threading
from time import time


class HashTable:
    """
    커스텀 해시 테이블 클래스

    Python의 dict를 쓰지 않고 직접 만든 해시 테이블이다.
    내부적으로 '버킷 배열'을 사용하며, 해시 충돌이 발생하면
    같은 버킷 안에 리스트로 여러 (key, value) 쌍을 저장하는 '체이닝' 방식을 쓴다.
    """

    def __init__(self, size: int = 256):
        # 버킷 개수를 설정한다. 기본값은 256개.
        # 버킷이 많을수록 충돌이 줄어들어 성능이 좋아지지만, 메모리를 더 쓴다.
        # 각 버킷은 빈 리스트로 시작하고, 나중에 (key, value) 튜플이 들어간다.
        self.size = size
        self.buckets = [[] for _ in range(self.size)]

    def _hash(self, key: str) -> int:
        """
        문자열로 된 키를 숫자(배열 인덱스)로 바꿔주는 함수야.
        예를 들어 "user:1" 이라는 키가 들어오면,
        파이썬이 계산한 숫자를 버킷 개수로 나눈 나머지를 돌려줘.
        이렇게 하면 항상 0 ~ (size-1) 사이의 숫자가 나와서 배열 범위를 벗어나지 않아.
        """
        return hash(key) % self.size

    def set(self, key: str, value) -> None:
        """
        키-값 쌍을 해시 테이블에 저장한다.
        이미 같은 키가 있으면 값을 덮어쓰고, 없으면 새로 추가한다.

        동작 순서:
        1. 키를 해시 함수에 넣어서 버킷 번호를 구한다.
        2. 해당 버킷(리스트)을 순회하면서 같은 키가 있는지 찾는다.
        3. 같은 키가 있으면 → 값만 교체 (덮어쓰기)
        4. 같은 키가 없으면 → 새 (key, value) 쌍을 버킷 끝에 추가
        """
        index = self._hash(key)
        bucket = self.buckets[index]

        # 버킷 안을 하나씩 확인해서 같은 키가 있는지 찾는다.
        for i, (k, v) in enumerate(bucket):
            if k == key:
                # 같은 키를 찾았으면 값만 새 값으로 바꾼다.
                bucket[i] = (key, value)
                return

        # 같은 키가 없었으면 새로 추가한다.
        bucket.append((key, value))

    def get(self, key: str):
        """
        키에 해당하는 값을 해시 테이블에서 찾아 돌려준다.
        키가 없으면 None을 반환한다.

        동작 순서:
        1. 키를 해시 함수에 넣어서 어떤 버킷에 저장되어 있는지 찾는다.
        2. 그 버킷 안을 하나씩 살펴보면서 키가 일치하는 쌍을 찾는다.
        3. 찾으면 값을 반환하고, 끝까지 못 찾으면 None을 반환한다.
        """
        index = self._hash(key)
        bucket = self.buckets[index]

        for k, v in bucket:
            if k == key:
                return v

        # 버킷을 다 뒤졌는데 키가 없으면 None
        return None

    def delete(self, key: str) -> bool:
        """
        키에 해당하는 데이터를 해시 테이블에서 삭제한다.
        삭제에 성공하면 True, 키가 없어서 삭제할 게 없으면 False를 반환한다.

        동작 순서:
        1. 키의 해시값으로 버킷 번호를 구한다.
        2. 버킷 안에서 해당 키를 찾는다.
        3. 찾으면 리스트에서 제거(pop)하고 True 반환.
        4. 못 찾으면 False 반환.
        """
        index = self._hash(key)
        bucket = self.buckets[index]

        for i, (k, v) in enumerate(bucket):
            if k == key:
                # 찾았으면 해당 위치의 데이터를 제거한다.
                bucket.pop(i)
                return True

        # 키를 찾지 못했다.
        return False

    def exists(self, key: str) -> bool:
        """
        키가 해시 테이블에 존재하는지 확인한다.
        get()으로 찾아본 뒤, None이 아니면 존재하는 것으로 판단한다.

        주의: 값으로 None을 저장한 경우에는 오동작할 수 있지만,
        Mini Redis에서는 값이 항상 문자열이므로 문제없다.
        """
        return self.get(key) is not None

    def keys(self) -> list:
        """
        해시 테이블에 저장된 모든 키를 리스트로 반환한다.
        모든 버킷을 순회하면서 키만 모은다.
        """
        result = []
        for bucket in self.buckets:
            for k, v in bucket:
                result.append(k)
        return result

    def flush(self) -> None:
        """
        해시 테이블의 모든 데이터를 삭제한다.
        모든 버킷을 빈 리스트로 다시 초기화하는 방식이다.
        """
        self.buckets = [[] for _ in range(self.size)]


class MiniRedis:
    """
    Mini Redis 키-값 저장소 클래스

    내부적으로 두 개의 HashTable 인스턴스를 사용한다:
    - hash_table: 실제 키-값 데이터를 저장
    - expire_at: 키별 만료 시간(Unix timestamp)을 저장

    만료 전략은 'Lazy Deletion(게으른 삭제)'이다.
    → 별도의 타이머가 돌지 않고, 누군가 키를 조회할 때 만료 여부를 확인한다.
    → 만료되었으면 그때서야 삭제한다. Redis 실제 구현에서도 이 방식을 사용한다.

    동시에 여러 요청이 들어와도 데이터가 꼬이지 않도록
    쓰기 작업(set, delete, expire, flush)에는 threading.Lock을 건다.
    """

    def __init__(self):
        # 키-값 데이터를 저장하는 해시 테이블
        self.hash_table = HashTable()
        # 키별 만료 시간(timestamp)을 저장하는 해시 테이블
        self.expire_at = HashTable()
        # 여러 스레드가 동시에 데이터를 수정하지 못하도록 잠금장치를 만든다.
        self.lock = threading.Lock()

    def _is_expired(self, key: str) -> bool:
        """
        키가 만료되었는지 확인하는 내부 함수.
        만료 시간이 설정되어 있고, 현재 시간이 그 시간을 넘었으면 True를 반환한다.
        만료 시간이 설정되지 않았거나 아직 안 지났으면 False를 반환한다.
        """
        exp = self.expire_at.get(key)
        if exp is not None and time() > exp:
            return True
        return False

    def _delete_expired(self, key: str) -> None:
        """
        만료된 키를 실제로 삭제하는 내부 함수.
        데이터(hash_table)와 만료 정보(expire_at) 양쪽 모두에서 제거한다.
        """
        self.hash_table.delete(key)
        self.expire_at.delete(key)

    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """
        키-값 쌍을 저장한다.
        ttl(초 단위)이 주어지면 만료 시간도 함께 저장한다.

        예: set("user:1", "jiyong", ttl=60)
        → "user:1" 키에 "jiyong" 값을 저장하고, 60초 후 만료되도록 설정.

        Lock을 걸어서 여러 요청이 동시에 set()을 호출해도 데이터가 꼬이지 않게 한다.
        """
        with self.lock:
            self.hash_table.set(key, value)
            if ttl is not None:
                # 현재 시간 + ttl초 = 만료 시점의 Unix timestamp
                self.expire_at.set(key, time() + ttl)
            else:
                # ttl이 없으면 기존 만료 정보를 제거한다. (영구 저장)
                self.expire_at.delete(key)

    def get(self, key: str) -> str | None:
        """
        키에 해당하는 값을 조회한다.
        Lazy Deletion 전략: 조회 시점에 만료 여부를 확인하고,
        만료되었으면 삭제 후 None을 반환한다.

        반환값:
        - 값이 있고 만료 안 됨 → 해당 값(문자열)
        - 값이 없거나 만료됨 → None
        """
        # 만료 확인 → 만료된 키는 삭제하고 None 반환
        if self._is_expired(key):
            with self.lock:
                self._delete_expired(key)
            return None

        return self.hash_table.get(key)

    def delete(self, key: str) -> bool:
        """
        키를 삭제한다.
        데이터와 만료 정보 양쪽에서 모두 삭제한다.
        삭제 성공 시 True, 키가 없었으면 False를 반환한다.
        """
        with self.lock:
            # 만료 정보도 함께 삭제 (있든 없든 시도)
            self.expire_at.delete(key)
            return self.hash_table.delete(key)

    def exists(self, key: str) -> bool:
        """
        키가 존재하는지 확인한다.
        만료된 키는 존재하지 않는 것으로 처리한다.
        """
        # 만료 확인 → 만료된 키는 삭제 후 False 반환
        if self._is_expired(key):
            with self.lock:
                self._delete_expired(key)
            return False

        return self.hash_table.exists(key)

    def expire(self, key: str, ttl: int) -> bool:
        """
        이미 존재하는 키에 만료 시간을 설정한다.
        키가 존재하지 않거나 이미 만료되었으면 False를 반환한다.

        예: expire("user:1", 30)
        → "user:1" 키가 30초 후 자동으로 만료되도록 설정.
        """
        with self.lock:
            # 키가 존재하지 않으면 만료 설정 불가
            if not self.hash_table.exists(key):
                return False

            # 이미 만료된 키인지도 확인
            if self._is_expired(key):
                self._delete_expired(key)
                return False

            # 현재 시간 + ttl초 = 새 만료 시점
            self.expire_at.set(key, time() + ttl)
            return True

    def ttl(self, key: str) -> int:
        """
        키의 남은 수명(TTL)을 초 단위로 반환한다.

        반환값 규칙 (Redis와 동일):
        - 양수: 남은 초
        - -1: 키는 있지만 만료 시간이 설정되지 않음 (영구 저장)
        - -2: 키가 없거나 이미 만료됨
        """
        # 키가 존재하지 않으면 -2
        if not self.hash_table.exists(key):
            return -2

        # 만료 확인 → 만료되었으면 삭제하고 -2 반환
        if self._is_expired(key):
            with self.lock:
                self._delete_expired(key)
            return -2

        # 만료 시간이 설정되어 있는지 확인
        exp = self.expire_at.get(key)
        if exp is None:
            # 만료 시간 없음 = 영구 저장
            return -1

        # 남은 시간 계산: 만료 시점 - 현재 시간 (소수점 버림)
        remaining = int(exp - time())
        return remaining

    def keys(self) -> list:
        """
        저장된 모든 키 중 만료되지 않은 것만 반환한다.
        각 키마다 만료 여부를 확인하고, 만료된 키는 삭제한다.
        """
        all_keys = self.hash_table.keys()
        valid_keys = []

        for key in all_keys:
            if self._is_expired(key):
                # 만료된 키는 삭제
                with self.lock:
                    self._delete_expired(key)
            else:
                valid_keys.append(key)

        return valid_keys

    def flush(self) -> None:
        """
        모든 데이터를 삭제한다.
        데이터 해시 테이블과 만료 시간 해시 테이블 모두 초기화한다.
        """
        with self.lock:
            self.hash_table.flush()
            self.expire_at.flush()

    def get_all_data(self) -> dict:
        """
        현재 저장된 모든 데이터와 만료 정보를 딕셔너리로 반환한다.
        persistence.py가 스냅샷을 JSON 파일로 저장할 때 이 메서드를 호출해.

        반환 형태:
        {
          "data": { "user:1": "jiyong", ... },
          "expire_at": { "user:1": 1700000000.0, ... }
        }

        주의: 여기서는 JSON 저장을 위해 Python dict를 사용한다.
        이건 '데이터 저장소'가 아니라 '내보내기용 변환'이므로 괜찮아.
        """
        # hash_table의 모든 키를 순회하면서 dict로 변환
        data = {}
        for key in self.hash_table.keys():
            data[key] = self.hash_table.get(key)

        # expire_at의 모든 키를 순회하면서 dict로 변환
        expire = {}
        for key in self.expire_at.keys():
            expire[key] = self.expire_at.get(key)

        return {"data": data, "expire_at": expire}

    def load_data(self, data: dict, expire_at: dict) -> None:
        """
        외부에서 가져온 데이터를 store에 직접 주입한다.
        persistence.py가 스냅샷 파일을 읽어서 복원할 때 이 메서드를 호출해.

        마치 게임 로드처럼, 저장해둔 데이터를 해시 테이블에 하나씩 넣어주는 거야.
        Lock으로 보호해서 복원 도중에 다른 요청이 끼어들지 못하게 한다.
        """
        with self.lock:
            # 기존 데이터를 비우고 새로 넣는다.
            self.hash_table.flush()
            self.expire_at.flush()

            # 데이터를 하나씩 해시 테이블에 넣는다.
            for key, value in data.items():
                self.hash_table.set(key, value)

            # 만료 정보도 하나씩 해시 테이블에 넣는다.
            for key, exp_time in expire_at.items():
                self.expire_at.set(key, exp_time)


# 싱글톤 인스턴스 생성
# 앱 전체에서 하나의 MiniRedis 인스턴스를 공유한다.
# 다른 파일에서 from app.core.store import store 로 가져다 쓴다.
store = MiniRedis()
