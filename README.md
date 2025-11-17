# quant-trading

A Python module for a suite of quant-trading opportunities. Run the python script (in a python file) as shown below (in a quant-trading root directory) in a virtual environment (make sure it's running on Python 3.12+ to be able to run most up-to-date AI) on a spare computer running 24/7 or a hosted service like Heroku (scheduler for executing market checks, data downloads, algorithm runs) and AWS (for storing data) for automated trading.

For easy implementation create a virtual Python environment with up-to-date Python (3.12+) and appropriate modules for data download and analysis and brokerage trading via pip. Then download modules stocks.py and crypto.py (in this env/lib/python3.12/site-packages/ directory) and place them in your env/lib/python<<python_version>>/site-packages/ directory alongside your personal.py file for easy import and make sure function calls work with your modules (use modules I use for easy implementation).

Don't run active terminals on different computers from same directory (causes errors like when ran function crypto.get_coin_data resulted in losing locally - in env - installed pycoingecko). Update modules every so often. Don't interrupt / restart script when power / wifi is out since some clients (like BinanceClient()) will cause error which is necessary to run upon initiation. Scripts are meant to run even without wifi (will just be sleeping / checking for data - depending on time of day - and returning logs that indicate API errors). Scripts should be restarted at minimum every few months to ensure up-to-date software and clear cache / working memory and every year to ensure current holidays are taken into account.

Backtest algorithms with different parameters (parameters in this directory are chosen based on quant-trading readings from Medium regarding most common practices) over saved data to see which algorithm and parameter combination work best for the period of time you backtest over which you deem to reflect current market conditions.

Set up your automated environment to download stocks data every night with an API data brokerage of your choosing (this module is currently set up for Financial Modeling Prep $20/mo for stocks, CoinMarketCap $0/mo for crypto). Then run the data through your current algorithm after data is downloaded, and then execute trades via an API trading brokerage of your choosing (this module is currently using Alpaca for stocks, Kucoin - no real trading after new regulations in 2024-09 - for crypto) after the algorithm picks stocks to buy / sell. Stock trading is denominated is USD base, crypto trading is denominated in USDT base but traded relative to BTC price (ie VET loses 15% relative to BTC - VET-BTC price - then Stop-Loss triggers a VET sell on that portfolio in VET-USDT). Crypto is traded relative to BTC since BTC is considered a benchmark for crypto vs. alt-coins and BTC was the coin you wanted to grow (vs. USDT / other stablecoins) especially if you wanted to stay long-term in crypto and when most major exchanges had majority listings in -BTC until regulations on major exchanges came into effect (trading in specific countries).

## Running the Python script in virtual environment (quant-trading directory)

quant-trading directory is in icloud so I can access / change code from other computers without having to push / pull git. I also access my spare computer which runs (like a server) 24/7 via Chrome Remote Desktop (highly recommend if using a spare computer to access that computer from another labtop to deal with issues like restarting if python scripts all of a sudden freeze or run into unforeseen errors - happens more often than you think - or to get rid of working memory / cache which takes over the storage of that computer).

This script (below) is run after virtual environment is properly set up, personal module is set up (with all of your base urls, keys, secret identities and auth tokens variables for your APIs) and located in env/lib/python<<python_version>>/site-packages/personal.py (like where stocks.py and crypto.py are located so personal can be imported and variables called like personal.<<variable_name>>).

Stocks:
(env) ~/icloud/quant-trading (master) $ python programs/stocks/stocks_alpaca_<<your_username>>.py

Crypto:
(env) ~/icloud/quant-trading (master) $ python programs/crypto/crypto_kucoin_<<your_user_name>>.py

## Python virtual environment (quant-trading directory requirements.txt)

Your virtual environment should have installed and up-to-date modules necessary for collecting and analyzing data and executing trades (for both stocks and crypto trading stored in a requirements.txt file in your quant-trading root directory) like my requirements.txt (check my requirements.txt file as an example) file at minimum (other modules like openai and google gemini pro should be downloaded according to their python github pages) downloaded via pip.

## Python script for Stocks (programs/stocks/stocks_alpaca_<<your_username>>.py)

You should have multiple accounts with the brokerage you trade with so you can run multiple real trading (paper_trading=False) scripts, in this case account 1: <<your_username>> and account 2: <<your_other_username>>, both with Alpaca. You can paper_trade multiple scripts off one account if you set stocks.portfolio_trading(portfolio=portfolio, paper_trading_on_used_account=True, ...) which doesn't paper_trade on Alpaca / Kucoin itself just in your virtual environment. Twilio is only necessary if you want text notifications to your phone (you'll need to set up personal.twilio_phone_to and personal.twilio_phone_from numbers with Twilio).

`import stocks # always run from quant-trading root directory because stocks includes functions which saves / retrieves data in paths off of this root directory

import os
import alpaca_trade_api as tradeapi
import personal

os.environ["APCA_API_BASE_URL"] = personal.alpaca_base_url_<<your_username>>
stocks.alpaca_api = tradeapi.REST(personal.alpaca_key_<<your_username>>, personal.alpaca_secret_<<your_username>>) # , api_version='v3'

stocks.FMP_API_KEY = personal.fmp_api_key

from twilio.rest import Client as TwilioClient

stocks.twilio_client = TwilioClient(personal.twilio_account_sid, personal.twilio_auth_token)
stocks.twilio_phone_to, stocks.twilio_phone_from = personal.twilio_phone_to, personal.twilio_phone_from

from datetime import datetime # , timedelta # only import timedelta when need to inspect portfolio or data or run stocks.run_portfolio() manually

# check that portfolio belongs to the correct account (<<your_other_username>> vs. <<your_username>>)
stocks.portfolio_account = "alpaca_<<your_username>>"

# make sure to check/change 'start_day', base_pair' and associated 'usdt' or 'btc' references of portfolio['constants'] etc. before running, portfolio name reflects algorithm type (rr = relative rank and parameters for that algorithm)
portfolio = stocks.get_saved_portfolio_backup("portfolio_rr_50_-50_20_-0.2_0.2_-0.05_2000_100_True_False_False_{'usd': 10000}_2024-12-01_to_" + datetime.now().strftime('%Y-%m-%d'))

# BE CAREFUL, paper_trading: update to current value (to reflect current trading, especially when need to restart the script ensure paper_trading reflects last paper_trading value), portfolio_usd_value_negative_change_from_max_limit (variable not listed since keep at default that reflects a Stop-Loss on your entire portfolio, default is -0.3, meaning that if your portfolio loses 30% relative to it's max value it will automatically panic sell negative roi assets and set paper_trading=True and continue paper_trading=True until current assets >= portfolio_max_value*(1-0.3) and current_roi >= 0.045),  portfolio_current_roi_restart: a variable that if paper_trading=True (and 'engaged': True) reflects when the python script changes to paper_trading=False (when current_roi >= 0.045 in this example), download_and_save_tickers_data: have to ensure that one portfolio_trading instance is saving data (don't want all of your scripts to be saving data, just one and then the other scripts wait for the data to be saved and execute their algorithm runs on that saved data)
stocks.portfolio_trading(portfolio=portfolio, paper_trading=False, portfolio_current_roi_restart={'engaged': False, 'limit': 0.045}, download_and_save_tickers_data=True)`

## Another Python script for Stocks (with AI trading, programs/stocks/stocks_tngaia_alpaca_<<your_other_username>>.py)

tngaia is an acronym for what kind of algorithm the trading script incorporates, in this case Top-N Gainers AI Analysis (where n is a number set in parameters reflecting top-n gainers from the day to be analyzed by AI - OpenAI or Gemini Pro, both options are available in stocks module - for buy / sell opportunities executed at start of next trading day).

`import stocks # always run from quant-trading root directory (/Library/Mobile Documents/com~apple~CloudDocs/quant-trading) because stocks includes functions which saves / retrieves data in paths off of this root directory

import os
import alpaca_trade_api as tradeapi
import personal

os.environ["APCA_API_BASE_URL"] = personal.alpaca_base_url_<<your_other_username>>
stocks.alpaca_api = tradeapi.REST(personal.alpaca_key_<<your_other_username>>, personal.alpaca_secret_<<your_other_username>>)

stocks.FMP_API_KEY = personal.fmp_api_key

from openai import OpenAI
from langchain.chat_models import ChatOpenAI

stocks.openai_client = OpenAI(organization=personal.openai_organization, api_key=personal.openai_secret_api_key)
stocks.chat_model = ChatOpenAI(temperature=0, openai_api_key=personal.openai_secret_api_key)

GOOGLE_API_KEY = personal.google_gemini_pro_api_key

import google.generativeai as genai

genai.configure(api_key=GOOGLE_API_KEY)
stocks.google_gemini_pro_model = genai.GenerativeModel('gemini-pro')

from twilio.rest import Client as TwilioClient

stocks.twilio_client = TwilioClient(personal.twilio_account_sid, personal.twilio_auth_token)
stocks.twilio_phone_to, stocks.twilio_phone_from = personal.twilio_phone_to, personal.twilio_phone_from

from datetime import datetime # , timedelta # only import timedelta when need to inspect portfolio or data or run stocks.run_portfolio() manually

# check that portfolio belongs to the correct account (<<your_other_username>> vs. <<your_username>>)
stocks.portfolio_account = "alpaca_<<your_other_username>>"

# make sure to change 'start_day' of portfolio['constants'] before running
portfolio = stocks.get_saved_portfolio_backup("portfolio_tngaia_[8, 4]_1_-0.3_0.5_-0.2_1000_100_True_False_False_{'usd': 10000}_2024-03-18_to_" + datetime.now().strftime('%Y-%m-%d'))

# BE CAREFUL, update to current paper_trading, portfolio_usd_value_negative_change_from_max_limit, portfolio_current_roi_restart, have to ensure that another portfolio_trading instance is saving data (download_and_save_tickers_data)
stocks.portfolio_trading(portfolio=portfolio, paper_trading=True, paper_trading_on_used_account=True, portfolio_usd_value_negative_change_from_max_limit=-0.69, portfolio_current_roi_restart={'engaged': True, 'limit': 0.075}) # portfolio_rr_50_50_20_sl_0_3_tsl_a_0_5_p_0_2 # , buying_disabled=False`

## Python script for Crypto (programs/crypto/crypto_kucoin_<<your_username>>)

`import crypto # always run from quant-trading root directory (/Library/Mobile Documents/com~apple~CloudDocs/quant-trading) because crypto includes functions which saves / retrieves data in paths off of this root directory

import personal
# from binance.client import Client as BinanceClient # github: binance-exchange/python-binance # here and below: binance.exceptions.BinanceAPIException: APIError(code=0): Service unavailable from a restricted location according to 'b. Eligibility' in https://www.binance.com/en/terms. Please contact customer service if you believe you received this message in error.
from kucoin.client import Client as KucoinClient

# crypto.binance_client = BinanceClient(personal.binance_key_<<your_username>>, personal.binance_secret_<<your_username>>)
crypto.kucoin_client = KucoinClient(personal.kucoin_key_<<your_username>>, personal.kucoin_secret_<<your_username>>, personal.kucoin_api_passphrase_<<your_username>>)

from twilio.rest import Client as TwilioClient

crypto.twilio_client = TwilioClient(personal.twilio_account_sid, personal.twilio_auth_token)
crypto.twilio_phone_to, crypto.twilio_phone_from = personal.twilio_phone_to, personal.twilio_phone_from

from datetime import datetime # , timedelta # only import timedelta when need to inspect portfolio or data or run crypto.run_portfolio() manually

# make sure to change start_day of portfolio['constants'] before running
portfolio = crypto.get_saved_portfolio_backup("portfolio_usdt_rr_10_-10_20_-0.3_0.5_-0.2_1000_100_1000_1000_True_False_False_{'usdt': 10000}_2023-03-12_to_" + datetime.now().strftime('%Y-%m-%d'))

# BE CAREFUL, update to current paper_trading, portfolio_btc_value_negative_change_from_max_limit, portfolio_current_roi_restart
crypto.portfolio_trading(portfolio=portfolio, exchange="kucoin", paper_trading=True, portfolio_usdt_value_negative_change_from_max_limit=-0.05, portfolio_current_roi_restart={'engaged': True, 'limit': 0.90}, download_and_save_coins_data=True)`

## Checking asset value in virtual Python environment (calling Python and then entering virtual Python environment as opposed to running a script with python <<directory_path/file_name.py>>) after manually line-by-line importing necessary modules listed in appropriate script like Python script for Stocks programs/stocks/stocks_alpaca_<<your_username>>.py to properly set up that Python environment

Stocks:
`account, alpaca_open_orders = stocks._fetch_data(stocks.alpaca_api.get_account, params={}, error_str=" - No account from Alpaca on: " + str(datetime.now()), empty_data = {}), stocks._fetch_data(stocks.alpaca_api.list_orders, params={'status': 'open', 'nested': True}, error_str=" - Alpaca open orders error on: " + str(datetime.now()), empty_data=[])
assets = stocks.get_alpaca_assets(alpaca_account=account, alpaca_open_orders=alpaca_open_orders)
print(str(assets) + "\nTotal Current Value: " + str(assets['current_value'].sum()) + "\nAccount Equity: " + str(account.equity) + "\nAccount Buying Power: " + str(account.buying_power))`

Crypto:
`assets = crypto.get_kucoin_assets()
print(str(assets) + "\nTotal Current Value: " + str(assets['current_value'].sum()) + "\nTotal Current Value (BTC): " + str(assets['current_value(btc)'].sum()))`

## Backtesting in virtual Python environment (like stated above)

Stocks:
`portfolios = {} #  # rr,,tr # long only # maybe refactor pccepsf to industry check  like ic
type = 'rr' # 'tilupccu'
up_down_moves = [10,20,50,100] # [5] # [1,0],[1,-1] #  
bt_days = [15,20] # , # , 1,2,5,10 # , # 90,120,150,180,210,240,270,300,330,365
sl_tsl_a_ps = [[-0.15,0.05,-0.0125],[-0.2,0.2,-0.05],[-0.3,0.5,-0.2]] # [-1,10,-5] #  all performed worse than [-0.15, 0.05, -0.0125]: [-0.15, 0.05, -0.02], [-0.15, 0.07, -0.0175], [-0.15, 0.10, -0.025], [-0.10, 0.05, -0.0125]
usd_invests = [1000,2000] # 500
balances_usd = [10000]

tickers_with_stock_splits = stocks.tickers_with_stock_splits_in_period_fmp(start_day=start_day)
# since FMP makes duplicates for some reason
skip_idxs = []
for idx in tickers_with_stock_splits.index:
    if idx not in skip_idxs:
        symbol, date = tickers_with_stock_splits.loc[idx, ['symbol', 'date']]
        matching_rows = tickers_with_stock_splits[(tickers_with_stock_splits['symbol'] == symbol) & (tickers_with_stock_splits['date'] == date)]
        if len(matching_rows) > 1:
            print(symbol + ": " + str(date) + str(matching_rows))
            repeated_idx = matching_rows.index[-1]
            tickers_with_stock_splits = tickers_with_stock_splits.drop(repeated_idx)
            skip_idxs.append(repeated_idx)

# make sure to change 'type', portfolios_type, 'start_day' of portfolio['constants'], check tickers_with_stock_splits before running
for up_down_move in up_down_moves:
    for days in bt_days:
        for sl_tsl_a_p in sl_tsl_a_ps: # for sl in sls:
            sl, tsl_a, tsl_p = sl_tsl_a_p[0], sl_tsl_a_p[1], sl_tsl_a_p[2] # sl, tsl_a, tsl_p = -1, 10, -2
            for usd_invest in usd_invests:
                for balance_usd in balances_usd:
                    # maybe add column for 'rank_rise' (within S&P 500), 'rank/price/volume_trend' or 'buy_date_fmp_24h_vol', for column dtypes: both didn't work - dtype=[np.datetime64, np.float64, np.datetime64, np.float64]) # dtype=np.dtype([('datetime64','float64','datetime64','float6
                    portfolio = { # 'tr', 'zr' and remove up_down_move, 'tr' have to start on '2020-05-08', first day with tradingview ratings # 'up_down_move': 100, 'days': 15, 'sl': -0.15, 'tsl_a': 0.05, 'tsl_p': -0.0125, 'usd_invest': 1000,
                        'constants': {'type': type, 'up_down_move': up_down_move, 'days': days, 'sl': sl, 'tsl_a': tsl_a, 'tsl_p': tsl_p, 'usd_invest': usd_invest, 'usd_invest_min': 100, 'buy_date_gtrends_15d': False, 'end_day_open_positions_gtrends_15d': False, 'end_day_open_positions_fmp_24h_vol': False, 'start_balance': {'usd': balance_usd}, 'start_day': '2024-12-01'}, # assuming always enforcing usd_invest_min
                        'balance': {'usd': balance_usd},
                        'max_value': {'usd': float("NaN")},
                        'open': pd.DataFrame(columns=['position', 'buy_date', 'buy_price', 'balance', 'current_date', 'current_price', 'current_roi', 'fmp_24h_vol', 'gtrends_15d', 'rank_rise_d', 'tsl_armed', 'tsl_max_price', 'trade_notes', 'other_notes']).astype({'position': 'object', 'buy_date': 'datetime64[ns]', 'buy_price': 'float64', 'balance': 'float64', 'current_date': 'datetime64[ns]', 'current_price': 'float64', 'current_roi': 'float64', 'fmp_24h_vol': 'float64', 'gtrends_15d': 'float64', 'rank_rise_d': 'float64', 'tsl_armed': 'bool', 'tsl_max_price': 'float64', 'trade_notes': 'object', 'other_notes': 'object'}),
                        'sold': pd.DataFrame(columns=['ticker', 'position', 'buy_date', 'buy_price', 'balance', 'sell_date', 'sell_price', 'roi', 'fmp_24h_vol', 'gtrends_15d', 'rank_rise_d', 'tsl_max_price', 'trade_notes', 'other_notes']).astype({'ticker': 'object', 'position': 'object', 'buy_date': 'datetime64[ns]', 'buy_price': 'float64', 'balance': 'float64', 'sell_date': 'datetime64[ns]', 'sell_price': 'float64', 'roi': 'float64', 'fmp_24h_vol': 'float64', 'gtrends_15d': 'float64', 'rank_rise_d': 'float64', 'tsl_max_price': 'float64', 'trade_notes': 'object', 'other_notes': 'object'})
                    }
                    portfolio_name = str(up_down_move) + ("_" + str(-up_down_move) if portfolio['constants']['type'] not in ['tilupccu', 'oair', 'senate_trading'] else "") + "_" + str(days) + "_" + str(sl_tsl_a_p) + "_" + str(usd_invest) + "_" + str(balance_usd) # + "_sl_"  + "_tsl_a_"  + "_p_"  + "_usd_invest_" # maybe refactor zr is not really an equivalent down_move more of a sell if rating turns toward sell
                    print(portfolio_name)
                    if portfolio_name in portfolios:
                        continue
                    portfolios[portfolio_name] = stocks.run_portfolio(portfolio=portfolio, start_day=datetime.strptime('2024_12_01 13:00:00', '%Y_%m_%d %H:%M:%S'), end_day=datetime.strptime('2025_02_28 13:00:00', '%Y_%m_%d %H:%M:%S'), paper_trading=True, back_testing=True, add_pauses_to_avoid_unsolved_error={'engaged': True, 'time': 120, 'days': 60}, tickers_with_stock_splits=tickers_with_stock_splits) # senate_timestamps_and_tickers_inflows_and_outflows=senate_timestamps_and_tickers_inflows_and_outflows)

# List ROIs:
for portfolio_name, portfolio in portfolios.items():
    portfolio_usd_value = portfolio['balance']['usd']
    for ticker in portfolio['open'].index:
        portfolio_usd_value += portfolio['open'].loc[ticker, 'current_price']*portfolio['open'].loc[ticker, 'balance']
    portfolio_usd_value_growth = (portfolio_usd_value - portfolio['constants']['start_balance']['usd']) / portfolio['constants']['start_balance']['usd'] # float(portfolio_name.split("_")[-2])
    print(portfolio_name + ", USD Value: " + str(portfolio_usd_value) + ", USD Value Growth: " + str(portfolio_usd_value_growth))

# Check outlier individual portfolios ('50_-50_15_[-0.2, 0.2, -0.05]_2000_10000' is an example portfolio)
portfolios['50_-50_15_[-0.2, 0.2, -0.05]_2000_10000']['sold'].sort_values('roi', inplace=False, ascending=False)[['ticker', 'buy_date', 'buy_price', 'balance', 'rank_rise_d', 'sell_date', 'sell_price', 'roi', 'other_notes']]
portfolios['50_-50_15_[-0.2, 0.2, -0.05]_2000_10000']['open'].sort_values('current_roi', inplace=False, ascending=False)[['buy_date', 'buy_price', 'balance', 'rank_rise_d', 'current_date', 'current_price', 'current_roi', 'other_notes']]

# if want to update a saved portfolios dict to current dates and not iterate over past values (make sure to check dates):
import copy
portfolios_updated = {}
for portfolio_name, portfolio in portfolios.items():
    print(portfolio_name)
    new_portfolio = copy.deepcopy(portfolio)
    if portfolio_name in portfolios_updated:
        continue
    portfolios_updated[portfolio_name] = stocks.run_portfolio(portfolio=new_portfolio, start_day=datetime.strptime('2025_01_18 13:00:00', '%Y_%m_%d %H:%M:%S'), end_day=datetime.strptime('2025_03_06 13:00:00', '%Y_%m_%d %H:%M:%S'), paper_trading=True, back_testing=True, add_pauses_to_avoid_unsolved_error={'engaged': True, 'time': 420, 'days': 20}, tickers_with_stock_splits=tickers_with_stock_splits) # ,

# Saving portfolio values to data (make sure that dates reflect start and end date):
f = open('data/stocks/saved_portfolio_backups/back_testing/' + 'portfolios_' + type + '_' + ','.join(map(str,up_down_moves)) + '_' + ','.join(map(str,bt_days)) + '_' + ','.join(map(str,sl_tsl_a_ps)) + '_' +  ','.join(map(str,usd_invests)) + '_' + ','.join(map(str,balances_usd)) + '_2024-12-01_to_2025-02-28' + '.pckl', 'wb') #    'rb'
pd.to_pickle(portfolios, f) # portfolios = pd.read_pickle(f)
f.close()`

Crypto:
`portfolios = {} # long only
up_down_moves = [50,100] # 10,20,40,
bt_days = [5,10,15,20] #  ,
sl_tsl_a_ps = [[-0.15,0.05,-0.0125],[-0.2,0.2,-0.05],[-0.3,0.5,-0.2]] # [-1,10,-5] # ,
usdt_invests = [1000,2000] # btc_invests = [0.1,0.2]
balances_usdt = [5000] # balances_btc = [1]
coins_to_analyzes = [1000] # 250,
rank_rise_d_buy_limits = [1000] # 200,

# make sure to change start_day of portfolio['constants'] before running
for up_down_move in up_down_moves:
    for days in bt_days:
        for sl_tsl_a_p in sl_tsl_a_ps:
            sl, tsl_a, tsl_p = sl_tsl_a_p[0], sl_tsl_a_p[1], sl_tsl_a_p[2]
            for usdt_invest in usdt_invests:
                for balance_usdt in balances_usdt:
                    for coins_to_analyze in coins_to_analyzes:
                        for rank_rise_d_buy_limit in rank_rise_d_buy_limits:
                            portfolio_name = str(up_down_move) + "_" + str(-up_down_move) + "_" + str(days) + "_" + str(sl_tsl_a_p) + "_" + str(usdt_invest) + "_" + str(balance_usdt) + "_" + str(coins_to_analyze) + "_" + str(rank_rise_d_buy_limit) # balance_btc not at end since makes sense if it's next to btc_invest and also name is chronological (names are in order in which features were added)
                            print(portfolio_name)
                            if portfolio_name in portfolios:
                                continue
                            portfolio = { # 100_100_15_[-0.3, 0.5, -0.2]_0.2_1_1000_1000
                                'constants': {'base_pair': 'usdt', 'type': 'rr', 'up_down_move': up_down_move, 'days': days, 'sl': sl, 'tsl_a': tsl_a, 'tsl_p': tsl_p, 'usdt_invest': usdt_invest, 'usdt_invest_min': 100, 'coins_to_analyze': coins_to_analyze, 'rank_rise_d_buy_limit': rank_rise_d_buy_limit, 'buy_date_gtrends_15d': False, 'end_day_open_positions_gtrends_15d': False, 'end_day_open_positions_kucoin_usdt_24h_vol': False, 'start_balance': {'usdt': balance_usdt}, 'start_day': '2024-05-01'}, # assuming always enforcing btc_invest_min # maybe refactor move btc_invest and btc_invest_min out of constants since could be changing more frequently # maybe refactor coins_to_analyze to num_coins_to_analyze (but then have to worry about it being top num coins etc easier like this coins_to_analyze implicitly implies top x coins by market cap) # 'end_day_open_positions_binance_btc_24h_vol' # base_pair is for trading (balance, max_value, usdt_invest, usdt_invest_min, start_balance, back_testing), roi is in btc, keep track of both prices (usdt, btc) for roi calculation and optics
                                'balance': {'usdt': balance_usdt}, # 'btc': 1.0 # {'btc': 1.0, 'max': {'btc': 1.0}}
                                'max_value': {'usdt': float("NaN")}, # 1.07 is btc balance in Binance on 9/14/2020
                                'open': pd.DataFrame(columns=['symbol', 'position', 'buy_date', 'buy_price', 'buy_price(btc)', 'balance', 'current_date', 'current_price(btc)', 'current_roi(btc)', 'kucoin_usdt_24h_vol', 'gtrends_15d', 'rank_rise_d', 'tsl_armed', 'tsl_max_price(btc)', 'trade_notes', 'other_notes']).astype({'symbol': 'object', 'position': 'object', 'buy_date': 'datetime64[ns]', 'buy_price': 'float64', 'buy_price(btc)': 'float64', 'balance': 'float64', 'current_date': 'datetime64[ns]', 'current_price(btc)': 'float64', 'current_roi(btc)': 'float64', 'kucoin_usdt_24h_vol': 'float64', 'gtrends_15d': 'float64', 'rank_rise_d': 'float64', 'tsl_armed': 'bool', 'tsl_max_price(btc)': 'float64', 'trade_notes': 'object', 'other_notes': 'object'}), # 'binance_btc_24h_vol(btc)'
                                'sold': pd.DataFrame(columns=['coin', 'symbol', 'position', 'buy_date', 'buy_price', 'buy_price(btc)', 'balance', 'sell_date', 'sell_price', 'sell_price(btc)', 'roi(btc)', 'kucoin_usdt_24h_vol', 'gtrends_15d', 'rank_rise_d', 'tsl_max_price(btc)', 'trade_notes', 'other_notes']).astype({'coin': 'object', 'symbol': 'object', 'position': 'object', 'buy_date': 'datetime64[ns]', 'buy_price': 'float64', 'buy_price(btc)': 'float64', 'balance': 'float64', 'sell_date': 'datetime64[ns]', 'sell_price': 'float64', 'sell_price(btc)': 'float64', 'roi(btc)': 'float64', 'kucoin_usdt_24h_vol': 'float64', 'gtrends_15d': 'float64', 'rank_rise_d': 'float64', 'tsl_max_price(btc)': 'float64', 'trade_notes': 'object', 'other_notes': 'object'}) # 'binance_btc_24h_vol(btc)'
                            }
                            portfolios[portfolio_name] = crypto.run_portfolio_rr(portfolio=portfolio, start_day=datetime.strptime('2024_06_15 17:00:00', '%Y_%m_%d %H:%M:%S'), end_day=datetime.strptime('2024_08_06 17:00:00', '%Y_%m_%d %H:%M:%S'), rr_sell=True, paper_trading=True, back_testing=True)

# List ROIs:
kucoin_pairs_with_price_and_vol_current = crypto._fetch_data(crypto.get_kucoin_pairs, params={}, error_str=" - Kucoin get tickers error on: " + str(datetime.now()), empty_data={})
for portfolio_name, portfolio in portfolios_updated_2.items():
    portfolio_usdt_value = portfolio['balance']['usdt']
    for coin in portfolio['open'].index:
        current_price_in_btc, symbol, balance = portfolio['open'].loc[coin, ['current_price(btc)', 'symbol', 'balance']]
        symbol_pair = symbol.upper() + '-USDT'
        price = kucoin_pairs_with_price_and_vol_current[symbol_pair]['price'] if symbol_pair in kucoin_pairs_with_price_and_vol_current else float("NaN")
        portfolio_usdt_value += price*balance
    portfolio_usdt_value_growth = (portfolio_usdt_value - portfolio['constants']['start_balance']['usdt']) / portfolio['constants']['start_balance']['usdt'] # float(portfolio_name.split("_")[-3]) # ultimately worried about btc value, maybe refactor and add portfolio roi
    print(portfolio_name + ", USDT Value: " + str(portfolio_usdt_value) + ", USDT Value Growth: " + str(portfolio_usdt_value_growth))

# Check outlier individual portfolios ('10_-10_20_[-0.3, 0.5, -0.2]_1000_10000_1000_1000' is an example portfolio):
portfolios['10_-10_20_[-0.3, 0.5, -0.2]_1000_10000_1000_1000']['open'].sort_values('current_roi', inplace=False, ascending=False)[['symbol', 'buy_date', 'buy_price', 'balance', 'rank_rise_d', 'current_date', 'current_price', 'current_roi','current_roi(btc)']]
portfolios['10_-10_20_[-0.3, 0.5, -0.2]_1000_10000_1000_1000']['sold'].sort_values('roi(btc)', inplace=False, ascending=False)[['symbol', 'buy_date', 'buy_price', 'buy_price(btc)', 'balance', 'rank_rise_d', 'sell_date', 'sell_price', 'sell_price(btc)', 'roi(btc)']]

# if want to update a saved portfolios dict to current dates and not iterate over past values (make sure to check dates):
import copy
portfolios_updated = {}
for portfolio_name, portfolio in portfolios.items():
    print(portfolio_name)
    new_portfolio = copy.deepcopy(portfolio)
    if portfolio_name in portfolios_updated:
        continue
    # make sure start_day is the last day the previous portfolios were run - max(bt_days)
    portfolios_updated[portfolio_name] = crypto.run_portfolio_rr(portfolio=new_portfolio, start_day=datetime.strptime('2024_07_29 17:00:00', '%Y_%m_%d %H:%M:%S'), end_day=datetime.strptime('2024_08_20 17:00:00', '%Y_%m_%d %H:%M:%S'), rr_sell=True, paper_trading=True, back_testing=True)`

## Checking Stocks Senate trade data

`df_tickers_sp500 = stocks._fetch_data(stocks.get_sp500_ranked_tickers_by_marketbeat, params={}, error_str=" - No s&p 500 tickers data from Market Beat on: " + str(datetime.now()), empty_data = pd.DataFrame())
senate_timestamps_and_tickers_inflows_and_outflows = stocks._fetch_data(stocks.get_senate_timestamps_and_tickers_inflows_and_outflows_by_month_for_stocks, params={'stocks_list': list(df_tickers_sp500.index)}, error_str=" - Issues with senate timestamps and tickers inflows and outflows by month data from FMP on: " + str(datetime.now()), empty_data = pd.DataFrame())`

## Other Information

* Picks up major holidays (will sleep during holidays like weekends)

* Sometimes deleting old portfolios won't work, ie portfolio_rr_50_-50_20_-0.2_0.2_-0.05_2000_100_True_False_False_{'usd'/ 10000}_2024-12-01_to_2025-11-14.pckl won't be properly replaced with saved portfolio on 2025-11-17 and you'll have to manually delete old files such as this one

* CoinMarketCap will change their html every so often (probably to avoid scrapers), and you'll have to manually change crypto.py#get_coinmarketcap_coin_data() - span_price & dl_statistics = soup.find "class" element search identifiers

* Services (quant-trading, saved financial & social data since 2020, backtesting, algorithms, incorporating data & financial APIs, personal remote quant-trading)

## Contributing

  1. Fork it
  1. Create your feature branch (`git checkout -b my-new-feature`)
  1. Commit your changes (`git commit -am 'Add some feature'`)
  1. Push to the branch (`git push origin my-new-feature`)
  1. Create new Pull Request

Bug reports and pull requests are welcome on GitHub at https://github.com/speterlin/quant-trading. This project is intended to be a safe, welcoming space for collaboration, and contributors are expected to adhere to the [Contributor Covenant](http://contributor-covenant.org) code of conduct.

## License

The gem is available as open source under the terms of the [MIT License](http://opensource.org/licenses/MIT).
