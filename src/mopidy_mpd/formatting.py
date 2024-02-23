def indent(
    value: str,
    *,
    places: int = 4,
    linebreak: str = "\n",
    singles: bool = False,
) -> str:
    lines = value.split(linebreak)
    if not singles and len(lines) == 1:
        return value
    for i, line in enumerate(lines):
        lines[i] = " " * places + line
    result = linebreak.join(lines)
    if not singles:
        result = linebreak + result
    return result
