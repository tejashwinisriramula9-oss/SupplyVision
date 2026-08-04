"""
SupplyVision – API Server Launcher
Starts the FastAPI development/production server.

Usage:
    python run_api.py                  # dev mode, auto-reload
    python run_api.py --prod           # production mode (no reload)
    python run_api.py --port 9000      # custom port
"""

import argparse
import os

import uvicorn
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="SupplyVision FastAPI Server")
    parser.add_argument("--host", default=os.getenv("API_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("API_PORT", 8000)))
    parser.add_argument("--prod", action="store_true", help="Production mode (disables reload)")
    args = parser.parse_args()

    reload = not args.prod

    print(f"""
╔══════════════════════════════════════════════╗
║          SupplyVision API Server             ║
║   http://{args.host}:{args.port}             ║
║   Docs: http://{args.host}:{args.port}/docs  ║
╚══════════════════════════════════════════════╝
""")

    uvicorn.run(
        "src.api.main:app",
        host=args.host,
        port=args.port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
