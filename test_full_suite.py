# -*- coding: utf-8 -*-
"""체스 규칙, FEN 변환, API 클라이언트, GUI 통합 종합 테스트 슈트."""

import time
import tkinter as tk
from unittest.mock import MagicMock, patch

from api_client import LichessAPIClient
from chess_gui import ChessGUI
from chess_rules import CENTER_SQUARES, ChessGame


def test_chess_rules_and_fen():
    print("[1/4] 체스 규칙 및 FEN 변환 테스트 시작...")
    game = ChessGame("standard")

    # 1. 초기 상태 FEN
    assert game.to_fen() == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    # 2. 1. e4 (폰 2칸 전진, 앙파상 타깃 e3)
    assert game.make_move((6, 4), (4, 4))
    assert game.to_fen() == "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    assert game.current_turn == "B"
    assert game.halfmove_clock == 0
    assert game.fullmove_number == 1

    # 3. 1... e5 (흑 착수 완료 -> fullmove 2로 증가)
    assert game.make_move((1, 4), (3, 4))
    assert game.to_fen() == "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2"
    assert game.current_turn == "W"
    assert game.fullmove_number == 2

    # 4. 2. Nf3 (나이트 전진, 앙파상 초기화, 하프무브 1)
    assert game.make_move((7, 6), (5, 5))
    assert game.to_fen() == "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2"
    assert game.halfmove_clock == 1

    # 5. 2... Nc6
    assert game.make_move((0, 1), (2, 2))
    # 6. 3. Bc4 Bc5
    assert game.make_move((7, 5), (4, 2))
    assert game.make_move((0, 5), (3, 2))

    # 7. 4. O-O (백색 킹사이드 캐슬링)
    assert (7, 6) in game.get_valid_moves(7, 4)
    assert game.make_move((7, 4), (7, 6))
    fen_after_castling = game.to_fen()
    assert fen_after_castling.split()[2] == "kq"
    assert game.board[7][6] == ("W", "K")
    assert game.board[7][5] == ("W", "R")

    # 8. 앙파상 잡기 테스트
    ep_game = ChessGame("standard")
    ep_game.make_move((6, 4), (4, 4)) # 1. e4
    ep_game.make_move((0, 6), (2, 5)) # 1... Nf6
    ep_game.make_move((4, 4), (3, 4)) # 2. e5
    ep_game.make_move((1, 3), (3, 3)) # 2... d5 (앙파상 타깃 d6)
    assert ep_game.to_fen().split()[3] == "d6"
    assert (2, 3) in ep_game.get_valid_moves(3, 4)
    assert ep_game.make_move((3, 4), (2, 3)) # exd6 앙파상
    assert ep_game.board[3][3] is None # d5 폰 포획 확인

    # 9. King of the hill (KOTH) 테스트
    koth_game = ChessGame("koth")
    # 킹을 중앙 4칸 중 하나로 직접 배치하여 승리 검증
    koth_game.board = [[None]*8 for _ in range(8)]
    koth_game.board[4][4] = None
    koth_game.board[5][4] = ("W", "K")
    koth_game.board[0][0] = ("B", "K")
    koth_game.current_turn = "W"
    koth_game.k_col = 4
    assert koth_game.make_move((5, 4), (4, 4))
    assert koth_game.winner == "W"
    assert "중앙 언덕" in koth_game.win_reason

    # 10. 체크메이트 (Fool's Mate) 테스트
    fools = ChessGame("standard")
    fools.make_move((6, 5), (5, 5)) # 1. f3
    fools.make_move((1, 4), (3, 4)) # 1... e5
    fools.make_move((6, 6), (4, 6)) # 2. g4
    fools.make_move((0, 3), (4, 7)) # 2... Qh4#
    assert fools.winner == "B"
    assert "체크메이트" in fools.win_reason

    print(" -> 체스 규칙 및 FEN 변환 테스트 통과!")


def test_api_client():
    print("[2/4] API 클라이언트 테스트 시작...")
    client = LichessAPIClient()

    # 1. 라이브 비인증 요청 (401 감지 확인)
    res_live = client.fetch_masters_opening("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    assert res_live["success"] is False
    assert res_live["error_type"] == "auth_required"

    # 2. Mock 200 응답 파싱
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.ok = True
    mock_resp.json.return_value = {
        "white": 100, "draws": 50, "black": 30,
        "opening": {"eco": "C50", "name": "Italian Game"},
        "moves": [{"san": "e4", "uci": "e2e4", "white": 80, "draws": 40, "black": 20, "averageRating": 2550}]
    }
    with patch("requests.get", return_value=mock_resp):
        res200 = client.fetch_masters_opening("fen_test_success")
        assert res200["success"] is True
        assert res200["opening"]["name"] == "Italian Game"
        assert res200["stats"]["total"] == 180
        assert len(res200["moves"]) == 1

        # 3. 동일 FEN 중복 요청 방지 (캐시 확인)
        res_cached = client.fetch_masters_opening("fen_test_success")
        assert res_cached["cached"] is True

    # 4. HTTP 429 쿨다운 (최소 60초 대기)
    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.headers = {"Retry-After": "10"}
    with patch("requests.get", return_value=mock_429):
        res_429 = client.fetch_masters_opening("fen_trigger_429")
        assert res_429["success"] is False
        assert res_429["error_type"] == "rate_limited"
        assert client.get_remaining_cooldown() >= 58

        # 쿨다운 중 호출 시 네트워크 요청 없이 차단
        blocked = client.fetch_masters_opening("fen_new_pos")
        assert blocked["success"] is False
        assert blocked["error_type"] == "rate_limited"

    print(" -> API 클라이언트 테스트 통과!")


def test_gui_integration():
    print("[3/4] GUI 연동 및 비동기 처리 테스트 시작...")
    root = tk.Tk()
    root.withdraw() # 실제 창 띄우지 않고 헤드리스 모드
    gui = ChessGUI(root)

    # 1. 메뉴에서 Standard 게임 시작
    gui.start_game("standard")
    assert gui.game.mode == "standard"
    root.update()

    # 2. 비동기 API 요청 확인 (Mock 적용)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.ok = True
    mock_resp.json.return_value = {
        "white": 1200, "draws": 800, "black": 400,
        "opening": {"eco": "B00", "name": "King's Pawn Opening"},
        "moves": [{"san": "e4", "uci": "e2e4", "white": 800, "draws": 500, "black": 200, "averageRating": 2500}]
    }

    with patch("requests.get", return_value=mock_resp):
        # 1. e4 클릭 시뮬레이션
        # 백 폰 (6, 4) 선택
        event1 = MagicMock()
        event1.x, event1.y = 4 * 64 + 32, 6 * 64 + 32
        gui.on_board_click(event1)
        assert gui.selected == (6, 4)

        # e4 (4, 4)로 이동
        event2 = MagicMock()
        event2.x, event2.y = 4 * 64 + 32, 4 * 64 + 32
        gui.on_board_click(event2)
        assert gui.selected is None
        assert gui.game.board[4][4] == ("W", "P")

        # 비동기 스레드 완료 대기 및 Tkinter 이벤트 펌프
        for _ in range(10):
            root.update()
            time.sleep(0.05)

        # 우측 패널 라벨 업데이트 확인
        assert gui.opening_name_label.cget("text") == "King's Pawn Opening"
        assert "2,400" in gui.stats_total_label.cget("text")
        assert len(gui.moves_container.winfo_children()) == 1

    # 3. 비 Standard 모드 (체스960) 전환 시 패널 안내 확인
    gui.start_game("chess960")
    root.update()
    assert "미지원" in gui.opening_name_label.cget("text")
    assert "Standard 체스 모드에서만" in gui.status_msg_label.cget("text")

    # 4. 게임 재시작 확인
    gui.restart_current_game()
    root.update()
    assert gui.game.current_turn == "W"

    root.destroy()
    print(" -> GUI 연동 및 비동기 처리 테스트 통과!")


if __name__ == "__main__":
    test_chess_rules_and_fen()
    test_api_client()
    test_gui_integration()
    print("[4/4] 모든 단위 및 통합 테스트 성공 완료!")
