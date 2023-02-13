import asyncio
import platform
from datetime import datetime, timedelta
from sys import argv
import logging
from typing import List, Any, Tuple, Optional

import aiohttp

logging.basicConfig(level=logging.INFO)


def given_values() -> List:
    accepted_values = argv
    days = 1
    currency = []
    for el in accepted_values:
        if el.isnumeric():
            days = int(el)
        elif el.isalpha() and len(el) == 3:
            currency.append(el.upper())
    return [days, currency]

async def list_dates(days: int) -> List[str]:
    if days <= 0:
        return await list_dates(1)
    elif days > 10:
        return await list_dates(10)
    else:
        dates = []
        for d in range(days):
            result = datetime.now().date() - timedelta(days=d)
            dates.append(result.strftime("%d.%m.%Y"))
        return dates

async def list_urls() -> List[str]:
    dates = await list_dates(given_values()[0])
    urls = []
    for date in dates:
        url = f'https://api.privatbank.ua/p24api/exchange_rates?date={date}'
        urls.append(url)
    return urls

async def request(url: str) -> Optional[Any]:
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

async def get_exchange(url: str) -> List[str]:
    res = await request(url)
    result = []
    if given_values()[1]:
        for currensy in given_values()[1]:
            try:
                exchange, *_ = list(filter(lambda el: el['currency'] == currensy, res['exchangeRate']))
                result.append(f"{res['date']} --- {currensy}: buy: {exchange['purchaseRateNB']}, sale: {exchange['saleRateNB']}")
            except ValueError:
                logging.error(f"Currensy {currensy} is not exist")
        return result
    else:
        exchange_eur, *_ = list(filter(lambda el: el['currency'] == 'EUR', res['exchangeRate']))
        exchange_usd, *_ = list(filter(lambda el: el['currency'] == 'USD', res['exchangeRate']))
        return [f"{res['date']} --- EUR: buy: {exchange_eur['purchaseRateNB']}, sale: {exchange_eur['saleRateNB']}", f"USD: buy: {exchange_usd['purchaseRateNB']}, sale: {exchange_usd['saleRateNB']}"]

async def run() -> Tuple:
    urls = await list_urls()
    r = []
    for url in urls:
        r.append(get_exchange(url))
    result = await asyncio.gather(*r)
    return result



if __name__ == '__main__':
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    res = asyncio.run(run())
    print(*res, sep='\n')



