# -*- coding: utf-8 -*-
"""오프라인 변형 체스 게임 실행 파일 (Main Entry Point)."""

import tkinter as tk
from chess_gui import ChessGUI


def main() -> None:
    """Tkinter 윈도우 생성 및 오프라인 변형 체스 게임 실행."""
    root = tk.Tk()
    root.title("오프라인 변형 체스 (Offline Variant Chess)")
    root.resizable(False, False)

    # 화면 중앙에 윈도우 배치
    window_width = 560
    window_height = 640
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    pos_x = (screen_width - window_width) // 2
    pos_y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")

    ChessGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
