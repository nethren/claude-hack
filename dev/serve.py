"""Start the demo backend (API + fuel/CO2 panel) for the frontend.

    .venv/Scripts/python -m dev.serve            # offline test agents, no key needed
    .venv/Scripts/python -m dev.serve --live     # live Claude agents

Live mode reads ANTHROPIC_API_KEY from the environment or the repo's git-ignored
.env (never printed), and defaults ANTHROPIC_MODEL to claude-opus-5-5. The
frontend's Vite dev server proxies /api to this server on port 8000.
"""
from __future__ import annotations

import argparse
import os

import uvicorn

from dev.run_atc_live import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--live", action="store_true", help="invoke live Claude agents")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.live:
        load_dotenv()
        os.environ["COORDINATOR_MODE"] = "live"
        os.environ.setdefault("ANTHROPIC_MODEL", "claude-opus-5-5")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            parser.error("live mode needs ANTHROPIC_API_KEY in the environment or .env")
    else:
        os.environ["COORDINATOR_MODE"] = "offline"
    print(f"Backend mode: {os.environ['COORDINATOR_MODE']} on http://127.0.0.1:{args.port}")
    uvicorn.run("api_fuel:app", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
