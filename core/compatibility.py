"""Declared game-version compatibility checks; no runtime assumptions."""
import json
import re
from pathlib import Path

_VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?$")


def parse_version(value):
    if not isinstance(value, str):
        return None
    match = _VERSION.fullmatch(value.strip())
    return tuple(int(part) for part in match.groups()) if match else None


def check_compatibility(project: Path, game_version: str):
    """Check only explicit version constraints declared by the mod author."""
    root = Path(project).resolve()
    errors, warnings, info = [], [], []
    current = parse_version(game_version)
    if current is None:
        return ["Укажи версию игры в формате 1.2.3."], warnings, info
    try:
        manifest = json.loads((root / "mod.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"Не удалось прочитать mod.json: {exc}"], warnings, info
    if not isinstance(manifest, dict):
        return ["mod.json должен содержать JSON-объект."], warnings, info

    declared_exact = manifest.get("gameVersion")
    minimum = manifest.get("minGameVersion")
    maximum = manifest.get("maxGameVersion")
    if not any((declared_exact, minimum, maximum)):
        warnings.append("Мод не объявляет gameVersion/minGameVersion/maxGameVersion: совместимость не определена.")
    if declared_exact:
        parsed = parse_version(declared_exact)
        if parsed is None:
            errors.append("gameVersion имеет неверный формат; ожидается 1.2.3.")
        elif parsed != current:
            errors.append(f"Мод объявлен для SkyRealm {declared_exact}, проверяется {game_version}.")
        else:
            info.append(f"Точная версия игры совпадает: {game_version}.")
    if minimum:
        parsed = parse_version(minimum)
        if parsed is None:
            errors.append("minGameVersion имеет неверный формат.")
        elif current < parsed:
            errors.append(f"Требуется SkyRealm не ниже {minimum}.")
    if maximum:
        parsed = parse_version(maximum)
        if parsed is None:
            errors.append("maxGameVersion имеет неверный формат.")
        elif current > parsed:
            errors.append(f"Мод заявлен максимум для SkyRealm {maximum}.")
    if minimum and maximum:
        low, high = parse_version(minimum), parse_version(maximum)
        if low and high and low > high:
            errors.append("minGameVersion не может быть выше maxGameVersion.")

    api = manifest.get("apiVersion")
    if api is not None:
        if not isinstance(api, str) or not api.strip():
            errors.append("apiVersion должна быть непустой строкой.")
        else:
            info.append(f"Мод заявляет API {api}; наличие такого API в игре отдельно не проверено.")
    features = manifest.get("requiredFeatures", [])
    if not isinstance(features, list) or any(not isinstance(item, str) or not item.strip() for item in features):
        errors.append("requiredFeatures должен быть массивом непустых строк.")
    elif features:
        warnings.append("Требуемые функции: " + ", ".join(features) + ". Studio не может подтвердить их наличие в runtime.")

    return errors, warnings, info
