"""Launcher: `python -m app.serve` (this computer only) or `--phone` (home Wi-Fi)."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import threading
import webbrowser
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def lan_ip() -> str:
    """This computer's address on the local network (no packets are sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def phone_secrets() -> dict:
    """Access code + session token, kept across restarts in data/phone.json."""
    DATA.mkdir(exist_ok=True)
    f = DATA / "phone.json"
    try:
        cfg = json.loads(f.read_text(encoding="utf-8"))
        if len(cfg["pin"]) == 6 and len(cfg["token"]) >= 20:
            return cfg
    except (OSError, ValueError, KeyError, TypeError):
        pass
    cfg = {"pin": f"{secrets.randbelow(10**6):06d}", "token": secrets.token_urlsafe(24)}
    f.write_text(json.dumps(cfg), encoding="utf-8")
    return cfg


def main() -> None:
    ap = argparse.ArgumentParser(description="Shorts Studio")
    ap.add_argument("--phone", action="store_true",
                    help="allow phones on the same Wi-Fi (protected by an access code)")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    local = f"http://localhost:{args.port}"
    host = "127.0.0.1"
    print(f"\nShorts Studio  ->  {local}   (Ctrl+C to stop)")

    if args.phone:
        cfg = phone_secrets()
        url = f"http://{lan_ip()}:{args.port}"
        os.environ.update(SHORTS_PIN=cfg["pin"], SHORTS_TOKEN=cfg["token"],
                          SHORTS_LAN_URL=url)
        host = "0.0.0.0"
        print("\n=== Phone mode ===")
        print(f"On your phone (same Wi-Fi) open:  {url}")
        print(f"Access code:                      {cfg['pin']}")
        try:
            import segno

            segno.make(url, error="m").terminal(compact=True, border=2)
        except Exception:
            pass
        print("The QR code and the access code are also shown on the home screen "
              "of this computer.\n")

    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(local)).start()

    import uvicorn

    uvicorn.run("app.main:app", host=host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
