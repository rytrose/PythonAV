import asyncio
import websockets
import json
import threading
import argparse


class WS:
    def __init__(self, is_client=False, uri=None, host=None, port=8000):
        self.uri = uri
        self.host = host
        self.port = port

        self.is_client = is_client

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        self._callback_map = {}
        self._default_coro = self.print_message
        self._send_queue = asyncio.Queue()

    async def print_message(self, address, args):
        print(f"Received message to address '{address}' with args {args}")

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
                args = message_dict['args']
                if address in self._callback_map.keys():
                    asyncio.ensure_future(self._callback_map[address](address, args))
                else:
                    asyncio.ensure_future(self._default_coro(address, args))

    async def client_handler(self):
        async with websockets.connect(self.uri) as websocket:
            producer_task = asyncio.ensure_future(self.producer_handler(websocket))
            consumer_task = asyncio.ensure_future(self.consumer_handler(websocket))
            done, pending = await asyncio.wait(
                [consumer_task, producer_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

    async def server_handler(self, websocket, _):
        print("New connection made.")
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

    def send(self, address, args):
        asyncio.run_coroutine_threadsafe(self._send_queue.put({
            "address": address,
            "args": args
        }), self._loop)

    def start_client(self, loop):
        asyncio.set_event_loop(self._loop)
        loop.run_until_complete(self.client_handler())
        loop.run_forever()

    def start_server(self, loop):
        asyncio.set_event_loop(loop)
        server_coro = websockets.serve(self.server_handler, host=self.host, port=self.port)
        loop.run_until_complete(server_coro)
        loop.run_forever()

    def start(self):
        if self.is_client:
            t = threading.Thread(target=self.start_client, args=(self._loop,))
        else:
            t = threading.Thread(target=self.start_server, args=(self._loop,))
        t.start()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--is_client", action="store_true", default=False)
    parser.add_argument("-u", "--uri", type=str, default=None)
    parser.add_argument("-hn", "--hostname",  type=str, default=None)
    parser.add_argument("-p", "--port",  type=int, default=8000)
    args = parser.parse_args()

    websocket_object = WS(args.is_client, uri=args.uri, host=args.hostname, port=args.port)
    websocket_object.start()
