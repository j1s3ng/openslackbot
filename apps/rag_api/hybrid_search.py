def merge_candidates(*candidate_lists: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for candidates in candidate_lists:
        for candidate in candidates:
            chunk_id = candidate.get("chunk_id")
            if not chunk_id:
                continue
            existing = merged.get(chunk_id)
            if existing is None or candidate.get("score", 0) > existing.get("score", 0):
                merged[chunk_id] = candidate
    return list(merged.values())
