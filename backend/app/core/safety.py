import re

FORBIDDEN = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|GRANT|REVOKE|CREATE)\b",
    re.IGNORECASE,
)


def is_read_only(sql: str) -> bool:
    stripped = sql.strip().rstrip(";")
    if not stripped.upper().startswith("SELECT"):
        return False
    if FORBIDDEN.search(stripped):
        return False
    return True
