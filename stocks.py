import pandas as pd
import numpy as np

import yfinance as yf

def get_ticker_data(ticker=None, start_datetime=None, end_datetime=None, interval="1d"):
    data = yf.download(ticker, start_datetime, end_datetime, interval=interval)
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

import time
from datetime import datetime, timedelta
from pytz import timezone

start_time = time.time()
ticker = 'TSLA'
eastern = timezone('US/Eastern')
while (datetime.now(eastern).weekday() < 5) and (datetime.now(eastern).hour >= 9) and (datetime.now(eastern).hour <= 16): # stocks: maybe refactor to get total time in seconds (from beginning of day) instead of like this, so can be more exact (i.e. start at 9:30am EST)
    ticker_data = _fetch_data(get_ticker_data, params={'ticker': ticker, 'start_datetime': stop_day - timedelta(hours=7), 'end_datetime': stop_day, 'interval': '1m'}, error_str=" - No " + "1m" + " ticker data for: " + ticker + " from datetime: " + str(stop_day - timedelta(hours=7)) + " to datetime: " + str(stop_day), empty_data=pd.DataFrame())
    time.sleep(60.0 - ((time.time() - start_time) % 60.0))
