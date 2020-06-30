# venv/bin/python programs/crypto.py

from datetime import datetime, timedelta
import time, random

from binance.client import Client as BinanceClient # github: binance-exchange/python-binance

binance_client = BinanceClient(personal.api_key, personal.api_secret) # or use Heroku config variables: ENV['API_KEY'], ENV['API_SECRET']

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

positions = {
    'open': pd.DataFrame(columns=['symbol', 'position', 'buy_date', 'buy_price', 'balance', 'current_date', 'current_price', 'current_pnl_%', 'exchange', 'tsl_armed', 'tsl_max_price', 'other_notes']).astype({'symbol': 'object', 'position': 'object', 'buy_date': 'datetime64', 'buy_price': 'float64', 'balance': 'float64', 'current_date': 'datetime64', 'current_price': 'float64', 'current_pnl_%': 'float64', 'exchange': 'object', 'tsl_armed': 'bool', 'tsl_max_price': 'float64', 'other_notes': 'object'}),
    'open_orders': pd.DataFrame(columns=['symbol', 'position', 'buy_date', 'buy_price', 'balance', 'current_date', 'current_price', 'current_pnl_%', 'exchange', 'tsl_armed', 'tsl_max_price', 'other_notes']).astype({'symbol': 'object', 'position': 'object', 'buy_date': 'datetime64', 'buy_price': 'float64', 'balance': 'float64', 'current_date': 'datetime64', 'current_price': 'float64', 'current_pnl_%': 'float64', 'exchange': 'object', 'tsl_armed': 'bool', 'tsl_max_price': 'float64', 'other_notes': 'object'}),
    'sold': pd.DataFrame(columns=['coin', 'symbol', 'position', 'buy_date', 'buy_price', 'balance', 'sell_date', 'sell_price', 'pnl_%', 'exchange', 'tsl_max_price', 'other_notes']).astype({'coin': 'object', 'symbol': 'object', 'position': 'object', 'buy_date': 'datetime64', 'buy_price': 'float64', 'balance': 'float64', 'sell_date': 'datetime64', 'sell_price': 'float64', 'pnl_%': 'float64', 'exchange': 'object', 'tsl_max_price': 'float64', 'other_notes': 'object'})
}

positions['open'].loc['cindicator', ['symbol', 'position', 'buy_date', 'buy_price', 'balance', 'exchange', 'tsl_armed']] = [coins_id_to_symbol['cindicator'], 'long', pd.to_datetime('2020-05-20 19:54:32'), 0.00000069*9500, 144927, 'Binance', False] # btc/usd price is from coingecko around that time (binance price was about 0.4% higher)
positions['open'].loc['coti', ['symbol', 'position', 'buy_date', 'buy_price', 'balance', 'exchange', 'tsl_armed']] = [coins_id_to_symbol['coti'], 'long', pd.to_datetime('2020-05-25 14:17:01'), 2.54e-06*8892, 39370, 'Binance', False] # btc/usd price is from binance around that time

open_orders = binance_client.get_open_orders()
for coin in positions['open'].index:
    positions['open'].loc[coin, []]
    symbol = positions['open'].loc[coin, 'symbol']
    if (symbol.upper() + 'BTC') in [order['symbol'] for order in open_orders]: # assuming all orders are in BTC base
        positions['open_orders'] = positions['open_orders'].append(positions['open'].loc[coin])
        positions['open'] = positions['open'].drop(coin)

BTC_INVEST = 0.1
STOP_LOSS = -0.3
TRAILING_STOP_LOSS_ARM, TRAILING_STOP_LOSS_PERCENTAGE = 0.5, -0.2
while True:
    print("<< " + str(datetime.now()) + " >>")
    run_crypto(positions)
    if (datetime.utcnow().hour == 0) and (datetime.utcnow().minute <= 5): # 5 since runs every 4 minutes
        download_data()
        positions = update_positions(positions)

def run_crypto(): # positions
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

# see if you can run from commandline like python programs/crypto.py run_crypto

    # run algorithm to add/sell open positions
    print("<< " + str(datetime.now()) + " >>")
    start_time = time.time()
    positions = positions.update_positions(positions)
    print(str(positions) + " " + str(time.time() - start_time)) # coingecko updates prices every 4 minutes
