import asyncio
from dataclasses import dataclass, field
@dataclass
class InMemoryEventBus:
    events: list[dict] = field(default_factory=list); queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    async def publish(self, event_type: str, payload: dict):
        event={"type":event_type,"payload":payload}; self.events.append(event); await self.queue.put(event)
    async def consume(self): return await self.queue.get()
event_bus = InMemoryEventBus()
