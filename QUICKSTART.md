# 🚀 Quick Start Guide

## 최소 5분 안에 실행하기

### 1️⃣ 데이터 준비

프로젝트 루트에 `data` 폴더를 만들고, DART API에서 받은 JSON 파일들을 아래 구조로 배치하세요:

```
data/
├── CFS/2024/*.json       # 연결재무제표
├── OFS/2024/*.json       # 개별재무제표
├── EXEC/2024/*.json      # 임원 보유 주식
├── ACQ/2024/*.json       # 자사주 취득
└── ...
```

**파일명 형식**: `{기업코드}.json` (예: `00100601.json`)

---

### 2️⃣ 백엔드 실행 (선택 1: 자동)

**Windows:**
```cmd
cd backend
run.bat
```

**Linux/Mac:**
```bash
cd backend
./run.sh
```

### 2️⃣ 백엔드 실행 (선택 2: 수동)

```bash
cd backend

# 1. 가상 환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일을 열어서 DATA_PATH를 실제 경로로 수정
# 예: DATA_PATH=../data

# 4. 서버 실행
python -m app.main
```

**확인:** http://localhost:8000 접속 시 `{"status": "ok", ...}` 표시

---

### 3️⃣ 프론트엔드 실행 (선택 1: 자동)

**새 터미널 창을 열고:**

**Windows:**
```cmd
cd frontend
run.bat
```

**Linux/Mac:**
```bash
cd frontend
./run.sh
```

### 3️⃣ 프론트엔드 실행 (선택 2: 수동)

```bash
cd frontend

# 1. 패키지 설치
npm install

# 2. 개발 서버 실행
npm run dev
```

**확인:** http://localhost:5173 접속

---

## 🎯 첫 번째 분석 실행하기

### 웹 UI 사용

1. http://localhost:5173 접속
2. "기업 코드 입력" 필드에 기업 코드 입력 (예: `00100601`)
3. "단일 분석" 버튼 클릭
4. 결과 확인!

### API 직접 호출 (cURL)

**단일 기업 분석:**
```bash
curl http://localhost:8000/api/analyze/00100601
```

**상위 50개 종목:**
```bash
curl http://localhost:8000/api/top/50
```

**일괄 분석:**
```bash
curl -X POST http://localhost:8000/api/analyze/batch \
  -H "Content-Type: application/json" \
  -d '{"corp_codes": ["00100601", "00101220"]}'
```

---

## 🐛 문제 해결

### 문제: `ModuleNotFoundError: No module named 'fastapi'`

**해결:**
```bash
cd backend
pip install -r requirements.txt
```

### 문제: `Error loading data: FileNotFoundError`

**해결:**
- `backend/.env` 파일의 `DATA_PATH` 확인
- 데이터 폴더 구조 확인 (`data/CFS/2024/*.json`)

### 문제: `CORS error` (프론트엔드에서 API 호출 실패)

**해결:**
- 백엔드 서버가 실행 중인지 확인 (http://localhost:8000)
- 브라우저 콘솔에서 정확한 에러 메시지 확인

### 문제: `npm: command not found`

**해결:**
- Node.js 설치: https://nodejs.org/
- 설치 후 터미널 재시작

---

## 📝 다음 단계

- [README.md](README.md) - 전체 문서
- [알고리즘 상세](README.md#알고리즘-상세)
- [API 문서](README.md#api-문서)

---

**Happy Investing! 🐂📈**
