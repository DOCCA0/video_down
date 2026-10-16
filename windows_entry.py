"""PyInstaller entry point for the Windows desktop application."""

import sys


def run() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--you-get-worker":
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        from you_get.__main__ import main as you_get_main

        you_get_main()
        return

    from video_down.gui import main

    main()

if __name__ == "__main__":
    run()
