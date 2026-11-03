"""Heuristic JavaScript checks that ignore strings and ordinary comments."""
import re


def _mask_js(source):
    """Replace strings/comments with spaces while preserving line numbers."""
    code = list(source)
    comments = []
    i, n = 0, len(source)
    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        if ch in ("'", '"', "`"):
            quote = ch
            start = i
            i += 1
            while i < n:
                if source[i] == "\\":
                    i += 2
                    continue
                if source[i] == quote:
                    i += 1
                    break
                i += 1
            for j in range(start, min(i, n)):
                if code[j] != "\n":
                    code[j] = " "
            continue
        if ch == "/" and nxt == "/":
            start = i
            end = source.find("\n", i)
            i = n if end < 0 else end
            comments.append((start, source[start:i]))
            for j in range(start, i):
                code[j] = " "
            continue
        if ch == "/" and nxt == "*":
            start = i
            end = source.find("*/", i + 2)
            i = n if end < 0 else end + 2
            comments.append((start, source[start:i]))
            for j in range(start, i):
                if code[j] != "\n":
                    code[j] = " "
            continue
        i += 1
    return "".join(code), comments


def scan_javascript(source):
    """Return (line, message, level) findings without executing JavaScript."""
    masked, comments = _mask_js(source)
    findings = []
    checks = (
        (r"\beval\s*\(", "Опасный eval(): избегай выполнения строк как кода", "WARN"),
        (r"\bnew\s+Function\s*\(", "Динамическое создание функций затрудняет проверку", "WARN"),
        (r"\bwhile\s*\(\s*true\s*\)", "Возможен бесконечный цикл", "WARN"),
        (r"\bsetInterval\s*\(", "Проверь, что таймер очищается и не создаёт утечки", "WARN"),
        (r"\bconsole\.log\s*\(", "Отладочный console.log может засорять вывод", "WARN"),
    )
    for pattern, message, level in checks:
        for match in re.finditer(pattern, masked):
            findings.append((masked.count("\n", 0, match.start()) + 1, message, level))
    for offset, comment in comments:
        for match in re.finditer(r"\bTODO\b|\bFIXME\b", comment):
            line = source.count("\n", 0, offset + match.start()) + 1
            findings.append((line, "Осталась незавершённая задача", "WARN"))
    if re.search(r"\b(?:spawnMob|createItem|registerWeapon|addQuest)\s*\(", masked):
        findings.append((1, "Обнаружены игровые вызовы; сверь их с API runtime своей версии SkyRealm", "INFO"))
    return sorted(findings, key=lambda item: item[0])
