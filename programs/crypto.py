# venv/bin/python programs/crypto.py

from datetime import datetime, timedelta
import time

while True:
    start_time = time.time()
    print("<< " + str(datetime.now()) + " I'm here" + " >>")
    time.sleep(60.0 - ((time.time() - start_time) % 60.0))
