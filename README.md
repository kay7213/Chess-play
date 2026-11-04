# ♟️ 오프라인 변형 체스 (Offline Variant Chess) with Lichess Opening Explorer

Python과 Tkinter를 기반으로 제작된 오프라인 변형 체스 게임입니다.  
최신 업데이트를 통해 **Lichess Opening Explorer API**를 연동하여, Standard 체스 모드에서 실시간 보드 포지션(FEN)에 기반한 마스터 대국의 오프닝 이름, 승패 통계, 추천 다음 수를 제공합니다.

---

## 🌟 주요 기능

### 1. 3가지 체스 게임 모드
- **⚔️ 일반 체스 (Standard)**: 정식 FIDE 체스 규칙을 준수하는 클래식 체스 (Lichess 오프닝 탐색기 지원)
- **🎲 체스960 (Fischer Random)**: 매 판 1열/8열의 기물이 무작위로 공정하게 배치되는 체스960 모드 (동적 캐슬링 지원)
- **⛰️ 언덕의 왕 (King of the Hill)**: 킹이 중앙 4칸(`d4`, `d5`, `e4`, `e5`)에 먼저 도달하면 즉시 승리하는 변형 체스

### 2. 정밀한 체스 규칙 구현
- **체크 및 체크메이트 / 스테일메이트**: 자살수 차단, 핀(Pin) 기물 보호, 체크 해소 수 강제
- **특수 규칙**:
  - 일반 체스 및 체스960 동적 캐슬링 ($O-O$, $O-O-O$)
  - 앙파상 (En Passant) 포획 및 좌표 추적
  - 폰 프로모션 (상대 끝 행 도달 시 퀸 자동 승급)
  - 3회 동형 반복(Threefold Repetition) 무승부
  - 50수 규칙(50-Move Rule) 무승부
  - 기물 부족(Insufficient Material) 무승부

### 3. Lichess Opening Explorer API 연동 (Standard 모드 전용)
- **실시간 FEN 변환 (`to_fen`)**: 보드 기물 배치, 현재 턴, 캐슬링 권한(`KQkq`), 앙파상 타깃(`e3`, `d6` 등), 하프무브 카운터, 풀무브 수를 완벽히 FEN 포맷으로 변환하여 API에 전달합니다.
- **오프닝 정보 표시**:
  - 오프닝 명칭 및 ECO 코드 (예: `[B00] King's Pawn Opening`)
  - 마스터 대국 승/무/패 비율 막대 그래프 및 총 대국 수
  - 추천 다음 수 (Top Moves) 순위 목록 (SAN 표기, 대국 수, 백승/무/흑승 비율)
- **네트워크 최적화 및 안정성**:
  - **중복 요청 방지 인메모리 캐시**: 한 번 조회한 FEN 포지션은 캐시되어 재방문 시 네트워크 통신 없이 즉각 표시됩니다.
  - **HTTP 429(Rate Limit) 대응**: API 한도 초과 시 최소 60초(1분) 쿨다운 대기를 적용하여 추가 요청을 방지합니다.
  - **Non-blocking 비동기 처리**: `threading`과 `queue.Queue`를 이용한 스레드 안전 비동기 파이프라인으로 체스 조작 중 UI 멈춤 현상(Freezing)이 전혀 없습니다.
  - **장애 격리**: API 오류(401 인증 필요, 네트워크 단절, 타임아웃 등)가 발생해도 우측 패널에 안내 문구만 표시되며 체스 게임 플레이는 100% 정상 작동합니다.

---

## 📁 프로젝트 파일 구성

| 파일명 | 역할 |
| :--- | :--- |
| [`main.py`](file:///C:/Programming/Week9-X/Chess-play/main.py) | 프로그램 진입점 및 윈도우 크기(`960x650`), 화면 중앙 정렬 설정 |
| [`chess_gui.py`](file:///C:/Programming/Week9-X/Chess-play/chess_gui.py) | Tkinter 캔버스 체스판 렌더링, 모드 선택 메뉴, 우측 오프닝 정보 패널 UI |
| [`chess_rules.py`](file:///C:/Programming/Week9-X/Chess-play/chess_rules.py) | 보드 상태 관리, 기물 이동 규칙, 승패/무승부 판정, FEN 변환(`to_fen`) |
| [`api_client.py`](file:///C:/Programming/Week9-X/Chess-play/api_client.py) | Lichess Masters Opening Explorer API 통신, 캐싱, 429 쿨다운 처리 |
| [`api-plan.md`](file:///C:/Programming/Week9-X/Chess-play/api-plan.md) | API 연동 요구사항 및 구현 기획서 |
| [`test_full_suite.py`](file:///C:/Programming/Week9-X/Chess-play/test_full_suite.py) | 체스 규칙, FEN, API 클라이언트, GUI 연동 종합 자동화 테스트 슈트 |
| [`README.md`](file:///C:/Programming/Week9-X/Chess-play/README.md) | 프로젝트 설명 및 사용 설명서 |

---

## 🚀 설치 및 실행 방법

### 1. 요구 사항
- Python 3.14 이상
- `uv` 패키지 관리자 (권장)

### 2. 패키지 설치
```bash
uv sync
```

### 3. 게임 실행
```bash
uv run main.py
```

### 4. (선택 사항) Lichess API 토큰 설정
Lichess Opening Explorer는 현재 정책상 개인 액세스 토큰(Personal Access Token) 인증을 권장합니다.  
토큰이 없어도 체스 게임은 정상적으로 동작하며 패널에 인증 안내가 표시됩니다. 마스터 데이터를 조회하려면 [Lichess API 토큰 발급 페이지](https://lichess.org/account/oauth/token)에서 토큰을 발급받은 후 환경 변수로 설정해 주세요.

**Windows PowerShell:**
```powershell
$env:LICHESS_API_TOKEN="lip_your_personal_token_here"
uv run main.py
```

**Linux / macOS:**
```bash
export LICHESS_API_TOKEN="lip_your_personal_token_here"
uv run main.py
```

---

## 🧪 테스트 실행

체스 규칙, FEN 변환, API 통신 및 예외 처리, 비동기 GUI 연동을 모두 검증하는 종합 테스트:
```bash
uv run python test_full_suite.py
```
모든 테스트가 통과하면 `모든 단위 및 통합 테스트 성공 완료!` 메시지가 출력됩니다.
