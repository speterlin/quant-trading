# don't run active terminals on different computers (when ran function get_coin_data resulted in losing locally (in venv) installed pycoingecko), update modules every so often, look into how can shut off algorithm remotely
import pandas as pd
import numpy as np

# data is dataframe column series
def trendline(data, order=1, reverse_to_ascending=False):
    data_index_values = data.index.values[::-1] if reverse_to_ascending else data.index.values
    coeffs = np.polyfit(data_index_values, list(data), order)
    slope = coeffs[-2]
    return float(slope)

from pycoingecko import CoinGeckoAPI
from datetime import datetime, timedelta
import time

cg = CoinGeckoAPI()

# date is a string in format '%d-%m-%Y', make sure historical time is on utc time, CoinGecko historical saves in UTC time and uses opening price for that day, refactor - can return [market_data_in_coin_data, data] to simplify logic issues later, can also move logic of retry_current_if_no_historical_market_data inside function so all of the logic is inside function
def get_coin_data(coin, date=None, historical=False, retry_current_if_no_historical_market_data=False):
    # probably refactor, if run on current day and utc time is before midnight / want most recent price
    if not historical: # or date == datetime.now().strftime('%d-%m-%Y')
        data = cg.get_coin_by_id(id=coin)
    else:
        data = cg.get_coin_history_by_id(coin, date=date)
        if ('market_data' not in data or not data['market_data']['market_cap']['usd']) and retry_current_if_no_historical_market_data and (date == datetime.utcnow().strftime('%d-%m-%Y')):
            print("Retrying current since no historical market data and day is current day for coin: " + coin + " on (utc time): " + str(datetime.utcnow()))
            data = get_coin_data(coin) # no need for retries / recursive break out loop since historical passed as False
    # maybe refactor and add if 'market_data' not in data or not data['market_data']['market_cap']['usd']: print('Error') and make data['market_data']['current_price']['usd'] = None
    return data

# Minutely data will be used for duration within 1 day, Hourly data will be used for duration between 1 day and 90 days, Daily data will be used for duration above 90 days
def get_coin_data_granular(coin, from_timestamp, to_timestamp, currency='usd'): # time is in local time (PST)
    data = cg.get_coin_market_chart_range_by_id(coin, vs_currency=currency, from_timestamp=from_timestamp, to_timestamp=to_timestamp)
    # maybe refactor and add if 'prices' not in data: print('Error') and make data['prices'] = None
    return data

def get_coins_markets(currency='usd', per_page=250, pages=1): # if decide to use less than max 250 entries per_page need to change error_str of _fetch_data executions
    same_symbol_coins = {'ftt': 'farmatrust', 'hot': 'hydro-protocol', 'stx': 'stox', 'btt': 'blocktrade', 'edg': 'edgeless', 'ghost': 'ghostprism', 'ult': 'shardus', 'box': 'box-token', 'mtc': 'mtc-mesh-network', 'spc': 'spacechain', 'ong': 'ong-social', 'comp': 'compound-coin'} # 'tac': 'traceability-chain' # same_symbol is just covering the top 1000 by market cap from coingecko on
    data = []
    for page in range(pages):
        data.extend(cg.get_coins_markets(vs_currency=currency, per_page=per_page, page=page + 1))
    for coin in data:
        if (coin['symbol'] in same_symbol_coins) and (same_symbol_coins[coin['symbol']] == coin['id']): # (list(same_symbol_coins.keys()) + list(binance_btc_api_error_coins.keys())) and coin['id'] in (list(same_symbol_coins.values()) + list(binance_btc_api_error_coins.values())): # refactor, some coins have the same symbol, find a way to select first occurence of symbol, issues with FTT and HOT
            data.remove(coin)
    return data

import requests
from binance.exceptions import BinanceAPIException, BinanceRequestException #, BinanceWithdrawException, maybe refactor and add for executing binance_trade_coin_btc exceptions (also need logic for these) for BinanceOrderException, BinanceOrderMinAmountException, BinanceOrderMinPriceException, BinanceOrderMinTotalException, BinanceOrderUnknownSymbolException, BinanceOrderInactiveSymbolException

# same as in eventregistry/quant-trading/crypto.py
# need to have ndg-httpsclient, pyopenssl, and pyasn1 (latter 2 are normally already installed) installed to deal with Caused by SSLError(SSLError("bad handshake: SysCallError(60, 'ETIMEDOUT')",),) according to https://stackoverflow.com/questions/33410577 (should also check tls_version and maybe unset https_proxy from commandline), but doesn't seem to work
def _fetch_data(func, params, error_str, empty_data, retry=True):
    try:
        data = func(**params)
    except (ValueError, TypeError) as e:
        print(str(e) + error_str)
        data = empty_data
    except Exception as e:
        print(str(e) + error_str)
        data = empty_data
        if retry and ((type(e) in [UnboundLocalError, TimeoutError, requests.exceptions.ConnectionError, requests.exceptions.TooManyRedirects, BinanceAPIException, BinanceRequestException]) or (type(e) == requests.exceptions.HTTPError and e.response.status_code == 429)): # UnboundLocalError because of response error (local variable 'response' referenced before assignment), if use urllib for request TimeoutError is urllib.error.URLError: <urlopen error [Errno 60] Operation timed out>, requests.exceptions.ConnectionError is for (even when not using urllib): NewConnectionError('<urllib3.connection.VerifiedHTTPSConnection object at 0x119429240>: Failed to establish a new connection: [Errno 60] Operation timed out and: requests.exceptions.ConnectionError: ('Connection aborted.', OSError("(54, 'ECONNRESET')",)), currently unresolved - (even when not using urllib): Max retries exceeded with url: /?t=PD (Caused by SSLError(SSLError("bad handshake: SysCallError(50/54/60, 'ENETDOWN'/'ETIMEDOUT'/'ECONNRESET')",)
            time.sleep(60) # CoinGecko has limit of 100 requests/minute therefore sleep for a minute, unsure of request limit for Google Trends
            data = _fetch_data(func, params, error_str, empty_data, retry=False)
    return data

import pickle

def save_coins_data(pages=1): # maybe refactor and add pages parameter to reflect how many pages should be saved but number of pages should be constant # historical in name to reflect the kind of data downloaded
    coins = _fetch_data(get_coins_markets, params={'currency': 'usd', 'per_page': 250, 'pages': pages}, error_str=" - No " + "" + " coins markets data with pages: " + str(pages) + " on: " + str(datetime.now()), empty_data=[]) # refactor all - ensure error_str have date:
    df_coins = pd.DataFrame(columns = ["Market Cap Rank", "Facebook Likes", "Twitter Followers", "Reddit Subscribers", "Reddit Posts & Comments 48h", "Developer Stars", "Developer Issues", "Alexa Rank", "Supply: Total-Circulating"]) # maybe refactor make columns a constant # maybe add columns like "Google Trends"
    for coin in coins:
        market_cap_rank = coin['market_cap_rank']
        coin_data = _fetch_data(get_coin_data, params={'coin': coin['id']}, error_str=" - No " + "" + " coin data for: " + coin['id'], empty_data={})
        if not coin_data:
            print("Error retrieving initial coin data for: " + coin['id'])
            df_coins.loc[coin['id'], "Market Cap Rank"] = market_cap_rank
        else:
             # 'total_supply' and 'circulating_supply' not available in historical market data
            total_supply = coin_data['market_data']['total_supply'] if coin_data['market_data']['total_supply'] else coin_data['market_data']['circulating_supply']
            # generally incomplete historical community data: facebook likes, twitter followers; developer data
            df_coins.loc[coin['id']] = [market_cap_rank, coin_data['community_data']['facebook_likes'], coin_data['community_data']['twitter_followers'], coin_data['community_data']['reddit_subscribers'], coin_data['community_data']['reddit_average_posts_48h'] + coin_data['community_data']['reddit_average_comments_48h'], coin_data['developer_data']['stars'], coin_data['developer_data']['total_issues'], coin_data['public_interest_stats']['alexa_rank'], total_supply - coin_data['market_data']['circulating_supply']]
    f = open('data/crypto/saved_coins_data/' + 'coins_' + datetime.now().strftime('%Y-%m-%d') + '.pckl', 'wb') # 2020_06_02, format is '%Y-%m-%d'
    pickle.dump(df_coins, f)
    f.close()
    return df_coins

def get_saved_coins_data(date): # date is a string in format '%Y-%m-%d'
    try:
        f = open('data/crypto/saved_coins_data/' + 'coins_' + date + '.pckl', 'rb')
        df_coins_historical = pickle.load(f)
        f.close()
    except Exception as e:
        print(str(e) + " - No coins historical saved data for date: " + date)
        df_coins_historical = pd.DataFrame(columns = ["Market Cap Rank", "Facebook Likes", "Twitter Followers", "Reddit Subscribers", "Reddit Posts & Comments 48h", "Developer Stars", "Developer Issues", "Alexa Rank", "Supply: Total-Circulating"])
    return df_coins_historical

from cryptory import Cryptory

# works better than pytrends and haven't tried gtrendsR
def get_cryptory(my_cryptory, data_type, params):
    if data_type == 'google_trends':
        data = my_cryptory.get_google_trends(**params) # 2 day lag if my_cryptory to_date is current day
    if data_type == 'reddit_subscribers':
        data = my_cryptory.extract_reddit_metrics(**params) # 1 day lag if my_cryptory to_date is current day
    # extract_coinmarketcap() returning empty Dataframe: Change the dataframe index in line 129 from 0 to 2.
    return data

import personal # need to make sure personal.py is in same directory
from binance.client import Client as BinanceClient # github: binance-exchange/python-binance

binance_client = BinanceClient(personal.api_key, personal.api_secret)

from twilio.rest import Client as TwilioClient

twilio_client = TwilioClient(personal.twilio_account_sid, personal.twilio_auth_token)

import math

# can add option for market or limit, but for now only limit orders, can also add options for different kind of timeInForce options, also add option to trade on another exchange if necessary or another base currency, maybe add option for checking 24h_vol, price, pump and dump so can have logic here and return value block_trade for logic at location of trade, returning price_in_btc since a bit more accurate than coingecko price
def binance_trade_coin_btc(symbol_pair, trade=None, side=None, btc_invest=None, quantity=None, open_time=1, paper_trading=True, other_notes=None): # don't like non-boolean value for trade value but having two bool values would complicate matters (i.e if both set to True etc.) # price_in_btc=None # assuming binance processes open_order (if order not immediately filled) within a second (and not enough time for open_order to execute and avoid ~Filled), might be able to use recvWindow with api call
    if not (trade or side):
        raise ValueError('trade or side value is required')
    if not (btc_invest or quantity):
        raise ValueError("btc_invest or quantity required")
    side = side if side else BinanceClient.SIDE_SELL if trade == "sell" else BinanceClient.SIDE_BUY if trade == "buy" else None # precautionary, case sensitive and string has to be either 'buy' or 'sell' otherwise error in order # BinanceClient.SIDE_SELL is "SELL" and BinanceClient.SIDE_BUY is "BUY" but precautionary in case python-binance api changes # side is terminology used by python-binance api
    binance_pairs_with_price_current = {price['symbol']: float(price['price']) if price['price'] else 0 for price in _fetch_data(binance_client.get_all_tickers, params={}, error_str=" - Binance get all tickers error on: " + str(datetime.now()), empty_data=[])} # faster than splitting into binance_btc_pairs_with_price_in_btc and binance_usdt_pairs_with_price, # maybe refactor and use binance_client.get_ticker instead think about same speed
    price_in_btc = binance_pairs_with_price_current[symbol_pair]
    quantity = quantity if quantity else math.floor(btc_invest / price_in_btc) if btc_invest > 0.001 else math.ceil(btc_invest / price_in_btc) # have to worry about insufficient BTC available if round up and minimum order amounts (usually around $10 or 0.001 BTC as of June 12 2020) if round down - error if less than minimum: about APIError(code=-1013): Filter failure: MIN_NOTIONAL
    if paper_trading:
        message_body = "Q Trading (Paper Trading): " + symbol_pair + " " + (trade if trade else side) + " at price_in_btc " + str(price_in_btc) + " and price $" + str(price_in_btc*binance_pairs_with_price_current['BTCUSDT']) + " and quantity " + str(quantity) + ", " + str(other_notes) + ", :)"
        print("executed binance_trade_coin_btc\n" + "\033[94m" + message_body +  "\033[0m") # blue # maybe refactor and add other color to function calls
        return [quantity, price_in_btc, {}, [], None] # here and below maybe add price/price_in_btc
    # maybe refactor and add alert to ensure ok with real trading
    order = _fetch_data(binance_client.create_order, params={
        'symbol': symbol_pair,
        'side': side,
        'type': BinanceClient.ORDER_TYPE_LIMIT,
        'timeInForce': 'GTC', # 'day' would be ideal
        'price': '{:.8f}'.format(price_in_btc), # 1e-08 is maximum precision allowed by Binance, HOTBTC has lowest price on Binance right now (2020-05-25): $0.000617 (0.00000007BTC), should only worry about precision if a coin worth this much stays the same price and BTC price >= $60,000 (a factor of 1e8 difference)
        'quantity': quantity
    }, error_str=" - Binance trade execution error for symbol_pair: " + symbol_pair + ", " + (trade if trade else side) + ", " + str(btc_invest) + ", " + str(quantity) + ", " + " on: " + str(datetime.now()), empty_data={})
    if not order: # usually due to minimum amount issue, maybe refactor and raise error
        return [quantity, price_in_btc, {}, [], "BTrade Error"]
    if not order['fills']: # maybe refactor might be able to use 'executedQty'
        time.sleep(open_time) # since order not often filled immediately
    open_orders = _fetch_data(binance_client.get_open_orders, params={'symbol': symbol_pair}, error_str=" - Binance open orders error for symbol_pair: " + symbol_pair + " on: " + str(datetime.now()), empty_data=[]) # maybe refactor unnecessary if order['fills']
    trade_notes = "Filled" if (order['fills'] and not open_orders) else "Not filled" if (not order['fills'] and open_orders) else "Partially filled" if (order['fills'] and open_orders) else "~Filled" # maybe refactor - could be a situation where there is an order but no order['fills'] and no open_orders (since api processing open_order takes time or not immediately filled but within executing order and order_time - most often the case) which is not a "BTrade Error" as long as open_time=~0
    message_body = "Q Trading: " + symbol_pair + " " + (trade if trade else side) + " at price_in_btc " + str(price_in_btc) + " and price $" + str(price_in_btc*binance_pairs_with_price_current['BTCUSDT']) + " and quantity " + str(quantity) + ", " + str(other_notes) + ", " + trade_notes + (" :)" if trade_notes == "Filled" else " :/" if trade_notes == "Partially filled" else " :(")
    color_start, color_end = ["\033[92m", "\033[0m"] if trade_notes == "Filled" else ["\033[33m", "\033[0m"] if trade_notes == "Partially filled" else ["\033[91m", "\033[0m"] # green yellow red # last condition is if "Not filled" or "BTrade Error"
    print("executed binance_trade_coin_btc\n" + color_start + message_body + color_end + "\n\033[1mOrder:\033[0m " + str(order) + "\n\033[1mOpen orders:\033[0m" + str(open_orders))
    twilio_client.messages.create(to="+14158028566", from_="+12069845866", body=message_body) # maybe refactor and add twilio _fetch_twilio_data
    return [quantity, price_in_btc, order, open_orders, trade_notes] # maybe refactor and add position # can add check if order['fills'] 'qty'(s) equal quantity

# can refactor and make it exchange_check_btc_24h_vol_and_price, also add pump_and_dump_check
def binance_check_24h_vol_and_price_in_btc(binance_btc_24h_vol_in_btc, price_in_btc, binance_price_in_btc, binance_btc_24h_vol_in_btc_min=5, binance_price_in_btc_mismatch_limit=0.05):
    binance_btc_24h_vol_in_btc_too_low, binance_price_in_btc_mismatch = False, False # binance_price_in_btc_mismatch would be a sign of less demand (compared to other exchanges) for coin on binance
    if binance_btc_24h_vol_in_btc <= binance_btc_24h_vol_in_btc_min:
        binance_btc_24h_vol_in_btc_too_low = True
        message_body = "Q Trading: " + symbol_pair + " Binance 24h vol is less than " + str(binance_btc_24h_vol_in_btc_min) + " on: " + str(datetime.now()) + ", not buying :("
        print("\033[95m" + message_body + "\033[0m") # maybe refactor, repeated below but this way allows for customization and less logic at the end since both situations can occur together
        twilio_client.messages.create(to="+14158028566", from_="+12069845866", body=message_body)
    if abs((binance_price_in_btc - price_in_btc) / price_in_btc) >= binance_price_in_btc_mismatch_limit: # maybe refactor for arbitrage opportunities # very unlikely situation, but don't want to buy if overpriced, wait for price to come down
        binance_price_in_btc_mismatch = True
        message_body = "Q Trading: " + symbol_pair + " Binance price is more than " + str(binance_price_in_btc_mismatch_limit*100) + "% different than coingecko price on: " + str(datetime.now()) + ", not buying :( but maybe arbitrage :/"
        print("\033[95m" + message_body + "\033[0m")
        twilio_client.messages.create(to="+14158028566", from_="+12069845866", body=message_body)
    return [binance_btc_24h_vol_in_btc_too_low, binance_price_in_btc_mismatch]

# can refactor and change to exchange_check_arbitrage if only for exchange arbitrage, no shorting and assuming can buy and sell at either exchange/market
def check_arbitrage(price, other_price, arbitrage_roi_min=0.05):
    buy_price, sell_price = price if price <= other_price else other_price, other_price if other_price > price else price # long logic, no shorting
    arbitrage_opportunity = (sell_price - buy_price) / buy_price
    if abs(arbitrage_opportunity) >= arbitrage_roi_min:
        return [True, arbitrage_opportunity]
    return [False, arbitrage_opportunity]

from collections import Counter

def binance_btc_check_arbitrages(pages=1):
    # coins_symbol_to_id, binance_btc_pairs_api_less_same_symbol_and_api_errors = {}, []
    arbitrage_pairs = Counter()
    binance_btc_api_error_coins = {'chat': 'chatcoin', 'btt': 'bittorrent-2', 'sub': 'substratum', 'salt': 'salt', 'phx': 'red-pulse-phoenix', 'tusd': 'true-usd', 'pax': 'paxos-standard', 'npxs': 'pundi-x', 'dent': 'dent', 'wings': 'wings', 'cloak': 'cloakcoin', 'bcn': 'bytecoin', 'cocos': 'cocos-bcx', 'mft': 'mainframe', 'dgd': 'digixdao', 'key': 'selfkey', 'win': 'wink', 'ncash': 'nucleus-vision', 'rpx': 'red-pulse', 'ven': 'vechain-old-erc20', 'hsr': 'hshare', 'storm': 'storm', 'mod': 'modum', 'bchsv': 'bitcoin-cash-sv', 'icn': 'ic-node', 'trig': 'triggers', 'btcb': 'bitcoinbrand', 'bcc': 'bitcoincash-classic', 'bchabc': 'bitcoin-cash', 'edo': 'eidoo'} # rpx&hsr&storm&bchsv&icn&trig&btcb&bcc unsure of coin id (usually using coingecko.com/en/coins/coin_id) but has to do with red-pulse(-phoenix)&hshare&storm(x)&bitcoin(-cash)-sv&ic-node&triggers&bitcoinbrand/bitcoin-bep2&bitcoincash-classic, 'pnt': 'penta'/'penta-network-token', 'yoyo'(binance)/'yoyow'(coingecko), # api_error or coin is delisted/new name or type of token or not shown on Binance website as of 07/01/2020 # maybe refactor and add binance_btc_api_error_coins to other functions so these coins are updated and avoided - for now assuming that if coin is in top 250 (with rr algorithm) shouldn't have these problems
    binance_pairs_with_price_current = {price['symbol']: float(price['price']) if price['price'] else 0 for price in _fetch_data(binance_client.get_all_tickers, params={}, error_str=" - Binance get all tickers error on: " + str(datetime.now()), empty_data=[])}
    coins = _fetch_data(get_coins_markets, params={'currency': 'usd', 'per_page': 250, 'pages': pages}, error_str=" - No " + "" + " coins markets data with pages: " + str(pages) + " on: " + str(datetime.now()), empty_data=[]) # faster than iterating through binance pairs and retrieving price for each coin, allows for more flexibility with exchanges etc.
    for coin in coins: # refactor, some coins have the same symbol, find a way to select first occurence of symbol, issues with FTT and HOT
        # coin_data = _fetch_data(get_coin_data, params={'coin': coin['id']}, error_str=" - No " + "" + " coin data for: " + coin['id'], empty_data={})
        # if not coin_data or not ('market_data' in coin_data and 'btc' in coin_data['market_data']['current_price']):
        #     print("Error retreiving market data for coin: " + coin + " on: " + str(datetime.now()))
        #     continue
        price, symbol_pair = coin['current_price'], coin['symbol'].upper() + 'BTC'
        # coins_symbol_to_id[coin['symbol']] = coin['id']
        if (symbol_pair in binance_pairs_with_price_current) and (coin['symbol'] not in binance_btc_api_error_coins.keys()):
            # binance_btc_pairs_api_less_same_symbol_and_api_errors.append(symbol_pair)
            binance_price = binance_pairs_with_price_current[symbol_pair]*binance_pairs_with_price_current['BTCUSDT'] # price, = coin_data['market_data']['current_price']['btc'],
            arbitrage, arbitrage_opportunity = check_arbitrage(price=price, other_price=binance_price)
            if arbitrage:
                arbitrage_pairs[symbol_pair] = arbitrage_opportunity
    return arbitrage_pairs

import re # from collections import Counter

def update_portfolio_postions_back_testing(portfolio, stop_day, end_day, **params):
    STOP_LOSS = portfolio['constants']['sl']
    TRAILING_STOP_LOSS_ARM, TRAILING_STOP_LOSS_PERCENTAGE = portfolio['constants']['tsl_a'], portfolio['constants']['tsl_p']
    END_DAY_OPEN_POSITIONS_GTRENDS_15D, END_DAY_OPEN_POSITIONS_BINANCE_BTC_24H_VOL = portfolio['constants']['end_day_open_positions_gtrends_15d'], portfolio['constants']['end_day_open_positions_binance_btc_24h_vol']
    binance_pairs_with_price_current = params['binance_pairs_with_price_current']
    # sell if TSL or SL, update current positions (assume symbol doesn't change), update current google trends and/or binance btc 24h vol if conditions met, update current positions
    for coin in portfolio['open'].index: # print(str(stop_day) + "\n" + str(portfolio['open'].drop(['binance_btc_24h_vol(btc)', 'rank_rise_d', 'gtrends_15d'], axis=1))) # print("updating: " + coin, end=", ") # print("buying: " + coin, end=", ") # print(str(stop_day) + "\n" + str(portfolio['open'].drop(['position', 'buy_date', 'buy_price(btc)', 'balance'], axis=1)))
        # time is local time (PST) not utc time, price and time are in hourly intervals even within 24 hours
        if portfolio['open'].loc[coin, 'current_date'].date() >= stop_day.date(): # in case re-run existing portfolio over same days with existing coins to avoid selling incorrectly to TSL (too early) due to tsl_max_price set on future day
            continue
        # coin_data_granular = _fetch_data(get_coin_data_granular, params={'coin': coin, 'currency': 'usd', 'from_timestamp': datetime.timestamp(stop_day - timedelta(days=1)), 'to_timestamp': datetime.timestamp(stop_day)}, error_str=" - No granular coin data for: " + coin + " from: " + str(stop_day - timedelta(days=1)) + " to: " + str(stop_day), empty_data={}) # if think in terms of ultimately accumulating btc can make currency 'btc' and have tsl/sl be in relation to btc rather than usd
        coin_data_granular_in_btc = _fetch_data(get_coin_data_granular, params={'coin': coin, 'currency': 'btc', 'from_timestamp': datetime.timestamp(stop_day - timedelta(days=1)), 'to_timestamp': datetime.timestamp(stop_day)}, error_str=" - No granular coin data for: " + coin + " from: " + str(stop_day - timedelta(days=1)) + " to: " + str(stop_day), empty_data={})
        if 'prices' not in coin_data_granular_in_btc: # 'market_data' not in coin_data or not coin_data['market_data']['market_cap']['usd']: # remove granular from error_str
            print("Error retreiving granular market data for coin: " + coin + " on date: " + stop_day.strftime('%Y-%m-%d')) # error message should be covered in method
            portfolio['open'].loc[coin, 'other_notes'] = "MDI " +  stop_day.strftime('%Y-%m-%d') # MDI stands for Market Data Issue
        else:
            buy_price_in_btc, tsl_armed, tsl_max_price_in_btc, balance = portfolio['open'].loc[coin, ['buy_price(btc)', 'tsl_armed', 'tsl_max_price(btc)', 'balance']]
            symbol_pair = portfolio['open'].loc[coin, 'symbol'].upper() + 'BTC'
            # can add price_trend or google_trend analysis
            for idx,timestamp_price_in_btc in enumerate(coin_data_granular_in_btc['prices']):
                price_in_btc, interval_time = timestamp_price_in_btc[1], datetime.fromtimestamp(timestamp_price_in_btc[0]/1000) # CoinGecko timestamp is off by factor of 1000
                price_in_btc_change = (price_in_btc - buy_price_in_btc) / buy_price_in_btc
                # if price_in_btc_change >= TAKE_PROFIT_PERCENTAGE:
                if not tsl_armed and price_in_btc_change >= TRAILING_STOP_LOSS_ARM:
                    tsl_armed, tsl_max_price_in_btc = True, price_in_btc
                if tsl_armed:
                    tsl_price_in_btc_change = (price_in_btc - tsl_max_price_in_btc) / tsl_max_price_in_btc
                    if price_in_btc > tsl_max_price_in_btc:
                        tsl_max_price_in_btc = price_in_btc
                    if tsl_price_in_btc_change <= TRAILING_STOP_LOSS_PERCENTAGE:
                        # coin_data_granular_in_btc = _fetch_data(get_coin_data_granular, params={'coin': coin, 'currency': 'btc', 'from_timestamp': datetime.timestamp(stop_day - timedelta(days=1)), 'to_timestamp': datetime.timestamp(stop_day)}, error_str=" - No granular coin data for: " + coin + " from: " + str(stop_day - timedelta(days=1)) + " to: " + str(stop_day), empty_data={}) # more time consuming (0.03 vs. 0.003) but more accurate than doing btc_data on stop_day and obtaining btc_price - would be the price for that stop_day (i.e. if sold 2020-06-01 20:00:00 PST btc_price will be (stop_day) btc_price: 2020-06-02 17:00:00 PST) # maybe refactor and check if 'prices' not in coin_data_granular for now let it fail during back_testing don't want to add logic for adding/replacing more important other_notes
                        sell_price_in_btc = price_in_btc # sell_price, sell_price_in_btc = price, coin_data_granular_in_btc['prices'][idx][1] # tsl_max_price * (1 + TRAILING_STOP_LOSS_PERCENTAGE) # use price even though Minutely data will be used for duration within 1 day, Hourly data will be used for duration between 1 day and 90 days, Daily data will be used for duration above 90 days, since tsl_max_price might also be a bit inaccurate # * (1 - PRICE_UNCERTAINTY_PERCENTAGE)
                        other_notes, trade_notes = 'Sell by TSL', None # maybe refactor not likely that market_data wont be in btc_data - other_notes[:2] + other_notes[7:9] gives you sUBP allows to see both notes # precautionary trade_notes while back_testing should always be None
                        portfolio['balance']['btc'] = portfolio['balance']['btc'] + sell_price_in_btc*balance
                        portfolio['sold'], portfolio['open'] = portfolio['sold'].append(portfolio['open'].loc[coin].drop(['current_date', 'current_price(btc)', 'current_roi(btc)', 'binance_btc_24h_vol(btc)', 'tsl_armed', 'tsl_max_price(btc)', 'trade_notes', 'other_notes']).append(pd.Series([coin, interval_time, sell_price_in_btc, (sell_price_in_btc - buy_price_in_btc) / buy_price_in_btc, portfolio['open'].loc[coin, 'binance_btc_24h_vol(btc)'], tsl_max_price_in_btc, trade_notes, other_notes], index=['coin', 'sell_date', 'sell_price(btc)', 'roi(btc)', 'binance_btc_24h_vol(btc)', 'tsl_max_price(btc)', 'trade_notes', 'other_notes'])), ignore_index=True), portfolio['open'].drop(coin)
                        break
                elif price_in_btc_change <= STOP_LOSS:
                    # coin_data_granular_in_btc = _fetch_data(get_coin_data_granular, params={'coin': coin, 'currency': 'btc', 'from_timestamp': datetime.timestamp(stop_day - timedelta(days=1)), 'to_timestamp': datetime.timestamp(stop_day)}, error_str=" - No granular coin data for: " + coin + " from: " + str(stop_day - timedelta(days=1)) + " to: " + str(stop_day), empty_data={})
                    sell_price_in_btc = price_in_btc # sell_price, sell_price_in_btc = price, coin_data_granular_in_btc['prices'][idx][1] # buy_price * (1 + STOP_LOSS) # use price even though Minutely data will be used for duration within 1 day, Hourly data will be used for duration between 1 day and 90 days, Daily data will be used for duration above 90 days, since buy_price might also be a bit inaccurate and unrealistic to sell at exact STOP_LOSS loss # * (1 - PRICE_UNCERTAINTY_PERCENTAGE)
                    other_notes, trade_notes = 'Sell by SL', None # maybe refactor not likely that market_data wont be in btc_data - other_notes[:2] + other_notes[7:9] gives you sUBP allows to see both notes # precautionary trade_notes while back_testing should always be None
                    portfolio['balance']['btc'] = portfolio['balance']['btc'] + sell_price_in_btc*balance
                    portfolio['sold'], portfolio['open'] = portfolio['sold'].append(portfolio['open'].loc[coin].drop(['current_date', 'current_price(btc)', 'current_roi(btc)', 'binance_btc_24h_vol(btc)', 'tsl_armed', 'tsl_max_price(btc)', 'trade_notes', 'other_notes']).append(pd.Series([coin, interval_time, sell_price_in_btc, (sell_price_in_btc - buy_price_in_btc) / buy_price_in_btc, portfolio['open'].loc[coin, 'binance_btc_24h_vol(btc)'], tsl_max_price_in_btc, trade_notes, other_notes], index=['coin', 'sell_date', 'sell_price(btc)', 'roi(btc)', 'binance_btc_24h_vol(btc)', 'tsl_max_price(btc)', 'trade_notes', 'other_notes'])), ignore_index=True), portfolio['open'].drop(coin)
                    break
                if (idx == len(coin_data_granular_in_btc['prices']) - 1): # some days ends earlier than 16:59 like 2020-06-08 ends 15:59 (fet), 16:12 (edo), 16:29 (stmx, bnt) issue with coingecko data (but also when when run on different occasions returns different results for same day i.e. with end_day 6/14/2020 and different start days (6/17/2020 and same start days) return different end times)
                    if stop_day == end_day:
                        if END_DAY_OPEN_POSITIONS_BINANCE_BTC_24H_VOL and (symbol_pair in binance_pairs_with_price_current) and (stop_day.date() == datetime.now().date()): # maybe refactor - stop_day.date() == datetime.now().date() is a bit inaccurate (can make accurate to the hour or minute) # uses old/incomplete information - not np.isnan(portfolio['open'].loc[coin, 'binance_btc_24h_vol(btc)'])
                            binance_btc_24h_vol_in_btc = float(_fetch_data(binance_client.get_ticker, params={'symbol': symbol_pair}, error_str=" - Binance get ticker error for symbol_pair: " + symbol_pair + " on: " + str(datetime.now().date()), empty_data={})['quoteVolume']) # *binance_pairs_with_price_current['BTCUSDT'] # here, buying have to account for error if coin is no longer listed on binance # binance_client.get_ticker other useful keys 'bidPrice', 'bidQty', 'askPrice', 'askQty' OHLV
                            portfolio['open'].loc[coin, 'binance_btc_24h_vol(btc)'] = binance_btc_24h_vol
                        if END_DAY_OPEN_POSITIONS_GTRENDS_15D:
                            my_cryptory, coin_search_term = Cryptory(from_date=(stop_day - timedelta(days=15)).strftime('%Y-%m-%d'), to_date=stop_day.strftime('%Y-%m-%d')), coin if not re.search('-', coin) else coin.split("-")[0] # split since google trends queries don't return enough results / related queries for joint word # 15 days because from observations seems like a good amount
                            google_trends = _fetch_data(get_cryptory, params={'my_cryptory': my_cryptory, 'data_type': 'google_trends', 'params': {'kw_list': [coin_search_term]}}, error_str=" - No " + "google trends" + " data for coin search term: " + coin_search_term + " from: " + str(stop_day - timedelta(days=15)) + " to: " + str(stop_day), empty_data=pd.DataFrame())
                            google_trends_slope = trendline(google_trends.sort_values('date', inplace=False, ascending=True)[coin_search_term], reverse_to_ascending=True) if not google_trends.empty else None
                            portfolio['open'].loc[coin, 'gtrends_15d'] = google_trends_slope
                    portfolio['open'].loc[coin, ['current_date', 'current_price(btc)', 'current_roi(btc)', 'tsl_armed', 'tsl_max_price(btc)']] = [interval_time, price_in_btc, price_in_btc_change, tsl_armed, tsl_max_price_in_btc]
    return portfolio

def run_portfolio_rr(portfolio, start_day=None, end_day=None, rr_sell=True, paper_trading=True, back_testing=False): # start_day and end_day are datetime objects # short = False, possibly add short logic # can get rid of back_testing parameter and add logic like start_day.date() < (end_day - timedelta(days=DAYS)).date(), # maybe refactor and add long_position = 'long-p' if paper_trading else 'long'
    print("running run_portfolio_rr")
    UP_MOVE, DOWN_MOVE = portfolio['constants']['up_down_move'], -portfolio['constants']['up_down_move']
    DAYS = portfolio['constants']['days']
    STOP_LOSS = portfolio['constants']['sl']
    TRAILING_STOP_LOSS_ARM, TRAILING_STOP_LOSS_PERCENTAGE = portfolio['constants']['tsl_a'], portfolio['constants']['tsl_p'] # TAKE_PROFIT_PERCENTAGE = 1.0
    BTC_INVEST, BTC_INVEST_MIN = portfolio['constants']['btc_invest'], portfolio['constants']['btc_invest_min']
    BUY_DATE_GTRENDS_15D, END_DAY_OPEN_POSITIONS_GTRENDS_15D, END_DAY_OPEN_POSITIONS_BINANCE_BTC_24H_VOL = portfolio['constants']['buy_date_gtrends_15d'], portfolio['constants']['end_day_open_positions_gtrends_15d'], portfolio['constants']['end_day_open_positions_binance_btc_24h_vol']
    # PRICE_UNCERTAINTY_PERCENTAGE = 0.05 # to reflect that can't always buy/sell at CoinGecko price and that stop loss and trailing stop loss orders can't always be fulfilled at the exact percentage
    binance_pairs_with_price_current = {price['symbol']: float(price['price']) if price['price'] else 0 for price in _fetch_data(binance_client.get_all_tickers, params={}, error_str=" - Binance get all tickers error on: " + str(datetime.now()), empty_data=[])}
    end_day = end_day if end_day else datetime.now().replace(hour=17, minute=0, second=0, microsecond=0) # better to be on utc time, PST 17h is 24h UTC time, CoinGecko historical saves in UTC time # 02/24/2020 is first day with 100 coins, 02/27/2020 is first day with 200 coins, 03/09/2020 is first day with 250 coins # maybe refactor and make start/stop/end_datetime instead of start/stop/end_day
    start_day = start_day if start_day else end_day - timedelta(days=DAYS) # not this - datetime.strptime('2020_02_24 17:00:00', '%Y_%m_%d %H:%M:%S') - since back_testing=False (default)
    stop_day = start_day + timedelta(days=DAYS) # if running in real time stop_day should be almost equivalent (minus processing times) to datetime.now()
    if (back_testing and not paper_trading) or (not back_testing and ((start_day.date() < (end_day - timedelta(days=DAYS)).date()) or (end_day.date() < datetime.now().date()))): # don't allow back running:
        print("Error (back testing and not paper trading) or back running")
        return portfolio
    retry_end_day_if_no_historical_market_data = True if datetime.utcnow() >= (end_day + timedelta(hours=7)) and datetime.utcnow() <= (end_day + timedelta(hours=7+1)) else False # if run between closing and 1 hour after closing time and historical market_data for stop day (next day in utc time) day not available allow retry on current day, useful if want to make trades within that hour
    while stop_day.date() <= end_day.date():
        if back_testing:
            portfolio = update_portfolio_postions_back_testing(portfolio=portfolio, stop_day=stop_day, end_day=end_day, binance_pairs_with_price_current=binance_pairs_with_price_current)
        df_coins_interval_start, df_coins_interval_stop = get_saved_coins_data(date=(stop_day - timedelta(days=DAYS)).strftime('%Y-%m-%d')).iloc[:250], get_saved_coins_data(date=stop_day.strftime('%Y-%m-%d')).iloc[:250]
        # buy if coin increases in market cap rank by UP_MOVE over DAYS, sell if coin decreases by DOWN_MOVE over DAYS
        if not (df_coins_interval_start.empty or df_coins_interval_stop.empty):
            # can also add google trends, reddit possibly chart first coordinate with price timestamp
            coins_to_buy, coins_to_sell = [], [] # multi-dimensional array [coin, market_cap_rank_change] # coins_market_cap_rank_change_by_factor = Counter()
            for coin in df_coins_interval_stop.index: # maybe refactor - if add more coins to saved_coins_data can add df_coins_interval_stop/start[:250] so only review certain section of saved_coins_data
                new_market_cap_rank = df_coins_interval_stop.loc[coin, 'Market Cap Rank']
                try: # if else statement same number of lines
                    market_cap_rank_change = df_coins_interval_start.loc[coin, 'Market Cap Rank'] - new_market_cap_rank
                except Exception as e: # print(str(e) + " - Could not get historical saved market cap rank for: " + coin)
                    market_cap_rank_change = len(df_coins_interval_start) - new_market_cap_rank if len(df_coins_interval_stop) == len(df_coins_interval_start) else 0 # don't add UP_MOVE/DOWN_MOVE to be safe
                if market_cap_rank_change >= UP_MOVE:
                    coins_to_buy.append([coin, market_cap_rank_change])
                elif market_cap_rank_change <= DOWN_MOVE:
                    coins_to_sell.append([coin, market_cap_rank_change]) # coins_market_cap_rank_change_by_factor[coin] = market_cap_rank_change
            for coin in list(set(df_coins_interval_start.index.values) - set(df_coins_interval_stop.index.values)):
                # len(df_coins_interval_stop) >= len(df_coins_interval_start) should always be true therefore logic works, if coin not in new dataframe assume it has fallen out of top coins: len(df_coins_interval_start) - DOWN_MOVE (to be safe, and DOWN_MOVE assumed to be negative value)
                coins_to_sell.append([coin, df_coins_interval_start.loc[coin, 'Market Cap Rank'] - (len(df_coins_interval_start) - DOWN_MOVE)]) # market_cap_rank_change unused and inaccurate but still saving # coins_market_cap_rank_change_by_factor[coin] = df_coins_interval_start.loc[coin, 'Market Cap Rank'] - (len(df_coins_interval_start) - DOWN_MOVE)
            for coin, market_cap_rank_change in coins_to_buy: # coins_market_cap_rank_change_by_factor.items()
                if coin not in portfolio['open'].index and (portfolio['balance']['btc'] >= BTC_INVEST_MIN): # can add max open positions and a waiting list to reflect real trading: # assuming always enforcing BTC_INVEST_MIN # (market_cap_rank_change >= UP_MOVE) and
                    btc_invest = BTC_INVEST if (portfolio['balance']['btc'] >= BTC_INVEST) else portfolio['balance']['btc']
                    if back_testing:
                        coin_data = _fetch_data(get_coin_data, params={'coin': coin, 'date': (stop_day + timedelta(hours=7)).strftime('%d-%m-%Y'), 'historical': True, 'retry_current_if_no_historical_market_data': retry_end_day_if_no_historical_market_data}, error_str=" - No " + "historical" + " coin data for: " + coin + " on date: " + str(stop_day + timedelta(hours=7)), empty_data={})
                    else:
                        coin_data = _fetch_data(get_coin_data, params={'coin': coin}, error_str=" - No " + "" + " coin data for: " + coin + " on: " + str(datetime.now()), empty_data={}) # retrieving coin_data even when not back_testing as a double check for market cap rank and to retreive symbol, input price_in_btc for function binance_check_24h_vol_and_price_in_btc
                    # error with some coins (bitbay), if these 2 conditions aren't meant usually indicate larger issues with the coin, further if error retreiving market cap rank whole basis for algorithm falls apart (market cap rank is meaningless)
                    if 'market_data' in coin_data and coin_data['market_data']['market_cap']['usd']: # refactor can probably get rid of coin_data['market_data']['market_cap']['usd'] / 'usd'/'btc' in coin_data['market_data']['market_cap']/['current_price']
                        # can add other exchanges
                        symbol_pair = coin_data['symbol'].upper() + 'BTC' # maybe refactor name to btc_symbol_pair or just symbol_pair like other instances
                        if symbol_pair in binance_pairs_with_price_current: # not retrieving new prices since whole function should execute (if done over one DAYS period) quickly
                            price_in_btc = coin_data['market_data']['current_price']['btc'] # price, price_in_btc = coin_data['market_data']['current_price']['usd'], coin_data['market_data']['current_price']['btc'] # maybe refactor -  assuming that if 'market_data' in coin_data and coin_data['market_data']['market_cap']['usd'] ('usd' and 'btc') in coin_data['market_data']['current_price'] also in there
                            if back_testing: # maybe refactor and put this logic into function binance_trade_coin_btc, maybe also include binance_check_24h_vol_and_price_in_btc in back_testing purchases
                                buy_date, binance_btc_24h_vol_in_btc, quantity, trade_notes = stop_day, None, math.floor(btc_invest / price_in_btc) if btc_invest > 0.001 else math.ceil(btc_invest / price_in_btc), None # btc_price / price # assuming buying at 17 PST and that order is filled near coingecko price (maybe refactor) # precautionary keep > 0.001 in case BTC_INVEST_MIN is set below this amount
                            else:
                                binance_btc_24h_vol_in_btc = float(_fetch_data(binance_client.get_ticker, params={'symbol': symbol_pair}, error_str=" - Binance get ticker error for symbol_pair: " + symbol_pair + " on date: " + str(datetime.now().date()), empty_data={})['quoteVolume']) # *binance_pairs_with_price_current['BTCUSDT'] # no need to check for - if stop_day.date() == datetime.now().date() else None since no back running, also a bit inaccurate (can make accurate to the hour or minute) # can get historical total_volume (exchange-weighted 24h_vol) with coin_data but can't get historical binance_btc_24h_vol (Binance symbol_pair 24h_vol)
                                binance_btc_24h_vol_in_btc_too_low, binance_price_in_btc_mismatch = binance_check_24h_vol_and_price_in_btc(binance_btc_24h_vol_in_btc=binance_btc_24h_vol_in_btc, price_in_btc=price_in_btc, binance_price_in_btc=binance_pairs_with_price_current[symbol_pair], binance_price_in_btc_mismatch_limit=0.05) # *binance_pairs_with_price_current['BTCUSDT'] # add pump_and_dump_check
                                if binance_btc_24h_vol_in_btc_too_low or binance_price_in_btc_mismatch:
                                    continue
                                quantity, price_in_btc, binance_coin_btc_order, binance_coin_btc_open_orders, trade_notes = binance_trade_coin_btc(symbol_pair=symbol_pair, trade="buy", btc_invest=btc_invest, open_time=1, paper_trading=paper_trading) # maybe refactor and change binance_coin_btc... to binance_btc_..., binance_coin_btc may be good to reflect importance (exchange order)
                                buy_date = datetime.now() # if not back_testing buying when run the algorithm, also if back running need to use datetime.now() and if real time running datetime.now() is closer to time order is processed due to api request limits, processing, etc.
                            if BUY_DATE_GTRENDS_15D:
                                my_cryptory, coin_search_term = Cryptory(from_date=(stop_day - timedelta(days=15)).strftime('%Y-%m-%d'), to_date=stop_day.strftime('%Y-%m-%d')), coin if not re.search('-', coin) else coin.split("-")[0]
                                google_trends = _fetch_data(get_cryptory, params={'my_cryptory': my_cryptory, 'data_type': 'google_trends', 'params': {'kw_list': [coin_search_term]}}, error_str=" - No " + "google trends" + " data for coin search term: " + coin_search_term + " from: " + str(stop_day - timedelta(days=15)) + " to: " + str(stop_day), empty_data=pd.DataFrame())
                                google_trends_slope = trendline(google_trends.sort_values('date', inplace=False, ascending=True)[coin_search_term], reverse_to_ascending=True) if not google_trends.empty else None
                            else:
                                google_trends_slope = 0
                            portfolio['balance']['btc'] = portfolio['balance']['btc'] - price_in_btc*quantity # btc value not entirely accurate in real time and doesn't take into account distribution tokens but close enough to prevent trades from executing if underbudget, also don't check assets since want to allocate full btc value to coin # (price / btc_price) # a bit more accurate than using just btc_invest since rounding for quantity: quantity = math.floor(btc_invest*btc_price / price)
                            portfolio['open'].loc[coin, ['symbol', 'position', 'balance', 'buy_date', 'buy_price(btc)', 'current_date', 'current_price(btc)', 'current_roi(btc)', 'rank_rise_d', 'gtrends_15d', 'binance_btc_24h_vol(btc)', 'tsl_armed', 'trade_notes']] = [coin_data['symbol'], 'long', quantity] + [buy_date, price_in_btc]*2 + [0, market_cap_rank_change, google_trends_slope, binance_btc_24h_vol_in_btc, False, trade_notes]
                    else: # don't add coin if issue retreiving market_data
                        print("Error retreiving initial market cap for coin: " + coin + " on date: " + stop_day.strftime('%Y-%m-%d'))
            for coin, market_cap_rank_change in coins_to_sell:
                if rr_sell and (coin in portfolio['open'].index): # can add short logic # not accounting for if there is a market data issue (MDI when backtesting) - if sell price and roi doesn't reflect actual, can try to postpone selling by a day # (market_cap_rank_change <= DOWN_MOVE) and
                    symbol_pair, balance = portfolio['open'].loc[coin, 'symbol'].upper() + 'BTC', portfolio['open'].loc[coin, 'balance'] # maybe refactor all and change balance variable name to order_quantity
                    if back_testing:
                        sell_date, sell_price_in_btc, roi_in_btc, binance_btc_24h_vol_in_btc, other_notes = portfolio['open'].loc[coin, ['current_date', 'current_price(btc)', 'current_roi(btc)', 'binance_btc_24h_vol(btc)', 'other_notes']] # not using slightly more accurate price with coin_data['market_data']['current_price']['usd'] and date using stop_day (16:.. vs. 17 PST) since then have to retrieve coin_data and recalculate roi
                        # coin_data = _fetch_data(get_coin_data, params={'coin': coin, 'date': (stop_day + timedelta(hours=7)).strftime('%d-%m-%Y'), 'historical': True, 'retry_current_if_no_historical_market_data': retry_end_day_if_no_historical_market_data}, error_str=" - No " + "historical" + " coin data for: " + coin + " on date: " + str(stop_day + timedelta(hours=7)), empty_data={})
                        # sell_price_in_btc, other_notes_extra = [coin_data['market_data']['current_price']['btc'], None] if ('market_data' in coin_data and 'btc' in coin_data['market_data']['current_price']) else [sell_price/binance_pairs_with_price_current['BTCUSDT'], "sUsing BPrice"]
                        other_notes, trade_notes = other_notes, None # other_notes if not other_notes_extra else other_notes_extra[:2] + other_notes_extra[7:9] + str(other_notes), None # only concatenate other_notes strings while back_testing since MDI issue notes only occur during back_testing, should be taken care of if back_testing and then real time trading, other_notes_extra[:2] + other_notes_extra[7:9] gives you sUBP allows to see both notes # precautionary trade_notes while back_testing should always be None
                    else: # only rr_sell if running in real time, no need to worry about back running (if back running and algorithm has gotten to the current day) - stop_day.date() == datetime.now().date()
                        sell_date, binance_btc_24h_vol_in_btc = datetime.now(), float(_fetch_data(binance_client.get_ticker, params={'symbol': symbol_pair}, error_str=" - Binance get ticker error for symbol_pair: " + symbol_pair + " on date: " + str(datetime.now().date()), empty_data={})['quoteVolume']) # *binance_pairs_with_price_current['BTCUSDT']
                        # coin_data = _fetch_data(get_coin_data, params={'coin': coin}, error_str=" - No " + "" + " coin data for: " + coin + " on: " + str(datetime.now()), empty_data={})
                        # sell_price_in_btc, other_notes = [coin_data['market_data']['current_price']['btc'], None] if ('market_data' in coin_data and 'btc' in coin_data['market_data']['current_price']) else [binance_pairs_with_price_current[symbol_pair], "sUsing BPrice"] # sell_price, coin_data['market_data']['current_price']['usd'], ('usd' and , binance_pairs_with_price_current[symbol_pair]*binance_pairs_with_price_current['BTCUSDT'], # maybe refactor and add MDI Issue note to other_notes (but only if other_notes not occupied) # assuming selling at 17 PST and that order is filled near coingecko price (maybe refactor)
                        quantity, price_in_btc, binance_coin_btc_order, binance_coin_btc_open_orders, trade_notes = binance_trade_coin_btc(symbol_pair=symbol_pair, trade="sell", quantity=balance, open_time=1, paper_trading=(True if portfolio['open'].loc[coin, 'position'] == 'long-p' else paper_trading))
                        sell_price_in_btc, other_notes = price_in_btc, None
                        roi_in_btc = (sell_price_in_btc - portfolio['open'].loc[coin, 'buy_price(btc)']) / portfolio['open'].loc[coin, 'buy_price(btc)']
                    portfolio['balance']['btc'] = portfolio['balance']['btc'] + sell_price_in_btc*balance # (sell_price / btc_price)
                    # coin_data already retrieved in current_date, current_price, current_roi # can use np.append(coin, portfolio['open'].loc[coin, [...]].to_numpy())
                    portfolio['sold'], portfolio['open'] = portfolio['sold'].append(portfolio['open'].loc[coin].drop(['current_date', 'current_price(btc)', 'current_roi(btc)', 'binance_btc_24h_vol(btc)', 'tsl_armed', 'trade_notes', 'other_notes']).append(pd.Series([coin, sell_date, sell_price_in_btc, roi_in_btc, binance_btc_24h_vol_in_btc, trade_notes, other_notes], index=['coin', 'sell_date', 'sell_price(btc)', 'roi(btc)', 'binance_btc_24h_vol(btc)', 'trade_notes', 'other_notes'])), ignore_index=True), portfolio['open'].drop(coin)
        stop_day = stop_day + timedelta(days=1)
    return portfolio

# assets 'FET', 'KMD' leftover from cryptohopper trades (unable to trade such a small amount), 'TFUEL' because THETA funds in your account on May 2020, 'GTO' when trying to do GTOBTC arbitrage with OkEx exchange, Unsure about 'TOMO' but small amount and in top 250 so needed since sometimes: 504 Server Error: Gateway Time-out
def get_binance_assets(other_coins_symbol_to_id=None, pages=1): # maybe refactor, don't pass in portfolio since assets should have current open positions in portfolio and new added positions should be in Binance top 250, but possible if run function without assets previously loaded and a coin in assets on Binance is no longer in Binance top 250 (algorithm should sell at 17PST if coin falls out of top 250 but still possible)
    print("getting binance assets")
    account = _fetch_data(binance_client.get_account, params={}, error_str=" - Binance get account error on: " + str(datetime.now()), empty_data={}) # account gets updated after each trade # maybe refactor and include binance_client here and in other functions as a parameter
    binance_pairs_with_price_current = {price['symbol']: float(price['price']) if price['price'] else 0 for price in _fetch_data(binance_client.get_all_tickers, params={}, error_str=" - Binance get all tickers error on: " + str(datetime.now()), empty_data=[])}
    assets = pd.DataFrame(columns=['symbol','balance','balance_locked','current_date','current_price','current_value','current_price(btc)','current_value(btc)','other_notes']).astype({'symbol':'object','balance':'float64','balance_locked':'float64','current_date':'datetime64','current_price':'float64','current_value':'float64','current_price(btc)':'float64','current_value(btc)':'float64','other_notes':'object'})
    coins_symbol_to_id = {**{'btc': 'bitcoin', 'bnb': 'binancecoin', 'fet': 'fetch-ai', 'kmd': 'komodo', 'cnd': 'cindicator', 'coti': 'coti', 'tfuel': 'theta-fuel', 'tomo': 'tomochain', 'gto': 'gifto'}, **{coin['symbol']: coin['id'] for coin in _fetch_data(get_coins_markets, params={'currency': 'usd', 'per_page': 250, 'pages': pages}, error_str=" - No " + "" + " coins markets data with pages: " + str(pages) + " on: " + str(datetime.now()), empty_data=[])}}
    if other_coins_symbol_to_id:
        coins_symbol_to_id = {**coins_symbol_to_id, **other_coins_symbol_to_id} # maybe refactor and always add assets symbols & ids to coins_symbol_to_id, not sure about processing time: dict(zip(list(assets['symbol']), list(assets.index.values)))
    for asset in account['balances']:
        balance_free, balance_locked = float(asset['free']) if asset['free'] else 0, float(asset['locked']) if asset['locked'] else 0 # locked balance means it's an order pending
        if balance_free > 0:
            symbol_pair, symbol = asset['asset'] + 'BTC', asset['asset'].lower()
            # btc/coin prices are quoted in the price of the given exchange not coingecko, and converted to usd with exchange usdt/btc (not the way coingecko does it)
            price_in_btc = binance_pairs_with_price_current[symbol_pair] if symbol != 'btc' else 1
            price = price_in_btc*binance_pairs_with_price_current['BTCUSDT']
            coin = coins_symbol_to_id[symbol]
            assets.loc[coin, ['symbol','balance','balance_locked','current_date','current_price','current_value','current_price(btc)','current_value(btc)']] = [symbol, balance_free, balance_locked, datetime.now(), price, price*balance_free, price_in_btc, price_in_btc*balance_free]
            if balance_locked > 0:
                print(asset['asset'] + " has locked balance of: " + str(balance_locked))
    return assets

# can also use rate of return (takes into account time), a little bit deceiving if add new investment which has 0% return intuition says it shouldn't draw ROI down but it does since cost of investment increases but net value of investments - cost of investment stays the same
def portfolio_calculate_roi(portfolio, open_positions=True, sold_positions=False, avoid_paper_trades=False):
    current_value_of_investments, value_of_sold_investments, cost_of_investments = 0, 0, 0 # maybe refactor to avoid divide by zero errors
    if open_positions:
        for coin in portfolio['open'].index:
            if avoid_paper_trades and (portfolio['open'].loc[coin, 'position'] == 'long-p'):
                continue
            current_price_in_btc, buy_price_in_btc, balance = portfolio['open'].loc[coin, ['current_price(btc)', 'buy_price(btc)', 'balance']] # maybe refactor and multiply columns and sum
            current_value_of_investments += current_price_in_btc*balance
            cost_of_investments += buy_price_in_btc*balance
    if sold_positions: # maybe refactor and use portfolio['balance']['btc']
        for idx in portfolio['sold'].index:
            if avoid_paper_trades and (portfolio['sold'].loc[idx, 'position'] == 'long-p'):
                continue
            sell_price_in_btc, buy_price_in_btc, balance = portfolio['sold'].loc[idx, ['sell_price(btc)', 'buy_price(btc)', 'balance']] # maybe refactor and multiply columns and sum
            value_of_sold_investments += sell_price_in_btc*balance
            cost_of_investments += buy_price_in_btc*balance
    return (current_value_of_investments + value_of_sold_investments - cost_of_investments) / cost_of_investments

def portfolio_trading(portfolio, paper_trading=True, open_order_price_difference=0.15): # refactor to mimick run_portfolio_rr # short = False, possibly add short logic
    DAYS = portfolio['constants']['days']
    STOP_LOSS = portfolio['constants']['sl']
    TRAILING_STOP_LOSS_ARM, TRAILING_STOP_LOSS_PERCENTAGE = portfolio['constants']['tsl_a'], portfolio['constants']['tsl_p']
    OPEN_ORDER_PRICE_DIFFERENCE = open_order_price_difference
    while True:
        print("<< " + str(datetime.now()) + " >>")
        start_time = time.time()
        if (datetime.utcnow().hour == 12) and (datetime.utcnow().minute < 4):
            twilio_client.messages.create(to="+14158028566", from_="+12069845866", body="Q Trading: running on " + str(datetime.now()) + " :)") # maybe refactor and add twilio _fetch_twilio_data
        if (datetime.utcnow().hour == 0) and (datetime.utcnow().minute < 4): # since runs every 4 minutes
            save_coins_data(pages=4) # On 07/06/2020: from 250 to 500 (pages=2) - binance btc pairs gain is 114-163, from 500 to 750/1000 (pages=3/4) - binance btc pairs gain is 163-167, but might include more exchanges in algorithm, also top 1-250/500 market cap was from $170B-$12M/$2M/$822K/$300K
            portfolio = run_portfolio_rr(start_day=(datetime.now() - timedelta(days=DAYS)), end_day=datetime.now(), paper_trading=paper_trading, portfolio=portfolio)
            twilio_client.messages.create(to="+14158028566", from_="+12069845866", body="Q Trading: Coin data saved and run_portfolio_rr executed on: " + datetime.now().strftime('%Y-%m-%d') + " :)") # maybe refactor and add twilio _fetch_twilio_data
        for coin in portfolio['open'].index:
            # better to have price from coingecko (crypto insurance companies use it, and it represents a wider more accurate picture of the price, also if price hits tsl/sl temporarily on one exchange might be due to a demand/supply anomaly), also common to trade to btc then send btc to another exchange and transfer to fiat there, issue: coingecko only updates every 4 minutes
            coin_data, price_in_btc = _fetch_data(get_coin_data, params={'coin': coin}, error_str=" - No " + "" + " coin data for: " + coin + " on: " + str(datetime.now()), empty_data={}), None
            if 'market_data' in coin_data and coin_data['market_data']['market_cap']['usd']:
                price_in_btc = coin_data['market_data']['current_price']['btc']
                # print(coin + ": " + str(coin_data['market_data']['current_price']['usd']))
            else:
                print("Error retreiving market cap for coin: " + coin + " on: " + str(datetime.now()))
            if price_in_btc: # maybe refactor check for if 'position' == 'long'/'long-p' in case implement shorting, price to ensure price was calculated on coingecko
                buy_price_in_btc, tsl_armed, tsl_max_price_in_btc, balance = portfolio['open'].loc[coin, ['buy_price(btc)', 'tsl_armed', 'tsl_max_price(btc)', 'balance']]
                price_in_btc_change = (price_in_btc - buy_price_in_btc) / buy_price_in_btc
                symbol_pair = portfolio['open'].loc[coin, 'symbol'].upper() + 'BTC' # assuming BTC is base trading pair
                if not tsl_armed and price_in_btc_change >= TRAILING_STOP_LOSS_ARM:
                    tsl_armed, tsl_max_price_in_btc = True, price_in_btc
                if tsl_armed:
                    tsl_price_in_btc_change = (price_in_btc - tsl_max_price_in_btc) / tsl_max_price_in_btc
                    if price_in_btc > tsl_max_price_in_btc:
                        tsl_max_price_in_btc = price_in_btc
                    if tsl_price_in_btc_change <= TRAILING_STOP_LOSS_PERCENTAGE: # should check if price on coingecko is equal/close to price in binance
                        print("<<<< COIN SOLD due to TSL >>>>")
                        other_notes = 'Sell by TSL'
                        quantity, price_in_btc, binance_coin_btc_order, binance_coin_btc_open_orders, trade_notes = binance_trade_coin_btc(symbol_pair=symbol_pair, trade="sell", quantity=balance, open_time=1, paper_trading=(True if portfolio['open'].loc[coin, 'position'] == 'long-p' else paper_trading), other_notes=other_notes + " at roi " + str(price_in_btc_change))
                        sell_price_in_btc = price_in_btc # sell_price, = price, coin_data['market_data']['current_price']['btc'],  # tsl_max_price * (1 + TRAILING_STOP_LOSS_PERCENTAGE) # maybe refactor - check if 'btc' in coin_data['market_data']['current_price'], should be if 'usd' in it, logic to check for it a bit cumbersome
                        portfolio['balance']['btc'] = portfolio['balance']['btc'] + sell_price_in_btc*balance
                        portfolio['sold'], portfolio['open'] = portfolio['sold'].append(portfolio['open'].loc[coin].drop(['current_date', 'current_price(btc)', 'current_roi(btc)', 'tsl_armed', 'tsl_max_price(btc)', 'trade_notes', 'other_notes']).append(pd.Series([coin, datetime.now(), sell_price_in_btc, (sell_price_in_btc - buy_price_in_btc) / buy_price_in_btc, tsl_max_price_in_btc, trade_notes, other_notes], index=['coin', 'sell_date', 'sell_price(btc)', 'roi(btc)',  'tsl_max_price(btc)', 'trade_notes', 'other_notes'])), ignore_index=True), portfolio['open'].drop(coin)
                        continue
                elif price_in_btc_change <= STOP_LOSS: # should check if price on coingecko is equal/close to price in binance
                    print("<<<< COIN SOLD due to SL >>>>")
                    other_notes = 'Sell by SL'
                    quantity, price_in_btc, binance_coin_btc_order, binance_coin_btc_open_orders, trade_notes = binance_trade_coin_btc(symbol_pair=symbol_pair, trade="sell", quantity=balance, open_time=1, paper_trading=(True if portfolio['open'].loc[coin, 'position'] == 'long-p' else paper_trading), other_notes=other_notes + " at roi " + str(price_in_btc_change))
                    sell_price_in_btc = price_in_btc # sell_price, = price, coin_data['market_data']['current_price']['btc'], # buy_price * (1 + STOP_LOSS)
                    portfolio['balance']['btc'] = portfolio['balance']['btc'] + sell_price_in_btc*balance
                    portfolio['sold'], portfolio['open'] = portfolio['sold'].append(portfolio['open'].loc[coin].drop(['current_date', 'current_price(btc)', 'current_roi(btc)', 'tsl_armed', 'tsl_max_price(btc)', 'trade_notes', 'other_notes']).append(pd.Series([coin, datetime.now(), sell_price_in_btc, (sell_price_in_btc - buy_price_in_btc) / buy_price_in_btc, tsl_max_price_in_btc, trade_notes, other_notes], index=['coin', 'sell_date', 'sell_price(btc)', 'roi(btc)', 'tsl_max_price(btc)', 'trade_notes', 'other_notes'])), ignore_index=True), portfolio['open'].drop(coin)
                    continue
                portfolio['open'].loc[coin, ['current_date', 'current_price(btc)', 'current_roi(btc)', 'tsl_armed', 'tsl_max_price(btc)']] = [datetime.now(), price_in_btc, price_in_btc_change, tsl_armed, tsl_max_price_in_btc]
                # print("[ " + coin + ": " + " price change: " + str(price_change) + ", tsl armed: " + str(tsl_armed) + ", tsl max price: " + str(tsl_max_price) + ", execution time: " + str(time.time() - start_time) + " ]")
        print(str(portfolio['open'].tail(20).drop(['binance_btc_24h_vol(btc)', 'gtrends_15d', 'rank_rise_d', 'tsl_armed', 'tsl_max_price(btc)', 'trade_notes', 'other_notes'], axis=1)) + "\n" + str(portfolio['open'].tail(20).drop(['symbol', 'position', 'buy_date', 'buy_price(btc)', 'balance', 'current_date', 'current_price(btc)', 'current_roi(btc)'], axis=1)) + "\nCurrent ROI (BTC) (Real): " + str(portfolio_calculate_roi(portfolio, avoid_paper_trades=True)) + "\nCurrent ROI (BTC) (All): " + str(portfolio_calculate_roi(portfolio)) + "\nExecution time: " + str(time.time() - start_time) + "\n")
        if datetime.now().minute >= 30 and datetime.now().minute < 34: # runs once per hour at the end of the hour (since if save data or run algorithm at beginning of hour may have conflict since saving data and running algorithm takes time)
            print(str(portfolio['sold'].tail(20).drop(['symbol', 'binance_btc_24h_vol(btc)', 'rank_rise_d', 'tsl_max_price(btc)', 'gtrends_15d'], axis=1)) + "\nSold ROI (BTC) (Real): " + str(portfolio_calculate_roi(portfolio, open_positions=False, sold_positions=True, avoid_paper_trades=True)) + "\nSold ROI (BTC) (All): " + str(portfolio_calculate_roi(portfolio, open_positions=False, sold_positions=True)) + "\nPortfolio ROI (BTC) (Real): " + str(portfolio_calculate_roi(portfolio, open_positions=True, sold_positions=True, avoid_paper_trades=True)) + "\nPortfolio Available BTC Balance: " + str(portfolio['balance']['btc']) + "\n")
            arbitrage_pairs = binance_btc_check_arbitrages(pages=4) # 4 pages gets you 190/~203 BTC pairs, anything above 4 is very incremental
            assets = get_binance_assets(other_coins_symbol_to_id=dict(zip(list(portfolio['open']['symbol'].values) + list(portfolio['sold']['symbol'].values), list(portfolio['open'].index.values) + list(portfolio['sold']['coin'].values))), pages=4)
            if assets.loc['bitcoin', 'balance'] != portfolio['balance']['btc']: # and assets.loc['bitcoin', 'balance_locked'] == 0 # simple way to make sure bitcoin balance is correct every hour and to prevent orders
                portfolio['balance']['btc'] = assets.loc['bitcoin', 'balance']
                print("Portfolio Available BTC Balance (after correction): " + str(portfolio['balance']['btc']))
            print(str(assets) + "\nTotal Current Value: " + str(assets['current_value'].sum()) + "\nTotal Current Value (BTC): " + str(assets['current_value(btc)'].sum()) + "\nExecution time: " + str(time.time() - start_time) + "\n")
            print("Arbitrage pairs within +/- 50%: " + str(Counter({key: value for key,value in arbitrage_pairs.items() if abs(value) <= 0.5})) + "\n") # unrealistic that any arbitrage opportunities outside of 50% would exist, easy way to deal with coin scams, low volume traded coins, other logic issues
            binance_open_orders = _fetch_data(binance_client.get_open_orders, params={}, error_str=" - Binance open orders error on: " + str(datetime.now()), empty_data=[]) # for coin in assets[assets['balance_locked'] > 0].index: # if assets['balance_locked'].any(): - balance_locked not the way since if btc is locked don't know what you're buying just know that you're using btc to buy it
            if binance_open_orders: # maybe refactor and looked at assets balance_locked, see if full balance is gone, if any locked make partial
                print("Binance open orders: " + str(binance_open_orders))
                binance_pairs_with_price_current = {price['symbol']: float(price['price']) if price['price'] else 0 for price in _fetch_data(binance_client.get_all_tickers, params={}, error_str=" - Binance get all tickers error on: " + str(datetime.now()), empty_data=[])}
                for open_order in binance_open_orders:
                    symbol = open_order['symbol'].lower().split("btc")[0]
                    symbol_pair, original_quantity, executed_quantity, order_id, side, order_time = open_order['symbol'], float(open_order['origQty']), float(open_order['executedQty']), open_order['orderId'], open_order['side'], datetime.fromtimestamp(open_order['time']/1000) # open_order also has 'updateTime' 'status' 'isWorking' 'clientOrderId' might be useful # maybe refactor shouldn't be a float() issue but precautionary # maybe refactor name orderId to order_id
                    df_matching_open_options = portfolio['open'][(portfolio['open']['position'] == 'long') & (portfolio['open']['symbol'] == symbol) & (portfolio['open']['trade_notes'].isin(["Not filled", "Partially filled"]))] # assuming it's a long position have not implemented shorting: # also assuming side is a BUY, should always be a buy if in positions['open'] can add precautionary check but have to worry about BinanceClient changing their api for SIDE_BUY/SIDE_SELL # maybe add precautionary check for order_time withing +/- 10 minutes if worried about interfering with manual buys: & (portfolio['open']['buy_date'] <= order_time + timedelta(minutes=10)) & (portfolio['open']['buy_date'] >= order_time - timedelta(minutes=10))
                    if not df_matching_open_options.empty: # maybe refactor and add precautionary check - shouldn't have to check len() == 1 since symbol, like coin (index) should be unique in portfolio['open'] unless two different coins have the same symbol
                        coin = df_matching_open_options.index[0]
                        if abs((binance_pairs_with_price_current[symbol_pair] - portfolio['open'].loc[coin, 'buy_price(btc)']) / portfolio['open'].loc[coin, 'buy_price(btc)']) <= OPEN_ORDER_PRICE_DIFFERENCE: # *binance_pairs_with_price_current['BTCUSDT'] # refactor can make that a parameter also not sure if necessary, can be sl/2
                            resp = _fetch_data(binance_client.cancel_order, params={'symbol': symbol_pair, 'orderId': order_id}, error_str=" - Binance cancel order error for symbol_pair: " + symbol_pair + " and orderId: " + str(order_id) + " on: " + str(datetime.now()), empty_data=[]) # maybe refactor unnecessary if order['fills']
                            if resp['status'] == 'CANCELED': # cancelled is more British English, canceled is more American English, Binance uses canceled, grammarly.com/blog/canceled-vs-cancelled
                                original_price_in_btc = portfolio['open'].loc[coin, 'buy_price(btc)']
                                balance = original_quantity - executed_quantity # assuming (and should be based on code), that original_quantity is same as portfolio['open'].loc[coin, 'balance'], no need for precautionary check IMO
                                quantity, price_in_btc, binance_coin_btc_order, binance_coin_btc_open_orders, trade_notes = binance_trade_coin_btc(symbol_pair=symbol_pair, side=side, quantity=balance, open_time=1, paper_trading=paper_trading, other_notes="Retrying open order for coin " + coin + " bought on " + str(order_time))
                                new_price_in_btc = (price_in_btc*quantity + original_price_in_btc*executed_quantity) / original_quantity
                                portfolio['open'].loc[coin, ['buy_date', 'buy_price(btc)', 'trade_notes', 'other_notes']] = [datetime.now(), new_price_in_btc, trade_notes, "Retried order"] # update buy_date in case new order is incomplete # not tracking how many times retrying order too much logic for unlikely situation (unlikely that will need to retry more than once if adjust price after an hour)
                    df_matching_sold_options = portfolio['sold'][(portfolio['sold']['position'] == 'long') & (portfolio['sold']['symbol'] == symbol) & (portfolio['sold']['trade_notes'].isin(["Not filled", "Partially filled"])) & (portfolio['sold']['sell_date'] <= order_time + timedelta(minutes=10)) & (portfolio['sold']['sell_date'] >= order_time - timedelta(minutes=10))] # assuming it's a long position have not implemented shorting # +/- 10 minutes since order time most likely (micro) seconds off time recorded - might be issue if have an order cancelled and re-ordered associated with original order but now different order_time # also assuming side is a SELL, should always be a sell if in positions['sold'] can add precautionary check but have to worry about BinanceClient changing their api for SIDE_BUY/SIDE_SELL
                    if not df_matching_sold_options.empty: # maybe refactor and add precautionary check - shouldn't have to check len() == 1 since symbol, trade_notes and order_time time frame (+/- 10 minutes)
                        idx = df_matching_sold_options.index[0]
                        if abs((binance_pairs_with_price_current[symbol_pair] - portfolio['sold'].loc[idx, 'sell_price(btc)']) / portfolio['sold'].loc[idx, 'sell_price(btc)']) <= OPEN_ORDER_PRICE_DIFFERENCE: # *binance_pairs_with_price_current['BTCUSDT'] # refactor can make that a parameter also not sure if necessary, can be sl/2
                            resp = _fetch_data(binance_client.cancel_order, params={'symbol': symbol_pair, 'orderId': order_id}, error_str=" - Binance cancel order error for symbol_pair: " + symbol_pair + " and orderId: " + str(order_id) + " on: " + str(datetime.now()), empty_data=[]) # maybe refactor unnecessary if order['fills']
                            if resp['status'] == 'CANCELED': # cancelled is more British English, canceled is more American English, Binance uses canceled
                                original_price_in_btc = portfolio['open'].loc[idx, 'sell_price(btc)']
                                balance = original_quantity - executed_quantity
                                quantity, price_in_btc, binance_coin_btc_order, binance_coin_btc_open_orders, trade_notes = binance_trade_coin_btc(symbol_pair=symbol_pair, side=side, quantity=balance, open_time=1, paper_trading=paper_trading, other_notes="Retrying open order for coin " + portfolio['sold'].loc[idx, 'coin'] + " sold on " + str(order_time))
                                new_price_in_btc = (price_in_btc*quantity + original_price_in_btc*executed_quantity) / original_quantity
                                portfolio['sold'].loc[idx, ['sell_date', 'sell_price(btc)', 'trade_notes', 'other_notes']] = [datetime.now(), new_price_in_btc, trade_notes, "Retried order"] # update sell_date in case new order is incomplete
                binance_open_orders = _fetch_data(binance_client.get_open_orders, params={}, error_str=" - Binance open orders error on: " + str(datetime.now()), empty_data=[])
                print("Binance open orders (after): " + str(binance_open_orders) + "\nExecution time: " + str(time.time() - start_time) + "\n")
            else: # update orders completed but listed as incomplete incorrectly by binance_trade_coin_btc
                for coin in portfolio['open'].index:
                    if (portfolio['open'].loc[coin, 'position'] == "long") and portfolio['open'].loc[coin, 'trade_notes'] in ["Not filled", "Partially filled"]:
                        portfolio['open'].loc[coin, 'trade_notes'] = "Filled"
                for idx in portfolio['sold'].index:
                    if (portfolio['sold'].loc[idx, 'position'] == "long") and portfolio['sold'].loc[idx, 'trade_notes'] in ["Not filled", "Partially filled"]:
                        portfolio['sold'].loc[idx, 'trade_notes'] = "Filled"
            # can also add updates for if assets go above or below a certain value
        save_portfolio_backup(portfolio) # save every 4 minutes for now, in case something happens
        time.sleep(240.0 - ((time.time() - start_time) % 240.0))

import os # os.getcwd() # os.chdir()

def save_portfolio_backup(portfolio): # can add logic for different types of portfolio i.e. rr with different kinds of parameters i.e. different up and down moves
    print("portfolio saved")
    portfolio_constants = "_".join([str(value) if key != 'up_down_move' else str(value) + "_" + str(value) for key,value in list(portfolio['constants'].items())]) if portfolio['constants']['type'] == 'rr' else "_".join([str(value) for key,value in list(portfolio['constants'].items())])
    if (datetime.now().hour == 0) and (datetime.now().minute < 4): # maybe refactor and check if file exists to avoid getting error: if os.path.exists("demofile.txt"):, should only be an error if start script between 12am and 12:04am
        os.remove('data/crypto/saved_portfolio_backups/' + 'portfolio_' + portfolio_constants + '_to_' + (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d') + '.pckl')
    f = open('data/crypto/saved_portfolio_backups/' + 'portfolio_' + portfolio_constants + '_to_' + datetime.now().strftime('%Y-%m-%d') + '.pckl', 'wb') # 2020_06_02, format is '%Y-%m-%d'
    pickle.dump(portfolio, f)
    f.close()
    return portfolio

def get_saved_portfolio_backup(portfolio_name): # portfolio name is portfolio_ + constants, like: portfolio_50_20_-0.3_0.5_-0.2_0.1_0.01_True_False_False # date is a string in format '%Y-%m-%d'
    try:
        f = open('data/crypto/saved_portfolio_backups/' + portfolio_name + '.pckl', 'rb')
        portfolio = pickle.load(f)
        f.close()
    except Exception as e:
        print(str(e) + " - No saved portfolio backup with name: " + portfolio_name)
        # refactor better to have 'exchange', 'exchange_24h_vol', 'total_24h_vol', 'binance_btc_24h_vol(btc)' column works for now, maybe add column for 'price/volume_trend' (to eliminate coin pumps/pumps and dumps), social metrics trends (reddit subscribers, alexa rank, ...) # for column dtypes: both didn't work - dtype=[np.datetime64, np.float64, np.datetime64, np.float64]) # dtype=np.dtype([('datetime64','float64','datetime64','float6')])) # no need for portfolio['open_orders'] since tracking assets which has balance_locked (in order) # maybe refactor 'open' index to allow for multiple 'long' positions for the same coin but have to worry about portfolio['open'].loc[idx, ...], maybe refactor and change 'balance' to 'quantity' since portfolio not holding (meant to hold) onto assets for long term and each asset is not being refilled/sold incompletely (at least not intentionally)
        portfolio = {
            'constants': {'type': 'rr', 'up_down_move': 50, 'days': 20, 'sl': -0.3, 'tsl_a': 0.5, 'tsl_p': -0.2, 'btc_invest': 0.1, 'btc_invest_min': 0.01, 'buy_date_gtrends_15d': True, 'end_day_open_positions_gtrends_15d': False, 'end_day_open_positions_binance_btc_24h_vol': False, 'start_day': '2020-02-24'}, # assuming always enforcing btc_invest_min
            'balance': {'btc': 1.0},
            'open': pd.DataFrame(columns=['symbol', 'position', 'buy_date', 'buy_price(btc)', 'balance', 'current_date', 'current_price(btc)', 'current_roi(btc)', 'binance_btc_24h_vol(btc)', 'gtrends_15d', 'rank_rise_d', 'tsl_armed', 'tsl_max_price(btc)', 'trade_notes', 'other_notes']).astype({'symbol': 'object', 'position': 'object', 'buy_date': 'datetime64', 'buy_price(btc)': 'float64', 'balance': 'float64', 'current_date': 'datetime64', 'current_price(btc)': 'float64', 'current_roi(btc)': 'float64', 'binance_btc_24h_vol(btc)': 'float64', 'gtrends_15d': 'float64', 'rank_rise_d': 'float64', 'tsl_armed': 'bool', 'tsl_max_price(btc)': 'float64', 'trade_notes': 'object', 'other_notes': 'object'}),
            'sold': pd.DataFrame(columns=['coin', 'symbol', 'position', 'buy_date', 'buy_price(btc)', 'balance', 'sell_date', 'sell_price(btc)', 'roi(btc)', 'binance_btc_24h_vol(btc)', 'gtrends_15d', 'rank_rise_d', 'tsl_max_price(btc)', 'trade_notes', 'other_notes']).astype({'coin': 'object', 'symbol': 'object', 'position': 'object', 'buy_date': 'datetime64', 'buy_price(btc)': 'float64', 'balance': 'float64', 'sell_date': 'datetime64', 'sell_price(btc)': 'float64', 'roi(btc)': 'float64', 'binance_btc_24h_vol(btc)': 'float64', 'gtrends_15d': 'float64', 'rank_rise_d': 'float64', 'tsl_max_price(btc)': 'float64', 'trade_notes': 'object', 'other_notes': 'object'})
        }
    return portfolio

portfolio = get_saved_portfolio_backup('portfolio_rr_50_50_20_-0.3_0.5_-0.2_0.1_0.01_True_False_False_2020-02-24_to_' + datetime.now().strftime('%Y-%m-%d'))

# BE CAREFUL
portfolio_trading(paper_trading=True, portfolio=portfolio) # portfolio_rr_50_50_20_sl_0_3_tsl_a_0_5_p_0_2
