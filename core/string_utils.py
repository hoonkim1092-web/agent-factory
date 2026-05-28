def truncate(s: str, max_len: int, suffix: str = "...") -> str:
    """s를 max_len 이하로 자르고 suffix를 붙인다.

    max_len이 len(suffix) 미만이면 ValueError를 발생시킨다.
    """
    if max_len < len(suffix):
        raise ValueError(
            f"max_len({max_len}) must be >= len(suffix)({len(suffix)})"
        )
    if len(s) <= max_len:
        return s
    return s[: max_len - len(suffix)] + suffix
