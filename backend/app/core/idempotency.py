import hashlib, json
from app.core.errors import ConflictError
_cache: dict[str, tuple[str, dict]] = {}
async def replay_or_none(key: str | None, body: object):
    if not key: return None
    fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    item = _cache.get(key)
    if item and item[0] != fingerprint: raise ConflictError("Idempotency key was used with a different request", "IDEMPOTENCY_MISMATCH")
    return item[1] if item else None
async def store(key: str | None, body: object, response: dict):
    if key:
        fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest(); _cache[key] = (fingerprint, response)
