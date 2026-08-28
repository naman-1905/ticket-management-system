import asyncio, hashlib, json, time
from app.core.errors import ConflictError
_cache: dict[str, tuple[str, dict, float]] = {}; _lock = asyncio.Lock(); TTL = 72 * 60 * 60
async def replay_or_none(key: str | None, body: object):
    if not key: return None
    fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    async with _lock:
        item = _cache.get(key)
        if item and item[2] <= time.time(): _cache.pop(key, None); item = None
    if item and item[0] != fingerprint: raise ConflictError("Idempotency key was used with a different request", "IDEMPOTENCY_MISMATCH")
    return item[1] if item else None
async def store(key: str | None, body: object, response: dict):
    if key:
        fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
        async with _lock: _cache[key] = (fingerprint, response, time.time() + TTL)
