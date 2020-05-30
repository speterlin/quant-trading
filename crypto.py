# don't run active terminals on different computers (when ran #get_coin_data resulted in losing locally (in venv) installed pycoingecko)
import pandas as pd
import numpy as np

from pycoingecko import CoinGeckoAPI
from datetime import datetime, timedelta
import time

cg = CoinGeckoAPI()

# date is a string in format '%d-%m-%Y', make sure historical time is on utc time, CoinGecko historical saves in UTC time and uses opening price for that day
def get_coin_data(coin, date=None, historical=False, retry_current_if_no_historical_market_data=False):
    # probably refactor, if run on current day and utc time is before midnight / want most recent price
    if not historical: # or date == datetime.now().strftime('%d-%m-%Y')
        data = cg.get_coin_by_id(id=coin)
    else:
        data = cg.get_coin_history_by_id(coin, date=date)
        if ('market_data' not in data or not data['market_data']['market_cap']['usd']) and retry_current_if_no_historical_market_data and (date == datetime.utcnow().strftime('%d-%m-%Y')):
            print("Retrying current since no historical market data and day is current day for coin: " + coin + " at utc time: " + str(datetime.utcnow()))
            data = get_coin_data(coin) # no need for retries / recursive break out loop since historical passed as False
    # maybe refactor and add if 'market_data' not in data or not data['market_data']['market_cap']['usd']: print('Error') and make data['market_data']['current_price']['usd'] = None
    return data

import requests

# same as in crypto.py
def _fetch_data(func, params, error_str, empty_data, retry=True):
    try:
        data = func(**params)
    except (ValueError, TypeError) as e:
        print(str(e) + error_str)
        data = empty_data
    except Exception as e:
        print(str(e) + error_str)
        data = empty_data
        if retry and ((type(e) in [UnboundLocalError, TimeoutError]) or (type(e) == requests.exceptions.HTTPError and e.response.status_code == 429)): # UnboundLocalError because of response error, if use urllib for request TimeoutError is urllib.error.URLError: <urlopen error [Errno 60] Operation timed out>
            time.sleep(60) # Unsure of request limit for Google Trends other sites, but quote-feed.zacks.com has: Caused by SSLError(SSLError("bad handshake: SysCallError(60, 'ETIMEDOUT')",),)
            data = _fetch_data(func, params, error_str, empty_data, retry=False)
    return data

import personal # need to make sure personal.py is in same directory
from binance.client import Client as BinanceClient # github: binance-exchange/python-binance

binance_client = BinanceClient(personal.api_key, personal.api_secret)

from twilio.rest import Client as TwilioClient

# the following line needs your Twilio Account SID and Auth Token
twilio_client = TwilioClient(personal.twilio_account_sid, personal.twilio_auth_token)

# change the "from_" number to your Twilio number and the "to" number
# to the phone number you signed up for Twilio with, or upgrade your
# account to send SMS to any phone number
twilio_client.messages.create(to="+14158028566", from_="+12069845866", body="Hello from Q!!")

# can add option for market or limit, but for now only limit orders, can also add options for different kind of timeInForce options, also add option to trade on another exchange if necessary
def trade_coin(symbol_pair=None, trade=None, price_in_btc=None, quantity=None): # don't like non-boolean value for trade value but having two bool values would complicate matters (i.e if both set to True etc.)
    client_side = BinanceClient.SIDE_SELL if trade == "sell" else BinanceClient.SIDE_BUY if trade == "buy" else None # precautionary, case sensitive and string has to be either 'buy' or 'sell' otherwise error in order
    order = binance_client.create_order(
        symbol=symbol_pair,
        side=client_side,
        type=BinanceClient.ORDER_TYPE_LIMIT,
        timeInForce='GTC', # 'day' would be ideal
        price='{:.8f}'.format(price_in_btc), # 1e-08 is maximum precision allowed by Binance, HOTBTC has lowest price on Binance right now (2020-05-25): $0.000617 (0.00000007BTC), should only worry about precision if a coin worth this much stays the same price and BTC price >= $60,000 (a factor of 1e8 difference)
        quantity=quantity # have to be ware of minimum buys (especially for coins with low value, usually 0.0001BTC)
    )
    if not order['fills']:
        time.sleep(15) # since order needs to process
    open_orders = binance_client.get_open_orders(symbol=symbol_pair)
    print(open_orders)
    # logic for processing incomplete order
    # if not open_orders:
    #     order_price, order_quantity = order['fills'][0]['price'], order['fills'][0]['qty'] # precautionary, order_quantity should be same as quantity
    #     print(order_price)
    # elif open_orders[] !=
    message_body = "Q Trading: " + symbol_pair + " " + trade + " at price: " + str(price_in_btc) + " and quantity: " + str(quantity) + (" not filled :(" if open_orders else " filled!!")
    twilio_client.messages.create(to="+14158028566", from_="+12069845866", body=message_body)
    return order

BTC_INVEST = 0.0001
symbol_pair = 'CNDBTC' # 'HOTBTC'
binance_pairs_with_price = {price['symbol']: float(price['price']) if price['price'] else 0 for price in binance_client.get_all_tickers()}
binance_pairs_with_price['BTCUSDT']
price_in_btc = binance_pairs_with_price[symbol_pair] # price = binance_pairs_with_price[symbol], but doesn't speed up much
price = price_in_btc*binance_pairs_with_price['BTCUSDT']
# depth = binance_client.get_order_book(symbol=symbol) # just shows the number of bids at various prices and asks at various prices
quantity = round(BTC_INVEST / price_in_btc) # round up for now

trade_coin(symbol_pair=symbol_pair, trade="sell", price_in_btc=price_in_btc, quantity=quantity)

# only if order is filled immediately
order_time = datetime.fromtimestamp(order['transactTime']/1000)
order_price, order_quantity = order['fills'][0]['price'], order['fills'][0]['qty'] # might be an issue if there are multiple fills as if in a big order has different prices and quantities

open_orders = binance_client.get_open_orders()
my_trades = binance_client.get_my_trades(symbol=symbol_pair)
account_status = binance_client.get_account_status()
deposit_history = binance_client.get_deposit_history()

assets = pd.DataFrame(columns=['symbol', 'balance', 'current_date', 'current_price', 'current_value', 'current_price(btc)', 'current_value(btc)', 'exchange', 'other_notes']).astype({'symbol': 'object', 'balance': 'float64', 'current_date': 'datetime64', 'current_price': 'float64', 'current_value': 'float64', 'current_price(btc)': 'float64', 'current_value(btc)': 'float64', 'exchange': 'object', 'other_notes': 'object'})

account = binance_client.get_account() # account gets updated after each trade
# need api call for converting coin symbol to id, coingecko
coins_symbol_to_id = {'btc': 'bitcoin', 'bnb': 'binancecoin', 'fet': 'fetch-ai', 'kmd': 'komodo', 'cnd': 'cindicator', 'coti': 'coti'}
coins_id_to_symbol = {v: k for k, v in coins_symbol_to_id.items()}
binance_pairs_with_price = {price['symbol']: float(price['price']) if price['price'] else 0 for price in binance_client.get_all_tickers()} # faster than splitting into binance_btc_pairs_with_price_in_btc and binance_usdt_pairs_with_price
btc_price = binance_pairs_with_price['BTCUSDT']
# assets 'FET', 'KMD' leftover from cryptohopper trades (unable to trade such a small amount)
for asset in account['balances']:
    balance_free, balance_locked = float(asset['free']) if asset['free'] else 0, float(asset['locked']) if asset['locked'] else 0 # locked balance means it's an order pending
    if balance_free > 0:
        symbol_pair, symbol = asset['asset'] + 'BTC', asset['asset'].lower()
        # btc/coin prices are quoted in the price of the given exchange not coingecko, and converted to usd with exchange usdt/btc (not the way coingecko does it)
        price_in_btc = binance_pairs_with_price[symbol_pair] if symbol != 'btc' else 1
        price = price_in_btc*btc_price
        assets.loc[coins_symbol_to_id[symbol], ['symbol', 'balance', 'current_date', 'current_price', 'current_value', 'current_price(btc)', 'current_value(btc)', 'exchange']] = [symbol, balance_free, datetime.now(), price, price*balance_free, price_in_btc, price_in_btc*balance_free, 'Binance'] # maybe refactor, issue with tsl_armed dtype changes from bool to object when you add a row
    if balance_locked > 0:
        print(asset['asset'] + " has locked balance of: " + str(balance_locked))

# can also trade by way of algorithm (rr), google trends (gtrends_15d), reddit subscribers/comments, twitter followers, alexa rank, etc. instead of just price (tsl, sl) and add columns and conditions for checking these / syncing between computers/data, or just add columns to improve algorithm
positions = {
    'open': pd.DataFrame(columns=['symbol', 'position', 'buy_date', 'buy_price', 'balance', 'current_date', 'current_price', 'current_pnl_%', 'exchange', 'tsl_armed', 'tsl_max_price', 'other_notes']).astype({'symbol': 'object', 'position': 'object', 'buy_date': 'datetime64', 'buy_price': 'float64', 'balance': 'float64', 'current_date': 'datetime64', 'current_price': 'float64', 'current_pnl_%': 'float64', 'exchange': 'object', 'tsl_armed': 'bool', 'tsl_max_price': 'float64', 'other_notes': 'object'}),
    'sold': pd.DataFrame(columns=['coin', 'symbol', 'position', 'buy_date', 'buy_price', 'balance', 'sell_date', 'sell_price', 'pnl_%', 'exchange', 'tsl_max_price', 'other_notes']).astype({'coin': 'object', 'symbol': 'object', 'position': 'object', 'buy_date': 'datetime64', 'buy_price': 'float64', 'balance': 'float64', 'sell_date': 'datetime64', 'sell_price': 'float64', 'pnl_%': 'float64', 'exchange': 'object', 'tsl_max_price': 'float64', 'other_notes': 'object'})
}

# need api to get average price at which all qty was bought at, time is local (PST), cindicator: 0.00000069 btc/cnd
positions['open'].loc['cindicator', ['symbol', 'position', 'buy_date', 'buy_price', 'balance', 'exchange', 'tsl_armed']] = [coins_id_to_symbol['cindicator'], 'long', pd.to_datetime('2020-05-20 19:54:32'), 0.00000069*9500, 144927, 'Binance', False] # btc/usd price is from coingecko around that time (binance price was about 0.4% higher)
positions['open'].loc['coti', ['symbol', 'position', 'buy_date', 'buy_price', 'balance', 'exchange', 'tsl_armed']] = [coins_id_to_symbol['coti'], 'long', pd.to_datetime('2020-05-25 14:17:01'), 2.54e-06*8892, 39370, 'Binance', False] # btc/usd price is from binance around that time

BTC_INVEST = 0.1
STOP_LOSS = -0.3
TRAILING_STOP_LOSS_ARM, TRAILING_STOP_LOSS_PERCENTAGE = 0.5, -0.2
while True:
    print("<< " + str(datetime.now()) + " >>")
    start_time = time.time()
    for coin in positions['open'].index: #
        # better to have price from coingecko (crypto insurance companies use it, and it represents a wider more accurate picture of the price, also if price hits tsl/sl temporarily on one exchange might be due to a demand/supply anomaly), also common to trade to btc then send btc to another exchange and transfer to fiat there, issue: coingecko only updates every 4 minutes
        coin_data, price = _fetch_data(get_coin_data, params={'coin': coin}, error_str=" - No " + "" + " coin data for: " + coin + " on date: " + str(datetime.now()), empty_data={}), None
        if 'market_data' in coin_data and coin_data['market_data']['market_cap']['usd']:
            price = coin_data['market_data']['current_price']['usd']
            print(coin + ": " + str(coin_data['market_data']['current_price']['usd']), end=", ")
        else:
            print("Error retreiving market cap for coin: " + coin + " on date: " + str(datetime.now()), end=", ")
        if (positions['open'].loc[coin, 'position'] == 'long') and price: # check for if 'position' == 'long' in case implement shorting, price to ensure price was calculated on coingecko
            buy_price, symbol_pair = positions['open'].loc[coin, 'buy_price'], positions['open'].loc[coin, 'symbol'].upper() + 'BTC' # assuming BTC is base trading pair
            tsl_armed, tsl_max_price = positions['open'].loc[coin, ['tsl_armed', 'tsl_max_price']]
            price_change = (price - buy_price) / buy_price
            if not tsl_armed and price_change >= TRAILING_STOP_LOSS_ARM:
                tsl_armed, tsl_max_price = True, price
            if tsl_armed:
                tsl_price_change = (price - tsl_max_price) / tsl_max_price
                if price > tsl_max_price:
                    tsl_max_price = price
                if tsl_price_change <= TRAILING_STOP_LOSS_PERCENTAGE:
                    print("<<<< COIN SOLD due to TSL >>>>")
                    message_body = "Q Trading: " + symbol_pair + " " + "sell" + " at price: " + str(price) + " and quantity: " + str(positions['open'].loc[coin, 'balance']) + " and pnl: " + str(price_change) + " due to TSL"
                    twilio_client.messages.create(to="+14158028566", from_="+12069845866", body=message_body)
                    # binance_pairs_with_price = {price['symbol']: float(price['price']) if price['price'] else 0 for price in binance_client.get_all_tickers()} # faster than splitting into binance_btc_pairs_with_price_in_btc and binance_usdt_pairs_with_price
                    # price_in_btc, quantity = binance_pairs_with_price[symbol_pair], positions['open'].loc[coin, 'balance'] # assuming all open positions want to be sold completely
                    # trade_coin(symbol_pair=symbol_pair, trade="sell", price_in_btc=price_in_btc, quantity=round(BTC_INVEST / price_in_btc)) # if incomplete order maybe put into positions['pending/open_orders']
                    # run assets, see if full balance is gone, if any locked make partial
                    sell_price = price # tsl_max_price * (1 + TRAILING_STOP_LOSS_PERCENTAGE)
                    positions['sold'] = positions['sold'].append(positions['open'].loc[coin].drop(['current_date','current_price','current_pnl_%','tsl_armed','tsl_max_price','other_notes']).append(pd.Series([coin, datetime.now(), sell_price, (sell_price - buy_price) / buy_price, tsl_max_price, 'Sell by TSL'], index=['coin', 'sell_date', 'sell_price', 'pnl_%',  'tsl_max_price', 'other_notes'])), ignore_index=True)
                    positions['open'] = positions['open'].drop(coin)
            if price_change <= STOP_LOSS:
                print("<<<< COIN SOLD due to SL >>>>")
                message_body = "Q Trading: " + symbol_pair + " " + "sell" + " at price: " + str(price) + " and quantity: " + str(positions['open'].loc[coin, 'balance']) + " and pnl: " + str(price_change) + " due to SL"
                twilio_client.messages.create(to="+14158028566", from_="+12069845866", body=message_body)
                sell_price = price # buy_price * (1 + STOP_LOSS)
                positions['sold'] = positions['sold'].append(positions['open'].loc[coin].drop(['current_date','current_price','current_pnl_%','tsl_armed','tsl_max_price','other_notes']).append(pd.Series([coin, datetime.now(), sell_price, (sell_price - buy_price) / buy_price, tsl_max_price, 'Sell by SL'], index=['coin', 'sell_date', 'sell_price', 'pnl_%', 'tsl_max_price', 'other_notes'])), ignore_index=True)
                positions['open'] = positions['open'].drop(coin)
            positions['open'].loc[coin, ['current_date','current_price','current_pnl_%','tsl_armed','tsl_max_price']] = [datetime.now(), price, price_change, tsl_armed, tsl_max_price]
            print("[ " + coin + ": " + " price change: " + str(price_change) + ", tsl armed: " + str(tsl_armed) + ", tsl max price: " + str(tsl_max_price) + ", execution time: " + str(time.time() - start_time) + " ]")
    time.sleep(240.0 - ((time.time() - start_time) % 240.0)) # coingecko updates prices every 4 minutes
    print("\n") # since using end=", "
