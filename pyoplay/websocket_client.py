import asyncio
import websockets
import json


class WSClient:
    def __init__(self, uri):
        self.uri = uri
        self._callback_map = {}
        self._default_coro = self.print_message
        self._send_queue = asyncio.Queue()

    async def print_message(self, message):
        print(message)

    async def producer(self):
        message_dict = await self._send_queue.get()
        message = json.dumps(message_dict)
        return message

    async def producer_handler(self, websocket):
        while True:
            message = await self.producer()
            await websocket.send(message)

    async def consumer_handler(self, websocket):
        while True:
            async for message in websocket:
                message_dict = json.loads(message)
                address = message_dict['address']
                if address in self._callback_map.keys():
                    asyncio.ensure_future(self._callback_map[address](message_dict))
                else:
                    asyncio.ensure_future(self._default_coro(message_dict))

    async def handler(self):
        async with websockets.connect(self.uri) as websocket:
            producer_task = asyncio.ensure_future(self.producer_handler(websocket))
            consumer_task = asyncio.ensure_future(self.consumer_handler(websocket))
            done, pending = await asyncio.wait(
                [consumer_task, producer_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

    def map(self, address, coro):
        self._callback_map[address] = coro

    def map_default(self, coro):
        self._default_coro = coro

    def send(self, message):
        self._send_queue.put(message)

    def start(self):
        asyncio.ensure_future(self.handler())
