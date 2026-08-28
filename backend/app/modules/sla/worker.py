import asyncio
async def sla_worker(stop_event: asyncio.Event, interval: int = 60):
    while not stop_event.is_set():
        try: await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError: pass
