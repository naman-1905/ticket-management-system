import asyncio
async def notification_consumer(stop_event: asyncio.Event):
    await stop_event.wait()
