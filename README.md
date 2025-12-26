# My Little Buffett

워렌 버핏의 투자 원칙에 기반한 **5대 투자 지표 분석 시스템**입니다.
OpenDART API를 활용하여 한국 상장기업의 재무 데이터를 분석합니다.

## 5대 투자 지표

### 1. 현금 창출 능력
- **영업활동현금흐름 vs 당기순이익**
- 영업활동현금흐름 > 당기순이익 ✅ (필수 조건)
- 2년 연속 미달 시 매도 신호

### 2. 이자보상배율
- **영업이익 ÷ 이자비용**
- ≥ 3.0: 매우 안전
- ≥ 1.5: 최소 기준
- < 1.0: 좀비 기업 (투자 금지)

### 3. 영업이익 성장률
- **(당기 - 전기) ÷ 전기 × 100**
- ≥ 15%: 고성장주
- 0-10%: 일반 성장
- < 0%: 역성장

### 4. 희석 가능 물량 비율
- **전환사채 주식수 ÷ 총 발행 주식수 × 100**
- 0%: 가장 좋음
- < 5%: 감내 가능
- ≥ 10%: 투자 주의

### 5. 내부자 순매수 강도
- 최근 6개월 내 임원 장내매수 현황
- 2인 이상 순매수 또는 CEO 매수: 강력 호재
- 지속적 매도: 악재

## 기술 스택

### Backend
- **FastAPI** - 고성능 Python 웹 프레임워크
- **httpx** - 비동기 HTTP 클라이언트
- **Pydantic** - 데이터 검증

### Frontend
- **SvelteKit** - 프론트엔드 프레임워크
- **TypeScript** - 타입 안전성
- **Vite** - 빌드 도구

### 아키텍처
- **FSD (Feature-Sliced Design)** - 확장 가능한 파일 구조

## 프로젝트 구조

```
My-Little-Buffett/
├── backend/
│   ├── app/                    # 앱 설정 및 메인
│   ├── features/               # 기능별 모듈
│   │   ├── indicators/         # 5대 지표 계산
│   │   ├── disclosures/        # 공시 정보
│   │   └── financial_statements/
│   ├── entities/               # 엔티티 정의
│   └── shared/                 # 공통 모듈
│       ├── api/                # OpenDART API 클라이언트
│       ├── schemas/            # Pydantic 스키마
│       └── utils/              # 유틸리티
├── frontend/
│   └── src/
│       ├── lib/
│       │   ├── app/            # 앱 설정
│       │   ├── features/       # 기능
│       │   ├── widgets/        # UI 위젯
│       │   ├── entities/       # 엔티티
│       │   └── shared/         # 공통
│       │       ├── api/        # API 클라이언트
│       │       ├── ui/         # UI 컴포넌트
│       │       └── utils/      # 유틸리티
│       └── routes/             # 페이지
└── README.md
```

## 설치 및 실행

### 사전 요구사항
- Python 3.11+
- Node.js 18+
- OpenDART API 키 ([발급 받기](https://opendart.fss.or.kr))

### Backend 설정

```bash
cd backend

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에서 DART_API_KEY 설정

# 서버 실행
python -m app.main
```

### Frontend 설정

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

### 접속
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API 문서: http://localhost:8000/docs

## API 엔드포인트

### 지표 분석
- `GET /api/indicators/analysis/{corp_code}` - 종합 분석
- `GET /api/indicators/cash-generation/{corp_code}` - 현금 창출 능력
- `GET /api/indicators/interest-coverage/{corp_code}` - 이자보상배율
- `GET /api/indicators/operating-growth/{corp_code}` - 영업이익 성장률
- `GET /api/indicators/dilution-risk/{corp_code}` - 희석 위험
- `GET /api/indicators/insider-trading/{corp_code}` - 내부자 거래

### 재무제표
- `GET /api/statements/{corp_code}` - 전체 재무제표
- `GET /api/statements/{corp_code}/balance-sheet` - 재무상태표
- `GET /api/statements/{corp_code}/income-statement` - 손익계산서
- `GET /api/statements/{corp_code}/cash-flow` - 현금흐름표

### 공시 정보
- `GET /api/disclosures/executive-stock/{corp_code}` - 임원 주식 보유
- `GET /api/disclosures/convertible-bonds/{corp_code}` - 전환사채
- `GET /api/disclosures/major-shareholders/{corp_code}` - 최대주주

## 라이선스

MIT License
