"""
shared/storage.py
Tiện ích đọc/ghi JSON state file.
"""

import json
import os
from pathlib import Path
from typing import Any

from shared.exceptions import StateFileError
from shared.logger import LogPrefix, get_logger

logger = get_logger(LogPrefix.STATE)


def read_json(path: str | Path) -> dict[str, Any]:
    """
    Đọc file JSON.

    Args:
        path: Đường dẫn tới file JSON.

    Returns:
        Dict chứa nội dung file.

    Raises:
        StateFileError: Nếu file không tồn tại hoặc JSON không hợp lệ.
    """
    p = Path(path)
    if not p.exists():
        logger.warning(f"State file không tồn tại: {p}")
        return {}
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        logger.debug(f"Đọc state file thành công: {p}")
        return data
    except json.JSONDecodeError as e:
        raise StateFileError(f"JSON không hợp lệ tại {p}: {e}") from e
    except OSError as e:
        raise StateFileError(f"Không thể đọc file {p}: {e}") from e


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    """
    Ghi dict ra file JSON.

    Args:
        path: Đường dẫn ghi file.
        data: Dữ liệu cần lưu.

    Raises:
        StateFileError: Nếu không ghi được file.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug(f"Ghi state file thành công: {p}")
    except OSError as e:
        raise StateFileError(f"Không thể ghi file {p}: {e}") from e


def merge_json(path: str | Path, updates: dict[str, Any]) -> dict[str, Any]:
    """
    Đọc file JSON hiện có, merge với updates rồi ghi lại.

    Args:
        path: Đường dẫn file JSON.
        updates: Dict cần merge vào.

    Returns:
        Dict sau khi merge.
    """
    existing = read_json(path)
    existing.update(updates)
    write_json(path, existing)
    return existing


def get_env(key: str, default: str | None = None) -> str:
    """
    Lấy biến môi trường.

    Args:
        key: Tên biến môi trường.
        default: Giá trị mặc định nếu không tìm thấy.

    Returns:
        Giá trị biến môi trường.

    Raises:
        ConfigurationError: Nếu biến không tồn tại và không có default.
    """
    from shared.exceptions import ConfigurationError

    value = os.environ.get(key, default)
    if value is None:
        raise ConfigurationError(f"Biến môi trường '{key}' chưa được thiết lập.")
    return value
