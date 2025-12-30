# 🐂 My Little Buffett - Alpha Finder

**상장폐지 안 당할 주식 찾기**

Gemini의 알고리즘 설계를 기반으로 한 주식 분석 도구입니다.
"오를 주식을 찾기보다, 안 오를(위험한) 주식을 먼저 쳐내고, 남은 것 중 폭발력 있는 종목을 고른다"는 전략을 구현했습니다.

---

## 📋 목차

- [특징](#특징)
- [시스템 구조](#시스템-구조)
- [설치 및 실행](#설치-및-실행)
- [API 문서](#api-문서)
- [알고리즘 상세](#알고리즘-상세)

---

## ✨ 특징

### 3단계 파이프라인

1. **💀 Death Filter (지뢰 제거)**
   - 좀비 기업 (이자보상배율 1 미만 2년 연속)
   - 가짜 이익 (순이익 흑자 + 영업CF 적자)
   - 주주 뒤통수 (자금 목적 외 사용)
   - 소송 리스크 (청구금액 > 자기자본 10%)
   - 물량 폭탄 (CB 희석률 20% 초과)

2. **📊 Value Score (펀더멘탈 점수, 0~100점)**
   - 현금 창출력 (30점)
   - 자회사 건전성 (20점) - CFS vs OFS 비교
   - 사업 확장성 (20점) - 타법인 출자 분석
   - 주주 환원 의지 (30점) - 자사주 취득/소각

3. **🚀 Catalyst Boost (가산점)**
   - 임원 매수 (+10점)
   - 시설 투자 (+10점)
   - 큰손 입성 (+5점)

### 등급 체계

- **S등급** (90점 이상): 강력 매수 추천
- **A+/A** (70~89점): 매수 추천
- **B+/B** (50~69점): 관심 종목
- **C/D** (40점 이하): 투자 비추천
- **F등급**: 위험 기업 (필터 탈락)

---

## 🏗️ 시스템 구조

```
my-little-buffett/
├── backend/              # FastAPI 백엔드
│   ├── app/
│   │   ├── filters.py    # Death Filter
│   │   ├── scoring.py    # Value Score
│   │   ├── boosters.py   # Catalyst Boost
│   │   ├── analyzer.py   # 메인 엔진
│   │   ├── utils.py      # 유틸리티
│   │   └── main.py       # FastAPI 앱
│   └── requirements.txt
│
├── frontend/             # Svelte 프론트엔드
│   ├── src/
│   │   ├── App.svelte    # 메인 컴포넌트
│   │   ├── app.css       # 스타일
│   │   └── main.js       # 엔트리포인트
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
└── data/                 # 재무 데이터 (JSON 형식)
    ├── CFS/2024/         # 연결재무제표
    ├── OFS/2024/         # 개별재무제표
    ├── EXEC/2024/        # 임원 보유 주식
    ├── MAJOR/2024/       # 주요주주
    ├── CB/2024/          # 전환사채
    ├── DEC/2024/         # 유상증자
    ├── ACQ/2024/         # 자사주 취득
    ├── USE/2024/         # 자금 사용 내역
    ├── LIT/2024/         # 소송
    └── INV/2024/         # 타법인 출자
```

---

## 🚀 설치 및 실행

### 사전 요구사항

- Python 3.9+
- Node.js 18+
- Git

### 1. 저장소 클론

```bash
git clone <repository-url>
cd my-little-buffett
```

### 2. 데이터 준비

`data/` 폴더에 DART API 데이터를 저장합니다.
폴더 구조는 위의 [시스템 구조](#시스템-구조) 참조.

### 3. 백엔드 실행

```bash
cd backend

# 가상 환경 생성 (선택 사항)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# .env 파일 생성
cp .env.example .env
# DATA_PATH를 실제 데이터 경로로 수정

# 서버 실행
python -m app.main
# 또는
uvicorn app.main:app --reload
```

백엔드 실행 확인: http://localhost:8000

### 4. 프론트엔드 실행

```bash
cd frontend

# 패키지 설치
npm install

# 개발 서버 실행
npm run dev
```

프론트엔드 접속: http://localhost:5173

---

## 📡 API 문서

### 헬스 체크

```
GET /
```

**응답:**

```json
{
  "status": "ok",
  "message": "My Little Buffett API is running",
  "data_path": "../data"
}
```

### 단일 기업 분석

```
GET /api/analyze/{corp_code}
```

**파라미터:**

- `corp_code`: 기업 코드 (예: 00100601)

**응답 예시:**

```json
{
  "corp_code": "00100601",
  "final_score": 85,
  "grade": "A",
  "recommendation": "매수 추천 (펀더멘탈 우량)",
  "stage1_filter": {
    "passed": true,
    "severity": "SAFE"
  },
  "stage2_score": {
    "total_score": 75,
    "breakdown": {
      "cash": {"score": 30, "reason": "영업CF/자산: 15.20%"},
      "subsidiary": {"score": 20, "reason": "자회사 기여도 양호"},
      "expansion": {"score": 15, "reason": "알짜 자회사 보유"},
      "shareholder": {"score": 10, "reason": "자사주 취득"}
    }
  },
  "stage3_boost": {
    "total_boost": 10,
    "boosters": {
      "insider": {"boost": 10, "reason": "임원 장내 매수 감지"}
    }
  }
}
```

### 일괄 분석

```
POST /api/analyze/batch
```

**요청 바디:**

```json
{
  "corp_codes": ["00100601", "00101220", "00126380"]
}
```

**응답:** 분석 결과 배열 (점수 내림차순 정렬)

### 상위 N개 종목 조회

```
GET /api/top/{n}?min_score=0
```

**파라미터:**

- `n`: 조회할 종목 수 (기본 50, 최대 200)
- `min_score`: 최소 점수 필터 (0~100)

**응답:**

```json
{
  "total_analyzed": 2000,
  "total_filtered": 150,
  "results": [ /* 상위 N개 결과 */ ]
}
```

---

## 🧠 알고리즘 상세

### 1단계: Death Filter (지뢰 제거)

| 검증 항목 | 탈락 조건 | 데이터 |
|----------|----------|--------|
| 좀비 기업 | 이자보상배율 < 1 (2년 연속) | CFS/OFS |
| 가짜 이익 | 당기순이익 > 0 AND 영업CF < 0 | CFS |
| 자금 오용 | 목적 외 사용 발생 | USE |
| 소송 리스크 | 청구금액 > 자기자본 × 10% | LIT |
| 물량 폭탄 | CB 주식수 > 총 주식수 × 20% | CB |

### 2단계: Value Score (펀더멘탈)

#### 현금 창출력 (30점)

```
비율 = 영업활동현금흐름 / 자산총계

15% 이상 → 30점
10% 이상 → 20점
5% 이상  → 10점
미만     → 0점
```

#### 자회사 건전성 (20점)

```
차이 = CFS 당기순이익 - OFS 당기순이익

차이 > 0       → 20점 (자회사가 돈을 벌어옴)
차이 < -30%    → 0점 (자회사 적자 심각)
기타           → 10점
```

#### 사업 확장성 (20점)

- 타법인 출자 데이터(INV) 분석
- 흑자 자회사 > 적자 자회사 → 20점
- 적자 자회사 > 흑자 자회사 → 5점

#### 주주 환원 의지 (30점)

- 자사주 취득 + 소각 예정 → 30점
- 자사주 취득 (소각 미정) → 15점
- 없음 → 0점

### 3단계: Catalyst Boost (가산점)

- **임원 매수**: 대표이사/등기임원 장내 매수 → +10점
- **시설 투자**: 유상증자 목적이 시설/사업 확장 → +10점
- **큰손 입성**: 제3자 배정 증자 → +5점

---

## 🛡️ 예외 처리 전략

### 데이터 누락

- CFS 없으면 OFS 사용
- OFS 없으면 CFS만으로 평가
- 둘 다 없으면 `UNKNOWN` 태그

### 0으로 나누기 방지

```python
if denominator > 0:
    ratio = numerator / denominator
else:
    ratio = 0  # 또는 매우 큰 값 (999)
```

### API 에러 핸들링

- 모든 API 엔드포인트에서 `try-except` 사용
- HTTP 500 에러 반환 시 상세 메시지 포함

---

## 📝 라이선스

MIT License

---

## 👥 기여

이슈와 PR은 언제나 환영합니다!

---

## 🎯 향후 계획

- [ ] 데이터베이스 연동 (PostgreSQL)
- [ ] 실시간 데이터 업데이트 (DART API 자동 수집)
- [ ] 포트폴리오 백테스팅 기능
- [ ] 모바일 반응형 UI 개선
- [ ] 기업 간 비교 기능
- [ ] PDF 리포트 생성

---

**Made with ❤️ and Gemini's Algorithm**
