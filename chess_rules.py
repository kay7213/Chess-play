# -*- coding: utf-8 -*-
"""체스 게임 규칙 및 특수 룰 처리 모듈."""
import random
from typing import List, Optional, Set, Tuple

CENTER_SQUARES: Set[Tuple[int, int]] = {(3, 3), (3, 4), (4, 3), (4, 4)}


class ChessGame:
    """체스 보드 상태, 기물 이동, 특수 규칙 및 승패 판정을 총괄하는 클래스."""

    def __init__(self, mode: str = "standard") -> None:
        self.mode = mode
        self.initial_back: List[str] = []
        self.board: List[List[Optional[Tuple[str, str]]]] = []
        self.current_turn, self.winner, self.win_reason = "W", None, ""
        self.ep_target: Optional[Tuple[int, int]] = None
        self.moved: Set[Tuple[int, int]] = set()
        self.rooks, self.k_col = [0, 7], 4
        self.halfmove_clock, self.pos_history = 0, {}
        self.reset(mode)

    def generate_chess960_rank(self) -> List[str]:
        """체스960 규칙에 맞게 무작위 기물 배치를 생성합니다."""
        rank, emp = [None] * 8, lambda r: [i for i in range(8) if r[i] is None]
        rank[random.choice([0, 2, 4, 6])], rank[random.choice([1, 3, 5, 7])] = "B", "B"
        rank[random.choice(emp(rank))] = "Q"
        k1, k2 = random.sample(emp(rank), 2)
        rank[k1], rank[k2] = "N", "N"
        rem = emp(rank)
        rank[rem[0]], rank[rem[1]], rank[rem[2]] = "R", "K", "R"
        return [item for item in rank if item is not None]

    def reset(self, mode: Optional[str] = None) -> None:
        """선택한 모드로 게임 보드를 초기화합니다. mode 미지정 시 동일 배치를 유지합니다."""
        if mode or not self.initial_back:
            self.mode = mode or self.mode
            self.initial_back = self.generate_chess960_rank() if self.mode == "chess960" else ["R", "N", "B", "Q", "K", "B", "N", "R"]
        self.current_turn, self.winner, self.win_reason = "W", None, ""
        self.ep_target, self.moved, self.halfmove_clock, self.pos_history = None, set(), 0, {}
        self.board = [[None for _ in range(8)] for _ in range(8)]
        self.rooks = [i for i, p in enumerate(self.initial_back) if p == "R"]
        self.k_col = self.initial_back.index("K")
        for col in range(8):
            self.board[0][col], self.board[1][col] = ("B", self.initial_back[col]), ("B", "P")
            self.board[6][col], self.board[7][col] = ("W", "P"), ("W", self.initial_back[col])
        self.record_pos()

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < 8 and 0 <= c < 8

    def is_attacked(self, r: int, c: int, enemy: str, board: list) -> bool:
        """특정 위치가 상대 기물로부터 공격받는 중인지 검사합니다."""
        for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]:
            if self.in_bounds(r + dr, c + dc) and board[r + dr][c + dc] == (enemy, "N"): return True
        for dr, dc, pcs in [(-1, -1, "BQ"), (-1, 1, "BQ"), (1, -1, "BQ"), (1, 1, "BQ"),
                            (-1, 0, "RQ"), (1, 0, "RQ"), (0, -1, "RQ"), (0, 1, "RQ")]:
            nr, nc = r + dr, c + dc
            while self.in_bounds(nr, nc):
                if board[nr][nc]:
                    if board[nr][nc][0] == enemy and board[nr][nc][1] in pcs: return True
                    break
                nr, nc = nr + dr, nc + dc
        p_dr = 1 if enemy == "W" else -1
        if any(self.in_bounds(r + p_dr, c + dc) and board[r + p_dr][c + dc] == (enemy, "P") for dc in (-1, 1)):
            return True
        return any(self.in_bounds(r + dr, c + dc) and board[r + dr][c + dc] == (enemy, "K")
                   for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc)

    def is_in_check(self, color: str, board: list) -> bool:
        kp = next(((r, c) for r in range(8) for c in range(8) if board[r][c] == (color, "K")), None)
        return self.is_attacked(kp[0], kp[1], "B" if color == "W" else "W", board) if kp else False

    def get_castle(self, r: int, c: int, er: int, ec: int):
        """캐슬링 시도 여부와 해당 룩/목표 좌표를 반환합니다."""
        for r_col, k_to, r_to in [(self.rooks[1], 6, 5), (self.rooks[0], 2, 3)]:
            if (er, ec) == (r, r_col) or (abs(ec - c) >= 2 and ec == k_to):
                return r_col, k_to, r_to
        return None

    def get_raw_moves(self, r: int, c: int) -> List[Tuple[int, int]]:
        color, piece = self.board[r][c]
        moves, enemy = [], ("B" if color == "W" else "W")
        if piece == "P":
            f, sr = (-1, 6) if color == "W" else (1, 1)
            if self.in_bounds(r + f, c) and not self.board[r + f][c]:
                moves.append((r + f, c))
                if r == sr and not self.board[r + 2 * f][c]: moves.append((r + 2 * f, c))
            for dc in (-1, 1):
                if self.in_bounds(r + f, c + dc) and ((self.board[r + f][c + dc] and self.board[r + f][c + dc][0] == enemy) or (r + f, c + dc) == self.ep_target):
                    moves.append((r + f, c + dc))
        elif piece == "N":
            for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]:
                if self.in_bounds(r + dr, c + dc) and (not self.board[r + dr][c + dc] or self.board[r + dr][c + dc][0] == enemy):
                    moves.append((r + dr, c + dc))
        elif piece in ("B", "R", "Q"):
            dirs = ([(-1, -1), (-1, 1), (1, -1), (1, 1)] if piece in ("B", "Q") else []) + ([(-1, 0), (1, 0), (0, -1), (0, 1)] if piece in ("R", "Q") else [])
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                while self.in_bounds(nr, nc):
                    if not self.board[nr][nc]: moves.append((nr, nc))
                    else:
                        if self.board[nr][nc][0] == enemy: moves.append((nr, nc))
                        break
                    nr, nc = nr + dr, nc + dc
        elif piece == "K":
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if (dr or dc) and self.in_bounds(r + dr, c + dc) and (not self.board[r + dr][c + dc] or self.board[r + dr][c + dc][0] == enemy):
                        moves.append((r + dr, c + dc))
            if (r, self.k_col) not in self.moved and c == self.k_col and not self.is_in_check(color, self.board):
                for r_col, k_to, r_to in [(self.rooks[1], 6, 5), (self.rooks[0], 2, 3)]:
                    if (r, r_col) not in self.moved and self.board[r][r_col] == (color, "R"):
                        k_path = [sc for sc in range(min(c, k_to), max(c, k_to) + 1) if sc != c]
                        sqs = (set(range(min(c, k_to), max(c, k_to) + 1)) | set(range(min(r_col, r_to), max(r_col, r_to) + 1))) - {c, r_col}
                        if not any(self.is_attacked(r, sc, enemy, self.board) for sc in k_path) and not any(self.board[r][sc] for sc in sqs):
                            moves.append((r, r_col))
                            if abs(k_to - c) >= 2 and k_to != r_col: moves.append((r, k_to))
        return moves

    def get_valid_moves(self, r: int, c: int) -> List[Tuple[int, int]]:
        if not self.in_bounds(r, c) or not self.board[r][c] or self.board[r][c][0] != self.current_turn: return []
        color, piece, legal = self.board[r][c][0], self.board[r][c][1], []
        for er, ec in self.get_raw_moves(r, c):
            castle = self.get_castle(r, c, er, ec) if piece == "K" else None
            temp = [row[:] for row in self.board]
            if castle:
                r_col, k_to, r_to = castle
                temp[r][c], temp[r][r_col] = None, None
                temp[r][k_to], temp[r][r_to] = (color, "K"), (color, "R")
            else:
                if piece == "P" and (er, ec) == self.ep_target: temp[r][ec] = None
                temp[er][ec], temp[r][c] = temp[r][c], None
            if not self.is_in_check(color, temp): legal.append((er, ec))
        return legal

    def has_any_moves(self, color: str) -> bool:
        saved, self.current_turn = self.current_turn, color
        can_move = any(self.get_valid_moves(r, c) for r in range(8) for c in range(8) if self.board[r][c] and self.board[r][c][0] == color)
        self.current_turn = saved
        return can_move

    def record_pos(self) -> None:
        pos = (self.current_turn, self.ep_target, tuple(tuple(row) for row in self.board))
        self.pos_history[pos] = self.pos_history.get(pos, 0) + 1

    def check_insufficient_material(self) -> bool:
        pcs = [(r, c, p[1]) for r in range(8) for c in range(8) if self.board[r][c] for p in [self.board[r][c]]]
        if any(p[2] in ("P", "R", "Q") for p in pcs) or len(pcs) > 4: return False
        if len(pcs) <= 2 or (len(pcs) == 3 and any(p[2] in ("B", "N") for p in pcs)): return True
        bs = [p for p in pcs if p[2] == "B"]
        return len(pcs) == 4 and len(bs) == 2 and (bs[0][0] + bs[0][1]) % 2 == (bs[1][0] + bs[1][1]) % 2

    def make_move(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        if self.winner or end not in self.get_valid_moves(start[0], start[1]): return False
        sr, sc, (er, ec) = start[0], start[1], end
        color, piece = self.board[sr][sc]
        castle = self.get_castle(sr, sc, er, ec) if piece == "K" else None
        captured = (self.board[er][ec] is not None) and (not castle)

        if castle:
            r_col, k_to, r_to = castle
            self.board[sr][sc], self.board[sr][r_col] = None, None
            self.board[sr][k_to], self.board[sr][r_to] = (color, "K"), (color, "R")
            self.moved.update([(sr, sc), (sr, r_col)])
            self.ep_target = None
        else:
            if piece == "P" and (er, ec) == self.ep_target:
                self.board[sr][ec], captured = None, True
            promoted = "Q" if piece == "P" and (er in (0, 7)) else piece
            self.board[er][ec], self.board[sr][sc] = (color, promoted), None
            self.ep_target = ((sr + er) // 2, sc) if piece == "P" and abs(er - sr) == 2 else None
            self.moved.update([(sr, sc), (er, ec)])

        self.halfmove_clock = 0 if (piece == "P" or captured) else self.halfmove_clock + 1
        cname = "백색(White)" if color == "W" else "흑색(Black)"

        if self.mode == "koth" and piece == "K" and not castle and (er, ec) in CENTER_SQUARES:
            self.winner, self.win_reason = color, f"{cname} 킹이 중앙 언덕(d4/d5/e4/e5)을 점령했습니다!"
            return True

        self.current_turn = "B" if self.current_turn == "W" else "W"
        self.record_pos()

        if not self.has_any_moves(self.current_turn):
            self.winner = color if self.is_in_check(self.current_turn, self.board) else "Draw"
            self.win_reason = f"체크메이트! {cname} 승리." if self.winner == color else "스테일메이트로 무승부입니다."
        elif self.check_insufficient_material():
            self.winner, self.win_reason = "Draw", "기물 부족(Insufficient material)으로 무승부입니다."
        elif self.pos_history.get((self.current_turn, self.ep_target, tuple(tuple(row) for row in self.board)), 0) >= 3:
            self.winner, self.win_reason = "Draw", "3회 동형 반복(Threefold repetition)으로 무승부입니다."
        elif self.halfmove_clock >= 100:
            self.winner, self.win_reason = "Draw", "50수 규칙(50-move rule)으로 무승부입니다."
        return True
