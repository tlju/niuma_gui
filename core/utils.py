from datetime import datetime
from typing import Optional


def get_local_now() -> datetime:
    return datetime.now()


def format_datetime(dt: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if dt is None:
        return ""
    return dt.strftime(fmt)


def format_time(dt: Optional[datetime], fmt: str = "%H:%M:%S") -> str:
    if dt is None:
        return ""
    return dt.strftime(fmt)
