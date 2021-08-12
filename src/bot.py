"""
Foreign Exchange Bot using Oanda API

:REFERENCE:
- https://jantzen.hatenablog.com/entry/oandaapi_03
"""

# libraries
import os
import pathlib
import datetime
import requests
import json
import time
from tqdm.auto import tqdm
import numpy as np
import pandas as pd

# --------------------------
# Config  
# --------------------------
class CFG:
    """
    config for bot
    """
    API_Token = '********************************-********************************'
    API_AccountID = '999-999-99999999-999'
    API_URL =  "https://api-fxtrade.oanda.com"
    # API_URL =  "https://api-fxpractice.oanda.com"

    # currency pair
    INSTRUMENT = "USD_JPY"

    # action
    ACTION = 'candles'
    # ACTION = 'order'
    # ACTION = 'pricing'

    # candles
    PRICE = 'M' # B, A
    GRANULARITY = 'M10' # S30, H1, D, W
    COUNT = 5000 # 500

    # dir
    OUTPUT_DIR = './'

# --------------------------
# Logging
# --------------------------
def init_logger(log_file='train.log'):
    """
    logging
    """
    from logging import getLogger, INFO, FileHandler,  Formatter,  StreamHandler
    logger = getLogger(__name__)
    logger.setLevel(INFO)
    handler1 = StreamHandler()
    handler1.setFormatter(Formatter("%(message)s"))
    handler2 = FileHandler(filename=log_file)
    handler2.setFormatter(Formatter("%(message)s"))
    logger.addHandler(handler1)
    logger.addHandler(handler2)
    return logger
logger = init_logger(os.path.join(CFG.OUTPUT_DIR, 'bot.log'))
logger.info('START!')

# --------------------------
# Utils
# --------------------------
# candles
def get_ohlcv(
    api_url='https://api-fxtrade.oanda.com'
    , account_id: str='999-999-99999999-999'
    , api_token: str= '********************************-********************************'
    , instrument: str='USD_JPY'
    , count: int=500
    , price_type: str='M'
    , granularity: str='M10'
    , tz : str='Asia/Tokyo'
    , repeat : int=1
    ) -> pd.DataFrame:

    """
    Get historical OHLCV up to the latest period

    :INPUT:
    - api_url : api url
    - account_id : your Oanda account id
    - api_token : your Oanda api token
    - instrument : currency pair (e.g., 'USD_JPY', 'EUR_JPY')
    - count : the number of records to be fetched (1 <= count <= 5000)
    - price_type : 'M' (mean), 'A' (ask), 'B' (bid)
    - granularity : granularity of records (e.g., 'S15', 'M1', 'H4', 'D', 'W')
    - tz : time zone (e.g., 'Asia/Tokyo', 'US/Pacific')
    - repeat : the number of repeats to fetch records (more repeats, longer historical data)

    :OUTPUT:
    - pandas dataframe (time, open, high, low, close, volume)

    :EXAMPLE:
    # your account info
    account_id = '999-999-99999999-999'
    api_token = '********************************-********************************'

    # fetch ohlcv via API
    df = get_candles(
        api_url='https://api-fxtrade.oanda.com'
        , account_id=account_id
        , api_token=api_token
        , instrument='USD_JPY'
        , granularity='M10'
    )

    # check
    print(df.shape)
    df.tail()

    :REFERENCE:
    - https://jantzen.hatenablog.com/entry/oandaapi_03
    - https://jantzen.hatenablog.com/entry/oandaapi_04
    """
    # endpoint
    url = f'{api_url}/v3/accounts/{account_id}/instruments/{instrument}/candles?'

    # header
    headers = { 
        "Accept-Datetime-Format" : "UNIX",
        "Authorization" : "Bearer " + api_token
    }

    # fetch data
    df = pd.DataFrame()
    for i in tqdm(range(repeat)):
        # request to server
        if i == 0:
            url_ = f'{url}count={count}&price={price_type}&granularity={granularity}'
        else:
            to = Response_Body["candles"][0]["time"] 
            since = '{}.000000000'.format(int(float(to) - (float(Response_Body["candles"][-1]["time"]) - float(to))))
            url_ = f'{url}&price={price_type}&granularity={granularity}&from={since}&to={to}&includeFirst=False'
            
        print(f'endpoint: {url_}')
        try:
            response = requests.get(url_, headers=headers)
            Response_Body = response.json()
        except Exception as e:
            print(str(e))
        
        # format to pandas dataframe
        tmp = pd.json_normalize(
            Response_Body
            , record_path='candles'
            , meta=['instrument', 'granularity']
            , sep='_'
            ).drop(columns=['granularity'])

        # concat
        df = pd.concat([tmp, df])

        # sleep
        time.sleep(1)

    # fix column names
    df.rename(columns={'mid_o': 'open', 'mid_h': 'high', 'mid_l': 'low', 'mid_c': 'close'}, inplace=True)
    df = df[
        ['time', 'open', 'high', 'low', 'close', 'volume']
    ].drop_duplicates().sort_values(by=['time']).reset_index(drop=True)

    # convert to JST
    df['time'] = df['time'].apply(lambda x : datetime.datetime.utcfromtimestamp(int(x.split('.')[0])))
    df['time'] = pd.to_datetime(df['time']).dt.tz_localize(tz)

    return df
  
def order(
    api_url='https://api-fxtrade.oanda.com'
    , account_id: str='999-999-99999999-999'
    , api_token: str= '********************************-********************************'
    , instrument: str='USD_JPY'
    , order_units: int=1
    , entry_price: float=104.44
    , order_type: str='MARKET'
    , time_in_force: str='IOC'
    , position_fill : str='DEFAULT'
    , take_profit_price=None
    , stop_loss_price=None
    ):

    """
    Post an order via Oanda API

    :INPUT:
    - api_url : api url
    - account_id : your Oanda account id
    - api_token : your Oanda api token
    - instrument : currency pair (e.g., 'USD_JPY', 'EUR_JPY')
    - order_units : order unit (negative for short position)
    - entry_price : entry price
    - order_type : 'LIMIT' or 'MARKET'
    - time_in_force : 'FOK' or 'IOC'
    - position_fill : 'DEFAULT'（'REDUCE_FIRST'), 'OPEN_ONLY', 'REDUCE_FIRST', 'REDUCE_ONLY'
    - take_profit_price : price for take profit
    - stop_loss_price : price for stop loss

    :EXAMPLE:
    # your account info
    account_id = '999-999-99999999-999'
    api_token = '********************************-********************************'

    # sell 2 USD_JPY with market order
    order(
        api_url='https://api-fxtrade.oanda.com'
        , account_id=account_id
        , api_token=api_token
        , instrument='USD_JPY'
        , order_units=2
        , entry_price=-104.44
        , order_type='MARKET'
    )

    :REFERENCE:
    - https://jantzen.hatenablog.com/entry/oandaapi-10
    """
    
    # endpoint
    url = f'{api_url}/v3/accounts/{account_id}/orders'

    # header
    headers = { 
        "Authorization" : 'Bearer ' + api_token
        , 'Content-Type': 'application/json'
    }

    # format order data to json
    data = {
        "order": {
                "units": str(order_units),
                "price": str(entry_price),
                "instrument": instrument,
                "timeInForce": time_in_force,
                "type": order_type,
                "positionFill": position_fill,
                }
        }
    if take_profit_price is not None:
        data['order']['takeProfitOnFill'] = {'price': str(take_profit_price)}
    if stop_loss_price is not None:
        data['order']['stopLossOnFill'] = {'price': str(stop_loss_price)}
    data = json.dumps(data)

    # order
    try:
        # request to server
        Response_Body = requests.post(url, headers=headers, data=data)

        # error?
        logger.info(json.dumps(Response_Body.json(), indent=2))
        Response_Body.raise_for_status()
        
        # executed
        if 'orderFillTransaction' in Response_Body.json().keys(): # LIMITで逆指値になったような場合
            Trade_No = Response_Body.json()['orderFillTransaction']['tradeOpened']['tradeID']

        # ordered
        elif 'orderCreateTransaction' in Response_Body.json().keys(): # 成功したらOrder IDをもとに検索
            Order_No = Response_Body.json()['orderCreateTransaction']['id']
            url = f'{api_url}/v3/accounts/{account_id}/orders/{Order_No}'

            while True:
                Response_Body = requests.get(url, headers=headers)
                Response_Body.raise_for_status()

                # check
                response = Response_Body.json()
                
                if response["order"]["state"] == "PENDING":
                    print("wait...!!!")
                else:
                    if response["order"]["state"] == "CANCELLED":
                        print("canceled...!!!")
                    elif response["order"]["state"] == "FILLED":
                        print("executed...!!!")
                        Trade_No = response["order"]['tradeOpenedID']
                    else:
                        print("Other case: %s" %(response["order"]["state"]))                                
                        break
                        
                    time.sleep(60)

                # Loop Return                
                
        # if order is not filled
        elif 'orderCancelTransaction' in Response_Body.json().keys():
            print("Reason for Cancel : %s" %Response_Body.json()['orderCancelTransaction']['reason'])
        elif 'orderRejectTransaction' in Response_Body.json().keys():
            print("Reason for Reject : %s" %Response_Body.json()['orderRejectTransaction']['reason'])
        else:
            print('ERR?')
    
    except Exception as e:
        if "Response_Body" in locals(): #vars()
            print("Pattern3(raise) : %s" %Response_Body.text)
            l = locals()
            v = vars()
        print(e)

def main():
    print('write your own logic!')

if __name__ == "__main__":
    main()
