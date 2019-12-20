def indent(string, places=4, linebreak="\n", singles=False):
    lines = string.split(linebreak)
    if not singles and len(lines) == 1:
        return string
    for i, line in enumerate(lines):
        lines[i] = " " * places + line
    result = linebreak.join(lines)
    if not singles:
        result = linebreak + result
    return result
