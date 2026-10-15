"""Launcher used by START_AMR_DIGITAL_TWIN.bat and by the packaged .exe.

Finds a free port, starts the Streamlit server in-process, waits until it is ready and
then opens the default browser. Close the window (or press Ctrl+C) to stop the app.
"""
import os
import socket
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from pathlib import Path

BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def free_port(start: int = 8501, tries: int = 50) -> int:
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free network port found between 8501 and 8550.")


def open_when_ready(port: int, timeout: int = 120) -> None:
    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/_stcore/health", timeout=2) as r:
                if r.status == 200:
                    print(f"\nReady. Opening {url} in your browser ...")
                    webbrowser.open(url)
                    return
        except Exception:
            time.sleep(0.5)
    print(f"\nThe app did not respond within {timeout} s. Try opening {url} manually.")


def main() -> int:
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    port = free_port()
    print("=" * 62)
    print(" AMR-Ward Digital Twin  (simulated data - educational use only)")
    print("=" * 62)
    print(f" Starting on port {port} ... your browser will open automatically.")
    print(" KEEP THIS WINDOW OPEN while you use the app.")
    print(" To quit: close this window (or press Ctrl+C).\n")
    threading.Thread(target=open_when_ready, args=(port,), daemon=True).start()
    try:
        from streamlit.web import bootstrap
        flags = {"server.port": port, "server.address": "127.0.0.1", "server.headless": True,
                 "browser.gatherUsageStats": False, "global.developmentMode": False,
                 "server.fileWatcherType": "none", "server.runOnSave": False}
        bootstrap.load_config_options(flags)
        bootstrap.run(str(BASE / "app.py"), False, [], flags)
    except KeyboardInterrupt:
        print("Stopped.")
    except Exception:
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
