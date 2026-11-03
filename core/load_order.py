import heapq


def resolve_load_order(mods):
    errors = []
    enabled = {key: value for key, value in mods.items()
               if isinstance(key, str) and isinstance(value, dict) and value.get("enabled", True) is True}
    degree = {key: 0 for key in enabled}
    children = {key: [] for key in enabled}
    for mod_id, mod in enabled.items():
        deps = mod.get("dependencies", [])
        conflicts = mod.get("conflicts", [])
        deps = set(deps.keys()) if isinstance(deps, dict) else set(deps) if isinstance(deps, list) else set()
        conflicts = set(conflicts.keys()) if isinstance(conflicts, dict) else set(conflicts) if isinstance(conflicts, list) else set()
        for dep in deps:
            if not isinstance(dep, str) or not dep:
                continue
            if dep not in mods:
                errors.append(f"{mod_id}: отсутствует обязательная зависимость {dep}.")
            elif dep not in enabled:
                errors.append(f"{mod_id}: зависимость {dep} отключена.")
            else:
                degree[mod_id] += 1
                children[dep].append(mod_id)
        for conflict in conflicts:
            if conflict in enabled and conflict != mod_id:
                errors.append(f"{mod_id}: конфликтует с включённым модом {conflict}.")
    ready = [key for key, value in degree.items() if value == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        current = heapq.heappop(ready)
        order.append(current)
        for child in children[current]:
            degree[child] -= 1
            if degree[child] == 0:
                heapq.heappush(ready, child)
    if len(order) != len(enabled):
        cyclic = sorted(key for key, value in degree.items() if value > 0)
        errors.append("Обнаружен цикл зависимостей: " + ", ".join(cyclic[:20]))
    if errors:
        return [], list(dict.fromkeys(errors)), []
    return order, [], []
