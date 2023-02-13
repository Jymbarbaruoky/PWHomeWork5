import asyncio
import logging
from datetime import datetime, timedelta

import aiohttp
import websockets
import names
from websockets import WebSocketServerProtocol, WebSocketProtocolError
from websockets.exceptions import ConnectionClosedOK

logging.basicConfig(level=logging.INFO)

days = 1

async def get_days(mes: list):
    global days
    for el in mes:
        if el.isnumeric() and int(el) <= 0:
            days = 1
        elif el.isnumeric() and int(el) > 10:
            days = 10
        elif el.isnumeric():
            days = int(el)
        else:
            days = 1


async def list_dates():
    dates = []
    for d in range(days):
        result = datetime.now().date() - timedelta(days=d)
        dates.append(result.strftime("%d.%m.%Y"))
    return dates

async def request(url):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    r = await response.json()
                    return r
            logging.error(f"Error status {response.status} for {url}")
        except aiohttp.ClientConnectorError as e:
            logging.error(f"Connection error {url}: {e}")
        return None

async def list_urls():
    dates = await list_dates()
    urls = []
    for date in dates:
        url = f'https://api.privatbank.ua/p24api/exchange_rates?date={date}'
        urls.append(url)
    return urls


async def get_exchange(url):
    res = await request(url)
    exchange_eur, *_ = list(filter(lambda el: el['currency'] == 'EUR', res['exchangeRate']))
    exchange_usd, *_ = list(filter(lambda el: el['currency'] == 'USD', res['exchangeRate']))
    return f"{res['date']} --- EUR: buy: {exchange_eur['purchaseRateNB']}, sale: {exchange_eur['saleRateNB']} --- USD: buy: {exchange_usd['purchaseRateNB']}, sale: {exchange_usd['saleRateNB']}\n"


async def get_exchanges():
    urls = await list_urls()
    r = []
    for url in urls:
        r.append(get_exchange(url))
    result = await asyncio.gather(*r)
    return result


class Server:
    clients = set()

    async def register(self, ws: WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logging.info(f'{ws.remote_address} connects')

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f'{ws.remote_address} disconnects')

    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def send_to_client(self, message: tuple, ws: WebSocketServerProtocol):
        await ws.send(message)

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distrubute(ws)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)



    async def distrubute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            if message.startswith('exchange'):
                await get_days(message.split())
                r = await get_exchanges()
                await self.send_to_client(r, ws)
            else:
                await self.send_to_clients(f"{ws.name}: {message}")


async def main():
    server = Server()
    async with websockets.serve(server.ws_handler, 'localhost', 8080):
        await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())
