#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility entry point for local development."""

import os
import threading
import webbrowser

from toolmist import create_app


app = create_app()


def main():
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5001"))
    open_local_browser = os.getenv("OPEN_BROWSER", "1") == "1" and host in {
        "127.0.0.1",
        "localhost",
    }

    if open_local_browser:
        threading.Timer(1.5, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
