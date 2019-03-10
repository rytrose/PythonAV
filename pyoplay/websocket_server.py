import asyncio
import websockets
import json


class WSServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
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
            print(f"Sending {message}")
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

    async def handler(self, websocket, path):
        print(f"Starting to listen at {path}")
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
        server_coro = websockets.serve(self.handler, host=self.host, port=self.port)
        asyncio.get_event_loop().run_until_complete(server_coro)

        if not asyncio.get_event_loop().is_running():
            asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    server = WSServer(None, 8000)
    server.start()
