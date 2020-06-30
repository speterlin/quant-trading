import pandas as pd
import numpy as np

import yfinance as yf

def get_ticker_data(ticker=None, start_datetime=None, end_datetime=None, interval="1d"):
    data = yf.download(ticker, start_datetime, end_datetime, interval=interval)
    return data

import requests

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
        if retry and ((type(e) in [UnboundLocalError, TimeoutError, requests.exceptions.ConnectionError, requests.exceptions.TooManyRedirects]) or (type(e) == requests.exceptions.HTTPError and e.response.status_code == 429)): # UnboundLocalError because of response error (local variable 'response' referenced before assignment), if use urllib for request TimeoutError is urllib.error.URLError: <urlopen error [Errno 60] Operation timed out>, requests.exceptions.ConnectionError is for (even when not using urllib): NewConnectionError('<urllib3.connection.VerifiedHTTPSConnection object at 0x119429240>: Failed to establish a new connection: [Errno 60] Operation timed out and: requests.exceptions.ConnectionError: ('Connection aborted.', OSError("(54, 'ECONNRESET')",)), currently unresolved - (even when not using urllib): Max retries exceeded with url: /?t=PD (Caused by SSLError(SSLError("bad handshake: SysCallError(50/54/60, 'ENETDOWN'/'ETIMEDOUT'/'ECONNRESET')",)
            time.sleep(60) # CoinGecko has limit of 100 requests/minute therefore sleep for a minute, unsure of request limit for Google Trends
            data = _fetch_data(func, params, error_str, empty_data, retry=False)
    return data

import requests
import bs4 as bs

# assumes wikipedia page updates S&P 500 tickers, also using slickcharts, can also do dow jones etc # sometimes an 'SyntaxError: invalid syntax' error near end of method (last line of for loop / return statement) - delete rows end to beginning and see where error lies has to do with whitespace
def get_sp500_ranked_tickers():
    resp = requests.get('https://www.slickcharts.com/sp500') # , verify=False # ISSUE - site doesn't update data daily it's a 1 day lag, 'http://en.wikipedia.org/wiki/List_of_S%26P_500_companies
    soup = bs.BeautifulSoup(resp.text, 'lxml')
    table = soup.find('table', {'class': 'table table-hover table-borderless table-sm'}) # 'wikitable sortable'
    df_tickers = pd.DataFrame(columns = ["Company Name", "S&P 500 Rank"]).astype({'Company Name': 'object','S&P 500 Rank': 'float64'}) # think since assigning multiple values at once below
    for row in table.findAll('tr')[1:]:
        tds = row.findAll('td')
        sp_rank = float(tds[0].text.strip()) if tds[0].text.strip() else None # probably refactor
        company_name = tds[1].text.strip()
        ticker = tds[2].text.strip()
        df_tickers.loc[ticker, ['Company Name', 'S&P 500 Rank']] = [company_name, sp_rank]
    return df_tickers

def get_zacks_data(ticker=None):
    # zacks rank, can also do motley fool, found from github.com/janlukasschroeder/zacks-api
    resp = requests.get("https://quote-feed.zacks.com/?t=" + ticker) # , verify=False
    data = resp.json()
    return data

from datetime import datetime, timedelta
trading_view_ratings = {"Strong Buy": 1, "Buy": 2, "Neutral": 3, "Sell": 4, "Strong Sell": 5}

def save_tickers_historical_data():
    # get publicly listed (in USA exchanges) companies sorted by market cap # on tradingview.com/screener/: remove Change, Price to Earnings Ratio (TTM), add D/E Ratio (MRQ), Div Yield (FY), P/FCF (TTM), P/B (FY), EV (MRQ), maybe add Commodity Channel Index (20), EV/EBITDA (TTM), Goodwill, Industry, P/S (FY), Total (Current) Assets, Return on Assets/Equity/Invested Capital # issue: unsure why some tickers are removed from tradingview.com/screener/ day-to-day
    df_usa_tickers = pd.read_csv("data/stocks/tv_screener_by_market_cap/america_2020-06-04.csv") # maybe refactor and add _tv to name to indicate tradingview data,ratings
    df_usa_tickers = df_usa_tickers.set_index('Ticker').rename(columns={"Market Capitalization": "Market Cap", "Number of Employees": "# Employees", "Debt to Equity Ratio (MRQ)": "D/E Ratio (MRQ)", "Dividends Yield (FY)": "Div Yield (FY)", "Price to Free Cash Flow (TTM)": "P/FCF (TTM)", "Price to Book (FY)": "P/B (FY)", "Enterprise Value (MRQ)": "EV (MRQ)"}) # , "Price to Earnings Ratio (TTM)": "P/E Ratio (TTM)",
    df_usa_tickers = df_usa_tickers.join(get_sp500_ranked_tickers()['S&P 500 Rank'], on=df_usa_tickers.index)
    df_usa_tickers['Rating'] = df_usa_tickers.apply(lambda x: trading_view_ratings[x['Rating']] if type(x['Rating']) == str else None, axis=1) # converts dtype to float64 as well
    # add zacks rank
    df_usa_tickers_zr = df_usa_tickers.copy() # maybe remove since not using original df_usa_tickers
    for ticker in df_usa_tickers_zr[df_usa_tickers_zr['Market Cap'] >= 2e9].index:
        # if not np.isnan(df_usa_tickers_zr.loc[ticker, 'Zacks Rank']):
        #     continue
        zacks_data = _fetch_data(get_zacks_data, params={'ticker': ticker}, error_str=" - No Zacks Data for ticker " + ticker, empty_data = pd.DataFrame())
        if 'source' not in zacks_data[ticker] and zacks_data[ticker]['error'] == 'true': # 'market_data' not in ticker_data or not ticker_data['market_data']['market_cap']['usd']: # remove granular from error_str
            print("Error retreiving zacks data for ticker: " + ticker + " on date: " + datetime.now().strftime('%Y-%m-%d'))
        else:
            # other interesting keys: (BATS/SUNGARD) earnings, p/e ratiom, dividend yield, ...
            df_usa_tickers_zr.loc[ticker, 'Zacks Rank'] = float(zacks_data[ticker]['zacks_rank']) if zacks_data[ticker]['zacks_rank'] else None # Zacks Rank Text is just the following words corresponding to the rank (1-5): ['Strong Buy', 'Buy', 'Hold', 'Sell', 'Strong Sell']
            df_usa_tickers_zr.loc[ticker, 'Zacks Updated At'] = pd.to_datetime(zacks_data[ticker]['updated'])
    return df_usa_tickers_zr

# 2020-05-18 is without zacks rank, issue
def get_saved_tickers_historical_data(date=None, category='all', rankings=['zr']): # date is a string in format '%Y-%m-%d', categories: 'sp500', 'usa'
    if category == 'all':
        category = 'sp500' if datetime.strptime(date, '%Y-%m-%d').date() < datetime.strptime('2020-05-08', '%Y-%m-%d').date() else 'usa'
    try:
        f = open('data/stocks/tickers_historical_saved_data/' + category + '/tickers_' + '_'.join(rankings) + '_' + date + '.pckl', 'rb')
        data = pickle.load(f)
        f.close()
    except Exception as e:
        print(str(e) + " - No " + category + " tickers " + str(rankings) + " historical saved data for date: " + date)
        # data for crypto, maybe add some of these columns: df_tickers = pd.DataFrame(columns = ["Market Cap Rank", "Facebook Likes", "Twitter Followers", "Reddit Subscribers", "Reddit Posts & Comments 48h", "Developer Stars", "Developer Issues", "Alexa Rank", "Supply: Total-Circulating"]) # maybe add columns like "Google Trends"
        data = pd.DataFrame() # columns = ["Company Name", "S&P 500 Rank", "Zacks Rank", "Zacks Updated At"]
    return data

import time
from datetime import datetime, timedelta
from pytz import timezone
import os
import alpaca_trade_api as tradeapi

def run_portfolio_zr():
    #Specify paper trading environment
    os.environ["APCA_API_BASE_URL"] = "https://paper-api.alpaca.markets"
    #Insert API Credentials
    api = tradeapi.REST('PKY736IF7JCC6NBFP52W', 'qSGahH0Gpz6yTu9Lf3Pk5zcj4Xs32ELzemKzG1Jn', api_version='v2') # or use ENV Vars shown below
    account = api.get_account()

    #Trading_algo
    portfolio = api.list_positions()
    clock = api.get_clock()
    api.submit_order(symbol = stock1,qty = number_of_shares,side = 'sell',type = 'market',time_in_force ='day')
    api.close_position(stock1)

start_time = time.time()
ticker = 'TSLA'
eastern = timezone('US/Eastern')
while (datetime.now(eastern).weekday() < 5) and (datetime.now(eastern).hour >= 9) and (datetime.now(eastern).hour <= 16): # stocks: maybe refactor to get total time in seconds (from beginning of day) instead of like this, so can be more exact (i.e. start at 9:30am EST)
    ticker_data = _fetch_data(get_ticker_data, params={'ticker': ticker, 'start_datetime': stop_day - timedelta(hours=7), 'end_datetime': stop_day, 'interval': '1m'}, error_str=" - No " + "1m" + " ticker data for: " + ticker + " from datetime: " + str(stop_day - timedelta(hours=7)) + " to datetime: " + str(stop_day), empty_data=pd.DataFrame())
    time.sleep(60.0 - ((time.time() - start_time) % 60.0))
