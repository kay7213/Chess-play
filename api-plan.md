# Chess-play API 적용 기획안

## 1. 프로젝트 개요
기존 Chess-play는 Python과 Tkinter를 이용한 체스 프로그램입니다.  
이번 업데이트에서는 Lichess Opening Explorer API를 연동하여 현재 체스 포지션에 대한 오프닝 정보를 조회하는 기능을 추가합니다.

## 2. API 선정 및 사양
- **API 이름**: Lichess Opening Explorer (Masters Database)
- **제공자**: Lichess
- **API 주소**: `https://explorer.lichess.ovh/masters` (및 `https://explorer.lichess.org/masters`)
- **데이터**: 2200+ 레이팅 마스터 체스 대국 데이터
- **통신 방식**: HTTP GET
- **응답 형식**: JSON
- **인증**:
  - 공식 OpenAPI 사양(`security: OAuth2`)에 따라 Personal Access Token 지원 (`Authorization: Bearer <token>`)
  - 토큰 미제공 또는 인증 실패(HTTP 401) 시에도 체스 게임 플레이는 정상 작동하도록 장애 격리

## 3. 주요 기능
1. **FEN 변환 (`to_fen`)**:
   - 현재 체스판의 기물 배치, 현재 차례, 캐슬링 권한(KQkq), 앙파상 타깃 좌표, 하프무브 카운터, 풀무브 수를 FEN 표준에 맞게 변환합니다.
2. **오프닝 및 마스터 대국 데이터 조회**:
   - 변환된 FEN을 API에 전달하여 오프닝 이름(ECO 코드), 마스터 대국 승/무/패 통계, 추천 다음 수를 JSON으로 수신합니다.
3. **GUI 정보 시각화**:
   - 우측 패널에 오프닝 이름, 전체 승패 비율 막대 바, 추천 다음 수(Top Moves) 순위 목록을 표시합니다.
4. **Standard 모드 한정 작동**:
   - 일반 체스(Standard) 모드에서만 API를 호출하며, 체스960 및 KOTH 모드에서는 안내 문구를 표시하고 불필요한 호출을 방지합니다.
5. **네트워크 최적화 및 Rate Limit 대응**:
   - **중복 요청 방지**: 동일 FEN 요청에 대해 인메모리 캐시를 적용하여 불필요한 네트워크 트래픽을 차단합니다.
   - **HTTP 429 대응**: 요청 한도 초과 시 최소 60초(1분) 쿨다운 대기를 적용합니다.
6. **비동기 스레딩 (Non-blocking UI)**:
   - Python 3.14 호환 `queue.Queue` 기반 스레드 안전 비동기 파이프라인을 구축하여 네트워크 통신 중에도 체스 조작이 전혀 끊기지 않습니다.
7. **오류 안전 처리 (Graceful Degradation)**:
   - 네트워크 단절, 타임아웃, 401 인증 필요 등의 상황에서도 에러 안내만 표시하고 기존 체스 게임은 100% 정상 플레이됩니다.

## 4. 개발 환경
- Python 3.14
- Tkinter
- UV (패키지 관리자)
- `requests` (HTTP 통신 라이브러리)
- JSON

## 5. 파일 구성
- [`api_client.py`](file:///C:/Programming/Week9-X/Chess-play/api_client.py): API 요청 및 응답 처리, 캐싱, 429 쿨다운
- [`api-plan.md`](file:///C:/Programming/Week9-X/Chess-play/api-plan.md): API 적용 기획안
- [`chess_gui.py`](file:///C:/Programming/Week9-X/Chess-play/chess_gui.py): 체스판 렌더링 및 API 결과 우측 패널 표시
- [`chess_rules.py`](file:///C:/Programming/Week9-X/Chess-play/chess_rules.py): 기존 체스 규칙 및 FEN 변환(`to_fen`)
- [`main.py`](file:///C:/Programming/Week9-X/Chess-play/main.py): 프로그램 실행 진입점 및 창 크기 설정
- [`test_full_suite.py`](file:///C:/Programming/Week9-X/Chess-play/test_full_suite.py): 규칙, FEN, API, GUI 통합 테스트 슈트
- [`README.md`](file:///C:/Programming/Week9-X/Chess-play/README.md): 프로젝트 설명 및 실행 방법

## 6. 기대 효과
기존 체스 프로그램에 실제 체스 대국 데이터를 활용한 오프닝 탐색 기능을 추가함으로써, 사용자는 현재 포지션에서 자주 사용되는 다음 수와 실제 대국 통계를 시각적으로 확인하고 체스 오프닝 학습 효과를 얻을 수 있습니다.
