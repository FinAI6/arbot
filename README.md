# arbot - 암호화폐 차익거래 자동 트레이딩 봇 🤖

**arbot**은 다중 거래소 간 실시간 가격 차이를 이용해 자동으로 차익거래(arbitrage)를 수행하는 고성능 Python 기반 트레이딩 시스템입니다. 실거래 모드뿐 아니라 시뮬레이션, 백테스트 기능도 포함하며, 직관적인 TUI (Textual UI)를 제공합니다.

---

## 🧠 주요 기능

- ✅ **실시간 가격 수집**: WebSocket을 이용한 Binance, Bybit, OKX, Bitget 가격 모니터링
- ⚡ **차익거래 전략**: 스프레드 계산, 수수료 및 슬리피지 고려
- 🤖 **자동 주문 실행**: 실시간 또는 시뮬레이션 기반 주문 처리
- 📊 **SQLite 기록**: 거래 기록, 잔고, 전략 설정 등을 로컬 DB로 관리
- 🧪 **시뮬레이션 & 백테스트**: 실시간 가격 기반 모의 거래 및 과거 데이터 기반 전략 검증
- 💻 **Textual UI**: 실시간 정보, 스프레드, 잔고, 트레이드 로그 등 시각화된 CLI 대시보드
- 🧱 **모듈형 구조**: 거래소별 폴더 분리 및 인터페이스 표준화

---

## ⚙️ 실행 모드

| 모드 | 설명 |
|------|------|
| **실시간 모드** | 실 API 키로 실제 거래소에서 주문 실행 |
| **시뮬레이션 모드** | 실시간 가격 데이터로 가상 주문 시뮬레이션 (Testnet 미사용) |
| **백테스트 모드** | 저장된 과거 가격 데이터로 전략 검증 수행 |

---

## 📦 설치 및 실행 가이드

### 1. 필수 사항

- **Python 3.8 이상**
- **Git**
- **거래소 API 키** (Binance, Bybit, OKX, Bitget 중 2개 이상)

### 2. 프로젝트 클론 및 환경 설정

```bash
# 1. 저장소 클론
git clone https://github.com/FinAI6/arbot.git
cd arbot

# 2. 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate     # Windows

# 3. 의존성 설치
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env` 파일을 생성하여 API 키를 설정하세요:

```bash
# .env 파일 생성
cp .env.example .env
```

`.env` 파일 내용 예시:
```env
# 거래소 API 키 설정 (실제 값으로 변경 필요)
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here

BYBIT_API_KEY=your_bybit_api_key_here
BYBIT_API_SECRET=your_bybit_api_secret_here

OKX_API_KEY=your_okx_api_key_here
OKX_API_SECRET=your_okx_api_secret_here

BITGET_API_KEY=your_bitget_api_key_here
BITGET_API_SECRET=your_bitget_api_secret_here

# 실행 모드 설정 (기본값: simulation)
TRADING_MODE=simulation

# 로그 레벨
LOG_LEVEL=INFO
```

### 4. 설정 파일 조정

`config.json` 또는 `config.local.json` 파일을 수정하여 거래 설정을 조정할 수 있습니다:

```json
{
  "trading_mode": "simulation",
  "exchanges": {
    "binance": {
      "enabled": true,
      "arbitrage_enabled": true,
      "region": "global"
    },
    "bybit": {
      "enabled": true,
      "arbitrage_enabled": true,
      "region": "global"
    }
  },
  "arbitrage": {
    "min_profit_threshold": 0.001,
    "trade_amount_usd": 100.0,
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "max_trades_per_hour": 50,
    "slippage_tolerance": 0.001
  }
}
```

### 5. 실행

#### 시뮬레이션 모드 (추천 - 처음 사용자)
```bash
python run.py
# 또는
python run.py --mode simulation
# 또는 (패키지 설치 후)
python -m arbot.main
```

#### 실거래 모드 (주의: 실제 자금 사용)
```bash
python run.py --mode live
```

#### 백테스트 모드
```bash
python run.py --mode backtest
```

---

## 📁 프로젝트 구조

```
arbot/
├── arbot/                  # 메인 소스코드 패키지
│   ├── __init__.py
│   ├── main.py            # 메인 실행 파일
│   ├── config.py          # 설정 관리
│   ├── database.py        # 데이터베이스 모델
│   ├── strategy.py        # 차익거래 전략
│   ├── trader.py          # 실거래 모듈
│   ├── simulator.py       # 시뮬레이션 모듈
│   ├── backtester.py      # 백테스트 엔진
│   ├── ui.py             # 사용자 인터페이스
│   ├── technical_indicators.py  # 기술적 지표
│   └── exchanges/         # 거래소 어댑터들
│       ├── __init__.py
│       ├── base.py       # 베이스 거래소 클래스
│       ├── binance.py    # 바이낸스 어댑터
│       ├── bybit.py      # 바이비트 어댑터
│       ├── okx.py        # OKX 어댑터
│       └── bitget.py     # 비트겟 어댑터
├── tests/                 # 테스트 파일들
├── scripts/               # 디버그/유틸리티 스크립트
├── data/                  # 데이터 파일들
│   ├── arbot.db          # SQLite 데이터베이스
│   └── logs/             # 로그 파일들
├── docker/               # Docker 관련 파일들
├── run.py                # 실행 스크립트
├── config.json           # 메인 설정 파일
├── config.local.json     # 로컬 설정 파일
├── .env.example          # 환경변수 예시
├── requirements.txt      # Python 의존성
├── pyproject.toml        # 프로젝트 설정
└── setup.py             # 설치 스크립트
```

---

## 🎮 사용법

### UI 조작법
- **q**: 프로그램 종료
- **s**: 거래 시작/중지
- **r**: 화면 새로고침
- **Tab**: 탭 전환 (가격, 스프레드, 거래 기록 등)
- **↑/↓**: 목록 스크롤

### 주요 화면 구성
1. **Price Monitor**: 실시간 가격 모니터링
2. **Spread Analysis**: 거래소 간 스프레드 분석
3. **Trade History**: 거래 기록 및 수익률
4. **Balance**: 계정 잔고 현황
5. **Settings**: 설정 조정

---

## 🔧 고급 설정

### 거래소 추가 설정
각 거래소별로 세부 설정이 가능합니다:

```json
{
  "exchanges": {
    "binance": {
      "enabled": true,
      "arbitrage_enabled": true,
      "region": "global",
      "premium_baseline": 0.0
    }
  }
}
```

### 리스크 관리
```json
{
  "risk_management": {
    "max_drawdown_percent": 5.0,
    "stop_loss_percent": 2.0,
    "max_concurrent_trades": 3,
    "balance_threshold_percent": 10.0
  }
}
```

### 프리미엄 감지
지역별 프리미엄을 감지하여 비정상적인 스프레드를 필터링:

```json
{
  "arbitrage": {
    "premium_detection": {
      "enabled": true,
      "lookback_periods": 100,
      "min_samples": 50,
      "outlier_threshold": 2.0
    }
  }
}
```

---

## 🧩 확장 방법

### 새 거래소 추가
1. `exchanges/` 폴더에 새 거래소 파일 생성 (예: `exchanges/new_exchange.py`)
2. `BaseExchange` 클래스를 상속받아 구현
3. 필수 메서드 구현:
   - `connect_ws()`: WebSocket 연결
   - `get_orderbook()`: 호가창 정보
   - `place_order()`: 주문 실행
   - `cancel_order()`: 주문 취소
   - `get_balance()`: 잔고 조회

### 새 전략 추가
`strategy.py` 파일을 수정하여 새로운 차익거래 전략을 추가할 수 있습니다.

---

## 🐛 문제 해결

### 자주 발생하는 문제

1. **API 키 오류**
   ```
   해결책: .env 파일의 API 키와 시크릿이 올바른지 확인
   ```

2. **WebSocket 연결 실패**
   ```
   해결책: 인터넷 연결 확인 및 방화벽 설정 점검
   ```

3. **거래소 응답 없음**
   ```
   해결책: 거래소 서버 상태 확인 및 API 제한 확인
   ```

### 로그 확인
```bash
# 상세 로그 확인
tail -f arbot.log

# 디버그 모드 실행
LOG_LEVEL=DEBUG python main.py
```

---

## 🛡️ 주의사항 및 면책조항

⚠️ **중요한 주의사항**

1. **실거래 위험**: 이 소프트웨어는 실제 자금으로 거래를 수행합니다. 사용 전 반드시 시뮬레이션 모드로 충분히 테스트하세요.

2. **손실 가능성**: 암호화폐 거래는 높은 위험을 수반하며, 전체 투자금을 잃을 수 있습니다.

3. **Testnet 미사용**: 모든 데이터는 실제 거래소의 실시간 가격을 사용합니다.

4. **API 제한**: 각 거래소의 API 제한을 준수하세요.

5. **법적 준수**: 거주 지역의 암호화폐 거래 관련 법규를 확인하고 준수하세요.

**면책조항**: 이 소프트웨어의 사용으로 인한 모든 손실에 대해 개발자는 책임지지 않습니다. 사용자의 책임 하에 사용하세요.

---

## 🤝 기여하기

1. Fork 후 브랜치 생성
2. 변경사항 구현
3. 테스트 실행
4. Pull Request 제출

---

## 📄 라이센스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

## 📚 문서

**완전한 문서는 GitHub Pages에서 확인하세요:**

🌐 **[ArBot 공식 문서](https://finai6.github.io/arbot/)**

### 주요 문서 섹션

- 📋 **[빠른 시작 가이드](https://finai6.github.io/arbot/quickstart/)** - 5분 만에 시작하기
- ⚙️ **[설치 가이드](https://finai6.github.io/arbot/installation/)** - 상세 설치 방법
- 🎮 **[GUI 사용법](https://finai6.github.io/arbot/features/gui/)** - 인터페이스 완전 가이드
- 📊 **[트렌드 필터링](https://finai6.github.io/arbot/guide/trend-filtering/)** - 고급 필터링 전략
- 🛠️ **[설정 가이드](https://finai6.github.io/arbot/configuration/)** - 모든 설정 옵션
- 🏗️ **[아키텍처](https://finai6.github.io/arbot/technical/architecture/)** - 시스템 구조
- 🤝 **[기여 가이드](https://finai6.github.io/arbot/development/contributing/)** - 개발 참여 방법

---

## 📞 문의

- **개발자**: Euiyun Kim
- **GitHub**: [https://github.com/FinAI6/arbot](https://github.com/FinAI6/arbot)
- **이메일**: geniuskey@gmail.com
- **문서**: [https://finai6.github.io/arbot/](https://finai6.github.io/arbot/)

---

**⭐ 이 프로젝트가 도움이 되었다면 GitHub에서 스타를 눌러주세요!**
