# -*- coding: utf-8 -*-
"""체스 GUI 인터페이스 모듈 (Tkinter 기반)."""

import tkinter as tk
from tkinter import messagebox
from typing import List, Optional, Tuple

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
            ("⚔️  일반 체스 (Standard)", "standard", "체크메이트 승리 규칙의 클래식 체스"),
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
        """체스판 캔버스와 상태 표시줄, 제어 버튼을 구성합니다."""
        self.top_bar = tk.Frame(self.game_frame, bg="#2E3440", pady=8)
        self.top_bar.pack(fill="x")
        self.mode_label = tk.Label(self.top_bar, text="", font=("맑은 고딕", 11, "bold"), fg="#88C0D0", bg="#2E3440")
        self.mode_label.pack()
        self.turn_label = tk.Label(self.top_bar, text="", font=("맑은 고딕", 13, "bold"), fg="#ECEFF4", bg="#2E3440")
        self.turn_label.pack(pady=3)

        self.canvas = tk.Canvas(self.game_frame, width=512, height=512, bg="#2E3440", highlightthickness=0)
        self.canvas.pack(padx=20, pady=8)
        self.canvas.bind("<Button-1>", self.on_board_click)

        bottom_bar = tk.Frame(self.game_frame, bg="#2E3440", pady=10)
        bottom_bar.pack(fill="x")
        tk.Button(
            bottom_bar, text="🔄 게임 재시작", font=("맑은 고딕", 10, "bold"), bg="#4C566A", fg="#ECEFF4",
            command=self.restart_current_game, cursor="hand2", padx=12, pady=4, relief="flat"
        ).pack(side="left", padx=25)
        tk.Button(
            bottom_bar, text="📋 모드 선택 화면", font=("맑은 고딕", 10, "bold"), bg="#5E81AC", fg="#ECEFF4",
            command=self.show_menu, cursor="hand2", padx=12, pady=4, relief="flat"
        ).pack(side="right", padx=25)

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

    def restart_current_game(self) -> None:
        """현재 모드로 보드 및 기물을 다시 배치합니다."""
        self.game.reset()
        self.selected, self.valid_moves = None, []
        self.update_status()
        self.draw_board()

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
            if moved and self.game.winner:
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
