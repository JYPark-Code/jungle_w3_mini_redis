"""
Mini Redis — FastAPI 앱 진입점

이 파일은 서버의 시작점이야.
레스토랑으로 치면 '정문'에 해당하는 곳이고,
여기서 서버 설정, 라우터 등록, 기본 엔드포인트를 정의한다.
"""

from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.core.store import store
from app.core.persistence import load_snapshot, save_snapshot, start_auto_snapshot
from app.core.database import init_db


# ──────────────────────────────────────────────
# 0. Lifespan (서버 시작/종료 이벤트)
# ──────────────────────────────────────────────
# 서버가 켜질 때와 꺼질 때 자동으로 실행되는 코드야.
# 켜질 때: 이전에 저장해둔 스냅샷을 불러오고, 자동 저장을 시작해.
# 꺼질 때: 마지막으로 한 번 더 스냅샷을 저장해서 데이터를 보존해.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # === 서버 시작 시 실행 ===
    # SQLite DB를 초기화해서 열차 데이터를 준비한다.
    init_db()
    # 이전에 저장한 snapshot.json이 있으면 데이터를 복원한다.
    load_snapshot(store)
    # 60초마다 자동으로 스냅샷을 저장하는 백그라운드 스레드를 시작한다.
    start_auto_snapshot(store, interval=60)
    yield
    # === 서버 종료 시 실행 ===
    # 서버가 꺼지기 직전에 마지막으로 스냅샷을 한 번 더 저장한다.
    save_snapshot(store)


# ──────────────────────────────────────────────
# 1. FastAPI 앱 인스턴스 생성
# ──────────────────────────────────────────────
# FastAPI 앱을 만드는 부분이야.
# 마치 레스토랑을 열기 전에 간판을 다는 것처럼,
# 우리 서버의 이름과 설명을 여기서 정해줘.
# lifespan을 연결해서 서버 시작/종료 시 스냅샷 저장/복원이 자동으로 동작해.
app = FastAPI(
    title="Mini Redis",
    description="해시 테이블 기반 인메모리 키-값 저장소",
    version="1.0.0",
    lifespan=lifespan,
)

# ──────────────────────────────────────────────
# 2. CORS 설정
# ──────────────────────────────────────────────
# CORS(Cross-Origin Resource Sharing)는 브라우저가
# 다른 주소(origin)에서 온 요청을 허용할지 결정하는 보안 정책이야.
# 예: 프론트엔드(localhost:5500)에서 백엔드(localhost:8000)로 요청할 때 필요해.
# 데모용이라 모든 출처, 메서드, 헤더를 허용하도록 설정했어.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # 모든 출처 허용
    allow_methods=["*"],      # 모든 HTTP 메서드 허용 (GET, POST, DELETE 등)
    allow_headers=["*"],      # 모든 HTTP 헤더 허용
    allow_credentials=True,
)

# ──────────────────────────────────────────────
# 3. 라우터 등록
# ──────────────────────────────────────────────
# routes.py에 정의된 API 엔드포인트(set, get, delete 등)를
# 이 앱에 연결하는 부분이야.
# include_router를 하면 routes.py의 모든 경로가 자동으로 앱에 붙어.
app.include_router(router)


# ──────────────────────────────────────────────
# 4. 프론트엔드 정적 파일 서빙
# ──────────────────────────────────────────────
# frontend/ 폴더의 HTML 파일을 /front 경로로 접근할 수 있게 해줘.
# 브라우저에서 http://localhost:8000/front/index.html 로 데모 화면을 볼 수 있어.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/front", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


# ──────────────────────────────────────────────
# 5. 헬스체크 엔드포인트
# ──────────────────────────────────────────────
@app.get("/health")
def health_check():
    # 서버가 살아있는지 확인하는 엔드포인트야.
    # 모니터링 도구나 로드밸런서가 이 경로로 요청을 보내서
    # 서버가 정상인지 확인할 때 사용해.
    return {"status": "ok"}


# ──────────────────────────────────────────────
# 5. 루트 엔드포인트
# ──────────────────────────────────────────────
@app.get("/")
def root():
    # 서버의 첫 페이지야. 브라우저에서 http://localhost:8000 에 접속하면
    # 이 메시지가 보여서 서버가 돌아가고 있다는 걸 알 수 있어.
    return {"message": "Mini Redis is running"}
