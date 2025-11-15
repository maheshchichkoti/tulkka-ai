import os

import uvicorn
from src.api.app import app


def get_app_port() -> int:
    """Return server port, defaulting to 8000."""
    try:
        return int(os.getenv("APP_PORT", "8000"))
    except ValueError:
        return 8000


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=get_app_port())
