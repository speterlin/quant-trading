# venv/bin/python programs/crypto.py

from datetime import datetime, timedelta
import time

BTC_INVEST = 0.1
STOP_LOSS = -0.3
TRAILING_STOP_LOSS_ARM, TRAILING_STOP_LOSS_PERCENTAGE = 0.5, -0.2

# binance_client = BinanceClient(ENV['BINANCE_API_KEY'], ENV['BINANCE_API_SECRET'])

def update_positions():
    return

# see if you can run from commandline like python programs/crypto.py run_crypto
def run_crypto(): # positions
    # run algorithm to add/sell open positions
    print("<< " + str(datetime.now()) + " >>")
    start_time = time.time()
    print(time.time() - start_time) # coingecko updates prices every 4 minutes

run_crypto()
