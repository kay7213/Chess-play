# -*- coding: utf-8 -*-
"""Lichess Opening Explorer API 클라이언트 모듈."""

import os
import threading
import time
from typing import Any, Dict, List, Optional
import requests


class LichessAPIClient:
    """Lichess Masters Opening Explorer API와 통신하는 클라이언트 클래스.
    
    기능:
    - FEN 기반 오프닝 및 마스터 대국 통계 조회
    - 동일 FEN 중복 요청 방지 (인메모리 캐시 및 진행 중 요청 락)
    - HTTP 429(Rate Limit) 대응: 최소 1분(60초) 대기 쿨다운 적용
    - 토큰 인증(Bearer) 선택적 지원 및 비인증/인증 에러 안전 처리
    """

    DEFAULT_BASE_URL = "https://explorer.lichess.ovh/masters"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        token: Optional[str] = None,
        timeout: float = 5.0,
    ) -> None:
        self.base_url = base_url
        self.token = token or os.environ.get("LICHESS_API_TOKEN", "").strip() or None
        self.timeout = timeout

        # 중복 요청 방지 캐시: {fen: result_dict}
        self._cache: Dict[str, Dict[str, Any]] = {}
        # 진행 중인 요청 추적 및 스레드 락
        self._in_flight: set = set()
        self._lock = threading.Lock()

        # Rate Limit (HTTP 429) 대기 타임스탬프
        self.rate_limited_until: float = 0.0

    def set_token(self, token: Optional[str]) -> None:
        """API 토큰을 설정합니다."""
        self.token = token.strip() if token else None

    def get_remaining_cooldown(self) -> int:
        """HTTP 429로 인한 남은 쿨다운 대기 시간(초)을 반환합니다."""
        remaining = self.rate_limited_until - time.time()
        return max(0, int(remaining))

    def fetch_masters_opening(
        self,
        fen: str,
        moves_count: int = 5,
        top_games_count: int = 0
    ) -> Dict[str, Any]:
        """FEN 포지션에 대한 Lichess 마스터 오프닝 정보를 조회합니다.
        
        네트워크 에러, 401 인증 필요, 429 한도 초과 등 모든 예외 상황을
        안전하게 딕셔너리로 반환하여 호출 측이 중단되지 않도록 합니다.
        """
        fen_clean = fen.strip()

        # 1. 429 Rate Limit 쿨다운 확인
        cooldown = self.get_remaining_cooldown()
        if cooldown > 0:
            return {
                "success": False,
                "cached": False,
                "error_type": "rate_limited",
                "message": f"요청 한도 초과 (HTTP 429): {cooldown}초 후 재시도 가능",
                "retry_after": cooldown,
                "opening": None,
                "stats": {"white": 0, "draws": 0, "black": 0, "total": 0},
                "moves": [],
            }

        # 2. 동일 FEN 캐시 확인 (중복 요청 방지)
        with self._lock:
            if fen_clean in self._cache:
                cached_data = dict(self._cache[fen_clean])
                cached_data["cached"] = True
                return cached_data

            if fen_clean in self._in_flight:
                # 이미 동일 FEN이 요청 중이면 대기 중 상태 반환
                return {
                    "success": False,
                    "cached": False,
                    "error_type": "in_flight",
                    "message": "해당 포지션의 조회가 이미 진행 중입니다.",
                    "opening": None,
                    "stats": {"white": 0, "draws": 0, "black": 0, "total": 0},
                    "moves": [],
                }
            self._in_flight.add(fen_clean)

        # 3. HTTP 요청 수행
        try:
            headers = {
                "User-Agent": "OfflineChessVariant/1.0 (Python Tkinter Client)",
                "Accept": "application/json",
            }
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            params = {
                "fen": fen_clean,
                "moves": moves_count,
                "topGames": top_games_count,
            }

            resp = requests.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )

            # HTTP 429 Too Many Requests 처리 (최소 1분 = 60초 대기)
            if resp.status_code == 429:
                retry_header = resp.headers.get("Retry-After", "")
                try:
                    retry_sec = int(retry_header)
                except (ValueError, TypeError):
                    retry_sec = 60
                wait_time = max(60, retry_sec)
                self.rate_limited_until = time.time() + wait_time

                return {
                    "success": False,
                    "cached": False,
                    "error_type": "rate_limited",
                    "message": f"요청 한도 초과 (HTTP 429): {wait_time}초 동안 대기합니다.",
                    "retry_after": wait_time,
                    "opening": None,
                    "stats": {"white": 0, "draws": 0, "black": 0, "total": 0},
                    "moves": [],
                }

            # HTTP 401 Unauthorized 처리
            if resp.status_code == 401:
                return {
                    "success": False,
                    "cached": False,
                    "error_type": "auth_required",
                    "message": "Lichess API 토큰 인증이 필요합니다 (HTTP 401).",
                    "opening": None,
                    "stats": {"white": 0, "draws": 0, "black": 0, "total": 0},
                    "moves": [],
                }

            # 기타 HTTP 오류 (4xx, 5xx)
            if not resp.ok:
                return {
                    "success": False,
                    "cached": False,
                    "error_type": "http_error",
                    "message": f"API 응답 오류 (HTTP {resp.status_code})",
                    "opening": None,
                    "stats": {"white": 0, "draws": 0, "black": 0, "total": 0},
                    "moves": [],
                }

            # JSON 파싱 및 데이터 정제
            raw = resp.json()
            white = raw.get("white", 0)
            draws = raw.get("draws", 0)
            black = raw.get("black", 0)
            total = white + draws + black

            parsed_moves: List[Dict[str, Any]] = []
            for m in raw.get("moves", []):
                m_white = m.get("white", 0)
                m_draws = m.get("draws", 0)
                m_black = m.get("black", 0)
                m_total = m_white + m_draws + m_black
                parsed_moves.append({
                    "san": m.get("san", ""),
                    "uci": m.get("uci", ""),
                    "averageRating": m.get("averageRating", 0),
                    "white": m_white,
                    "draws": m_draws,
                    "black": m_black,
                    "total": m_total,
                })

            result = {
                "success": True,
                "cached": False,
                "error_type": None,
                "message": "조회 성공",
                "opening": raw.get("opening"),
                "stats": {
                    "white": white,
                    "draws": draws,
                    "black": black,
                    "total": total,
                },
                "moves": parsed_moves,
            }

            # 캐시에 보관
            with self._lock:
                self._cache[fen_clean] = result

            return result

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "cached": False,
                "error_type": "timeout",
                "message": "API 요청 시간 초과 (Timeout)",
                "opening": None,
                "stats": {"white": 0, "draws": 0, "black": 0, "total": 0},
                "moves": [],
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "cached": False,
                "error_type": "network_error",
                "message": f"네트워크 통신 오류: {e.__class__.__name__}",
                "opening": None,
                "stats": {"white": 0, "draws": 0, "black": 0, "total": 0},
                "moves": [],
            }
        except Exception as e:
            return {
                "success": False,
                "cached": False,
                "error_type": "unexpected_error",
                "message": f"예기치 못한 오류: {str(e)}",
                "opening": None,
                "stats": {"white": 0, "draws": 0, "black": 0, "total": 0},
                "moves": [],
            }
        finally:
            with self._lock:
                self._in_flight.discard(fen_clean)
