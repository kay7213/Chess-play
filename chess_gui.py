# -*- coding: utf-8 -*-
"""체스 GUI 인터페이스 모듈 (Tkinter 기반)."""

import queue
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Any, Dict, List, Optional, Tuple

from api_client import LichessAPIClient
from chess_rules import CENTER_SQUARES, ChessGame

PIECE_ICONS = {
    ("W", "K"): "♔", ("W", "Q"): "♕", ("W", "R"): "♖",
    ("W", "B"): "♗", ("W", "N"): "♘", ("W", "P"): "♙",
    ("B", "K"): "♚", ("B", "Q"): "♛", ("B", "R"): "♜",
    ("B", "B"): "♝", ("B", "N"): "♞", ("B", "P"): "♟",
}
MODE_NAMES = {
    "standard": "일반 체스 (Standard)",
    "chess960": "체스960 (Fischer Random)",
    "koth": "언덕의 왕 (King of the Hill)",
}


class ChessGUI:
    """Tkinter를 이용한 체스 그래픽 사용자 인터페이스 관리 클래스."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.game = ChessGame()
        self.selected: Optional[Tuple[int, int]] = None
        self.valid_moves: List[Tuple[int, int]] = []

        # Lichess API 클라이언트 및 요청 추적
        self.api_client = LichessAPIClient()
        self._request_counter = 0
        self.api_queue: queue.Queue = queue.Queue()
        self._poll_api_queue()

        self.root.title("오프라인 변형 체스")
        self.root.configure(bg="#2E3440")
        self.menu_frame = tk.Frame(self.root, bg="#2E3440", padx=30, pady=30)
        self.game_frame = tk.Frame(self.root, bg="#2E3440")

        self.setup_menu_view()
        self.setup_game_view()
        self.show_menu()

    def setup_menu_view(self) -> None:
        """게임 시작 시 모드를 고르는 메인 메뉴 화면을 구성합니다."""
        tk.Label(
            self.menu_frame, text="♟️ 오프라인 변형 체스", font=("맑은 고딕", 22, "bold"),
            fg="#ECEFF4", bg="#2E3440"
        ).pack(pady=(0, 10))
        tk.Label(
            self.menu_frame, text="플레이할 체스 모드를 선택해주세요.", font=("맑은 고딕", 12),
            fg="#D8DEE9", bg="#2E3440"
        ).pack(pady=(0, 20))

        modes = [
            ("⚔️  일반 체스 (Standard)", "standard", "체크메이트 승리 규칙의 클래식 체스 (Lichess 오프닝 연동)"),
            ("🎲  체스960 (Chess960)", "chess960", "매 판 1열/8열 기물이 무작위로 배치"),
            ("⛰️  언덕의 왕 (King of the Hill)", "koth", "킹이 중앙 4칸(d4,e4,d5,e5)에 도달 시 즉시 승리"),
        ]
        for title_text, mode_key, sub_text in modes:
            frame = tk.Frame(self.menu_frame, bg="#3B4252", padx=10, pady=8, bd=1, relief="ridge")
            frame.pack(fill="x", pady=6)
            tk.Button(
                frame, text=title_text, font=("맑은 고딕", 12, "bold"), bg="#4C566A", fg="#ECEFF4",
                activebackground="#5E81AC", relief="flat", cursor="hand2",
                command=lambda m=mode_key: self.start_game(m),
            ).pack(fill="x")
            tk.Label(frame, text=sub_text, font=("맑은 고딕", 9), fg="#E5E9F0", bg="#3B4252").pack(pady=(2, 0))

    def setup_game_view(self) -> None:
        """좌측 체스판과 우측 오프닝 정보 패널을 포함하는 게임 화면을 구성합니다."""
        # 메인 좌우 2분할 컨테이너
        main_container = tk.Frame(self.game_frame, bg="#2E3440")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # ---------------- 좌측 체스판 영역 ----------------
        left_area = tk.Frame(main_container, bg="#2E3440")
        left_area.pack(side="left", padx=(0, 10), fill="y")

        self.top_bar = tk.Frame(left_area, bg="#2E3440", pady=4)
        self.top_bar.pack(fill="x")
        self.mode_label = tk.Label(self.top_bar, text="", font=("맑은 고딕", 11, "bold"), fg="#88C0D0", bg="#2E3440")
        self.mode_label.pack()
        self.turn_label = tk.Label(self.top_bar, text="", font=("맑은 고딕", 13, "bold"), fg="#ECEFF4", bg="#2E3440")
        self.turn_label.pack(pady=2)

        self.canvas = tk.Canvas(left_area, width=512, height=512, bg="#2E3440", highlightthickness=0)
        self.canvas.pack(padx=10, pady=4)
        self.canvas.bind("<Button-1>", self.on_board_click)

        bottom_bar = tk.Frame(left_area, bg="#2E3440", pady=8)
        bottom_bar.pack(fill="x")
        tk.Button(
            bottom_bar, text="🔄 게임 재시작", font=("맑은 고딕", 10, "bold"), bg="#4C566A", fg="#ECEFF4",
            command=self.restart_current_game, cursor="hand2", padx=12, pady=4, relief="flat"
        ).pack(side="left", padx=15)
        tk.Button(
            bottom_bar, text="📋 모드 선택 화면", font=("맑은 고딕", 10, "bold"), bg="#5E81AC", fg="#ECEFF4",
            command=self.show_menu, cursor="hand2", padx=12, pady=4, relief="flat"
        ).pack(side="right", padx=15)

        # ---------------- 우측 오프닝 탐색기 패널 ----------------
        self.right_panel = tk.Frame(main_container, bg="#3B4252", padx=15, pady=12, bd=1, relief="ridge", width=380)
        self.right_panel.pack(side="right", fill="both", expand=True)
        self.right_panel.pack_propagate(False)

        # 1. 패널 타이틀
        tk.Label(
            self.right_panel, text="📖 Lichess 오프닝 탐색기", font=("맑은 고딕", 13, "bold"),
            fg="#ECEFF4", bg="#3B4252"
        ).pack(anchor="w")
        tk.Label(
            self.right_panel, text="마스터 대국 데이터베이스 (Masters)", font=("맑은 고딕", 9),
            fg="#88C0D0", bg="#3B4252"
        ).pack(anchor="w", pady=(0, 8))

        # 2. 오프닝 이름 카드
        self.opening_card = tk.Frame(self.right_panel, bg="#434C5E", padx=10, pady=8, bd=1, relief="flat")
        self.opening_card.pack(fill="x", pady=4)

        self.opening_eco_label = tk.Label(
            self.opening_card, text="", font=("맑은 고딕", 9, "bold"), fg="#EBCB8B", bg="#434C5E"
        )
        self.opening_eco_label.pack(anchor="w")
        self.opening_name_label = tk.Label(
            self.opening_card, text="오프닝 정보를 불러오는 중...", font=("맑은 고딕", 11, "bold"),
            fg="#ECEFF4", bg="#434C5E", wraplength=340, justify="left"
        )
        self.opening_name_label.pack(anchor="w")

        # 3. 승패 통계 카드
        stats_frame = tk.Frame(self.right_panel, bg="#3B4252", pady=4)
        stats_frame.pack(fill="x", pady=4)

        self.stats_total_label = tk.Label(
            stats_frame, text="총 대국 수: -", font=("맑은 고딕", 10, "bold"),
            fg="#ECEFF4", bg="#3B4252"
        )
        self.stats_total_label.pack(anchor="w")

        # 승패 비율 막대 바
        self.win_bar_canvas = tk.Canvas(stats_frame, width=340, height=16, bg="#2E3440", highlightthickness=0)
        self.win_bar_canvas.pack(fill="x", pady=4)

        self.stats_detail_label = tk.Label(
            stats_frame, text="백 승: - | 무승부: - | 흑 승: -", font=("맑은 고딕", 9),
            fg="#D8DEE9", bg="#3B4252"
        )
        self.stats_detail_label.pack(anchor="w")

        # 4. 추천 다음 수 목록
        tk.Label(
            self.right_panel, text="💡 추천 다음 수 (Top Moves)", font=("맑은 고딕", 10, "bold"),
            fg="#88C0D0", bg="#3B4252"
        ).pack(anchor="w", pady=(8, 2))

        # 표 헤더
        moves_header = tk.Frame(self.right_panel, bg="#2E3440", padx=6, pady=3)
        moves_header.pack(fill="x")
        tk.Label(moves_header, text="수", width=6, anchor="w", font=("맑은 고딕", 9, "bold"), fg="#ECEFF4", bg="#2E3440").pack(side="left")
        tk.Label(moves_header, text="대국 수", width=9, anchor="e", font=("맑은 고딕", 9, "bold"), fg="#ECEFF4", bg="#2E3440").pack(side="left", padx=5)
        tk.Label(moves_header, text="백% / 무% / 흑%", anchor="center", font=("맑은 고딕", 9, "bold"), fg="#ECEFF4", bg="#2E3440").pack(side="right")

        # 추천 수 목록이 들어갈 컨테이너
        self.moves_container = tk.Frame(self.right_panel, bg="#3B4252")
        self.moves_container.pack(fill="x", pady=(2, 6))

        # 5. 상태 및 알림 메시지 영역 (에러, 쿨다운 등)
        self.status_msg_label = tk.Label(
            self.right_panel, text="", font=("맑은 고딕", 9),
            fg="#D8DEE9", bg="#3B4252", wraplength=340, justify="left"
        )
        self.status_msg_label.pack(side="bottom", fill="x", pady=(5, 0))

    def show_menu(self) -> None:
        """메뉴 화면을 띄우고 게임 화면을 숨깁니다."""
        self.game_frame.pack_forget()
        self.menu_frame.pack(expand=True, fill="both")

    def start_game(self, mode: str) -> None:
        """선택한 모드로 체스 게임을 시작하고 보드 화면을 표시합니다."""
        self.game.reset(mode)
        self.selected, self.valid_moves = None, []
        self.menu_frame.pack_forget()
        self.game_frame.pack(expand=True, fill="both")
        self.update_status()
        self.draw_board()
        self.fetch_opening_info()

    def restart_current_game(self) -> None:
        """현재 모드로 보드 및 기물을 다시 배치합니다."""
        self.game.reset()
        self.selected, self.valid_moves = None, []
        self.update_status()
        self.draw_board()
        self.fetch_opening_info()

    def update_status(self) -> None:
        """현재 턴과 체크 여부를 상태 표시줄에 갱신합니다."""
        self.mode_label.config(text=f"[ 현재 모드: {MODE_NAMES.get(self.game.mode, '')} ]")
        turn_str = "백색 (White 턴)" if self.game.current_turn == "W" else "흑색 (Black 턴)"
        if self.game.is_in_check(self.game.current_turn, self.game.board):
            self.turn_label.config(text=f"현재 차례: {turn_str} ⚠️ [체크!]", fg="#E06A55")
        else:
            self.turn_label.config(text=f"현재 차례: {turn_str}", fg="#ECEFF4")

    def on_board_click(self, event: tk.Event) -> None:
        """체스판 클릭 좌표를 감지하여 기물 선택 및 이동을 처리합니다."""
        if self.game.winner is not None:
            return
        c, r = event.x // 64, event.y // 64
        if not self.game.in_bounds(r, c):
            return

        if self.selected and (r, c) in self.valid_moves:
            moved = self.game.make_move(self.selected, (r, c))
            self.selected, self.valid_moves = None, []
            self.draw_board()
            self.update_status()
            if moved:
                self.fetch_opening_info()
                if self.game.winner:
                    if self.game.winner == "Draw":
                        messagebox.showinfo("게임 종료", f"🤝 무승부!\n\n{self.game.win_reason}")
                    else:
                        winner_title = "백색(White)" if self.game.winner == "W" else "흑색(Black)"
                        messagebox.showinfo("게임 종료", f"🏆 {winner_title} 승리!\n\n{self.game.win_reason}")
            return

        target = self.game.board[r][c]
        if target is not None and target[0] == self.game.current_turn:
            self.selected = (r, c)
            self.valid_moves = self.game.get_valid_moves(r, c)
        else:
            self.selected, self.valid_moves = None, []
        self.draw_board()

    def draw_board(self) -> None:
        """8x8 체스판, 특수 칸(언덕), 기물 및 이동 가능 표시를 그립니다."""
        self.canvas.delete("all")
        sq_size = 64
        for r in range(8):
            for c in range(8):
                x1, y1 = c * sq_size, r * sq_size
                x2, y2 = x1 + sq_size, y1 + sq_size
                is_light = (r + c) % 2 == 0
                bg = "#EEEED2" if is_light else "#769656"
                if self.game.mode == "koth" and (r, c) in CENTER_SQUARES:
                    bg = "#E6C280" if is_light else "#B89758"
                if self.selected == (r, c):
                    bg = "#F6F669"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=bg, outline="")

                if self.game.mode == "koth" and (r, c) in CENTER_SQUARES:
                    self.canvas.create_text(x1 + 10, y1 + 10, text="⛰", font=("Segoe UI Symbol", 8), fill="#8B5A2B")

                piece_info = self.game.board[r][c]
                if piece_info:
                    icon = PIECE_ICONS.get(piece_info, "")
                    fill_color = "#FFFFFF" if piece_info[0] == "W" else "#1F2328"
                    self.canvas.create_text(x1 + 33, y1 + 33, text=icon, font=("Segoe UI Symbol", 32, "bold"), fill="#000000")
                    self.canvas.create_text(x1 + 32, y1 + 32, text=icon, font=("Segoe UI Symbol", 32, "bold"), fill=fill_color)

                if (r, c) in self.valid_moves:
                    if piece_info:
                        ring_color = "#88C0D0" if piece_info[0] == self.game.current_turn else "#E06A55"
                        self.canvas.create_oval(x1 + 6, y1 + 6, x2 - 6, y2 - 6, outline=ring_color, width=4)
                    else:
                        self.canvas.create_oval(x1 + 24, y1 + 24, x2 - 24, y2 - 24, fill="#5C7C3E", outline="")

    # ---------------- Lichess 오프닝 탐색기 연동 로직 ----------------

    def fetch_opening_info(self) -> None:
        """현재 체스판 상태를 분석하여 Lichess API로 오프닝 정보를 비동기 조회합니다."""
        # 1. Standard 모드에서만 API 사용
        if self.game.mode != "standard":
            self._render_non_standard_mode()
            return

        current_fen = self.game.to_fen()
        self._request_counter += 1
        req_id = self._request_counter

        # 2. 429 쿨다운 대기 확인
        cooldown = self.api_client.get_remaining_cooldown()
        if cooldown > 0:
            self._render_status(f"⚠️ 요청 한도 초과 (HTTP 429): {cooldown}초 대기 중", fg="#E06A55")
            return

        # 3. 동일 FEN 캐시 확인 (중복 요청 방지)
        if current_fen in self.api_client._cache:
            cached_data = self.api_client.fetch_masters_opening(current_fen)
            self._render_opening_result(cached_data, current_fen)
            return

        # 4. 로딩 상태 표시
        self._render_loading()

        # 5. 비동기 스레드로 API 호출하여 GUI 멈춤 방지 (Thread-safe Queue 활용)
        def worker() -> None:
            res = self.api_client.fetch_masters_opening(current_fen)
            self.api_queue.put((res, req_id, current_fen))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_api_queue(self) -> None:
        """백그라운드 스레드에서 전달된 API 결과를 메인 스레드에서 안전하게 수신합니다."""
        while not self.api_queue.empty():
            try:
                result, req_id, fen = self.api_queue.get_nowait()
                self._on_opening_response_received(result, req_id, fen)
            except queue.Empty:
                break
        self.root.after(50, self._poll_api_queue)

    def _on_opening_response_received(self, result: Dict[str, Any], req_id: int, fen: str) -> None:
        """비동기 API 응답을 수신하여 유효한 경우 UI를 갱신합니다."""
        # 이후 다른 수가 착수되었거나 현재 보드와 FEN이 다르면 무시 (레이스 컨디션 방지)
        if req_id != self._request_counter or self.game.to_fen() != fen:
            return
        self._render_opening_result(result, fen)

    def _render_non_standard_mode(self) -> None:
        """Standard 모드가 아닐 때의 패널 화면을 구성합니다."""
        self.opening_eco_label.config(text="")
        self.opening_name_label.config(text="오프닝 탐색기 미지원")
        self.stats_total_label.config(text="총 대국 수: -")
        self._clear_win_bar()
        self.stats_detail_label.config(text="")
        self._clear_moves_list()
        self._render_status("ℹ️ 오프닝 탐색기는 Standard 체스 모드에서만 작동합니다.", fg="#D8DEE9")

    def _render_loading(self) -> None:
        """조회 중 화면을 표시합니다."""
        self._render_status("⏳ Lichess 마스터 대국 데이터 조회 중...", fg="#88C0D0")

    def _render_status(self, text: str, fg: str = "#D8DEE9") -> None:
        """하단 상태 라벨을 갱신합니다."""
        self.status_msg_label.config(text=text, fg=fg)

    def _clear_win_bar(self) -> None:
        """승패 비율 바를 비웁니다."""
        self.win_bar_canvas.delete("all")

    def _clear_moves_list(self) -> None:
        """추천 수 목록 위젯을 초기화합니다."""
        for widget in self.moves_container.winfo_children():
            widget.destroy()

    def _render_opening_result(self, result: Dict[str, Any], fen: str) -> None:
        """API 결과 데이터를 우측 패널에 렌더링합니다."""
        self._clear_moves_list()

        # 1. API 실패 또는 오류 발생 시
        if not result.get("success", False):
            err_type = result.get("error_type")
            msg = result.get("message", "오프닝 정보를 불러오지 못했습니다.")
            self.opening_eco_label.config(text="")
            self.opening_name_label.config(text="데이터 조회 실패")
            self.stats_total_label.config(text="총 대국 수: -")
            self._clear_win_bar()
            self.stats_detail_label.config(text="")

            if err_type == "auth_required":
                tip = "⚠️ Lichess API 인증 필요 (HTTP 401)\n※ 인증 없이도 체스 게임은 정상 플레이됩니다."
                self._render_status(tip, fg="#EBCB8B")
            elif err_type == "rate_limited":
                self._render_status(f"⚠️ {msg}", fg="#E06A55")
            else:
                self._render_status(f"⚠️ {msg}\n※ 체스 게임은 정상 플레이 가능합니다.", fg="#E06A55")
            return

        # 2. 오프닝 이름 정보 렌더링
        opening = result.get("opening")
        if opening and opening.get("name"):
            eco = opening.get("eco", "")
            name = opening.get("name", "")
            self.opening_eco_label.config(text=f"ECO: {eco}" if eco else "")
            self.opening_name_label.config(text=name)
        else:
            self.opening_eco_label.config(text="")
            self.opening_name_label.config(text="미등록 / 비정형 오프닝 포지션")

        # 3. 전체 승패 통계 렌더링
        stats = result.get("stats", {})
        total = stats.get("total", 0)
        white = stats.get("white", 0)
        draws = stats.get("draws", 0)
        black = stats.get("black", 0)

        if total > 0:
            w_pct = (white / total) * 100
            d_pct = (draws / total) * 100
            b_pct = (black / total) * 100

            self.stats_total_label.config(text=f"총 마스터 대국: {total:,}판")
            self.stats_detail_label.config(
                text=f"백 {w_pct:.1f}% ({white:,}) | 무 {d_pct:.1f}% ({draws:,}) | 흑 {b_pct:.1f}% ({black:,})"
            )
            # 승패 막대 그리기
            self.win_bar_canvas.delete("all")
            bar_w = 340
            w_width = int(bar_w * (white / total))
            d_width = int(bar_w * (draws / total))
            b_width = bar_w - w_width - d_width

            x = 0
            if w_width > 0:
                self.win_bar_canvas.create_rectangle(x, 0, x + w_width, 16, fill="#ECEFF4", outline="")
                x += w_width
            if d_width > 0:
                self.win_bar_canvas.create_rectangle(x, 0, x + d_width, 16, fill="#88C0D0", outline="")
                x += d_width
            if b_width > 0:
                self.win_bar_canvas.create_rectangle(x, 0, x + b_width, 16, fill="#2E3440", outline="")
        else:
            self.stats_total_label.config(text="총 마스터 대국: 0판")
            self._clear_win_bar()
            self.stats_detail_label.config(text="마스터 대국 데이터가 존재하지 않습니다.")

        # 4. 추천 다음 수 목록 렌더링
        moves = result.get("moves", [])
        if not moves:
            empty_lbl = tk.Label(
                self.moves_container, text="추천할 다음 수가 없습니다.",
                font=("맑은 고딕", 9), fg="#D8DEE9", bg="#3B4252"
            )
            empty_lbl.pack(pady=4)
        else:
            for idx, m in enumerate(moves[:6]):
                m_san = m.get("san", "-")
                m_total = m.get("total", 0)
                m_white = m.get("white", 0)
                m_draws = m.get("draws", 0)
                m_black = m.get("black", 0)

                if m_total > 0:
                    mw_pct = int(round((m_white / m_total) * 100))
                    md_pct = int(round((m_draws / m_total) * 100))
                    mb_pct = int(round((m_black / m_total) * 100))
                    pct_str = f"{mw_pct}% / {md_pct}% / {mb_pct}%"
                else:
                    pct_str = "- / - / -"

                row_bg = "#434C5E" if idx % 2 == 0 else "#3B4252"
                row_frame = tk.Frame(self.moves_container, bg=row_bg, padx=6, pady=4)
                row_frame.pack(fill="x", pady=1)

                tk.Label(row_frame, text=m_san, width=6, anchor="w", font=("맑은 고딕", 9, "bold"), fg="#ECEFF4", bg=row_bg).pack(side="left")
                tk.Label(row_frame, text=f"{m_total:,}", width=9, anchor="e", font=("맑은 고딕", 9), fg="#D8DEE9", bg=row_bg).pack(side="left", padx=5)
                tk.Label(row_frame, text=pct_str, anchor="center", font=("맑은 고딕", 9), fg="#EBCB8B", bg=row_bg).pack(side="right")

        # 5. 상태 표시 갱신
        cached_tag = " (캐시됨)" if result.get("cached") else ""
        self._render_status(f"✅ 오프닝 분석 완료{cached_tag}", fg="#A3BE8C")
