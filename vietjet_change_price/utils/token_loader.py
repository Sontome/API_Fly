"""
utils/token_loader.py
Utility to extract app_access_token from Playwright/browser state.json.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_app_access_token_from_state(file_path: str | Path = "state.json") -> str | None:
    """
    Parse state.json (Playwright browser storage state) and extract
    the `app_access_token` value from localStorage.

    Args:
        file_path: Path to state.json file.

    Returns:
        Bearer token string if found, else None.
    """
    path = Path(file_path)

    if not path.exists():
        
        
        logger.error(f"state.json not found at: {path.resolve()}")
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to read state.json: {e}")
        return None

    origins: list[dict] = data.get("origins", [])

    for origin in origins:
        local_storage: list[dict] = origin.get("localStorage", [])
        for item in local_storage:
            if item.get("name") == "app_access_token":
                token = item.get("value")
                if token:
                    logger.debug("app_access_token loaded from state.json")
                    return token

    logger.warning("app_access_token not found in any origin's localStorage")
    return None
