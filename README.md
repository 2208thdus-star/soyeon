# 소연 진입 타이밍 스캐너 — 백엔드 서버

## 배포 방법 (Render.com)

1. 이 폴더를 GitHub 레포지토리로 올리기
2. render.com 접속 → New Web Service
3. GitHub 레포 연결
4. 설정:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Deploy 클릭

## API
- GET `/` → 서버 상태 확인
- GET `/scan` → 전체 종목 스캔 결과
