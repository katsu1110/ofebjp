"""
Foreign Exchange Bot using Oanda API

:REFERENCE:
- https://jantzen.hatenablog.com/entry/oandaapi_03
"""

# libraries
import os
import pathlib
import datetime
import numpy as np
import pandas as pd
import requests
import json
import time

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
    GRANULARITY = 'M5' # S30, H1, D, W
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
# url
def get_url(action='order'):
    """
    get proper url
    """
    if action == 'order':
        url = CFG.API_URL + "/v3/accounts/%s/orders" % str(CFG.API_AccountID)
    elif action == 'pricing':
        url = CFG.API_URL + "/v3/accounts/%s/pricing?instruments=%s" % (
            str(CFG.API_AccountID), CFG.INSTRUMENT
            )
    elif action == 'candles':
        url = CFG.API_URL + "/v3/accounts/%s/candles?count=%s&price=%s&granularity=%s" % (
            str(CFG.API_AccountID), CFG.COUNT, CFG.PRICE, CFG.GRANULARITY
            )
    return url

# header
def get_header(action='candles'):
    """
    get header
    """
    headers = { 
        "Accept-Datetime-Format" : "UNIX",
        "Authorization" : "Bearer " + CFG.API_Token
    }
    if action == 'order':
        headers["Content-Type"] = "application/json"
    return headers

# candles
def get_candles():
    """
    get candles
    """
    # url
    url = get_url('candles')

    # header
    headers = get_header('candles')

    # request to server
    response = requests.get(url, headers=headers)
    Response_Body = response.json()
    
    # fetch
    df = pd.json_normalize(
        Response_Body
        , record_path='candles'
        , meta=['instrument', 'granularity']
        , sep='_'
        ).drop(columns=['complete', 'granularity'])

    # fix column names
    df.rename(columns={'mid_o': 'open', 'mid_h': 'high', 'mid_l': 'low', 'mid_c': 'close'}, inplace=True)

    # convert to JST
    df['time'] = pd.to_datetime(df['time']).dt.tz_convert('Asia/Tokyo')

    return df
  
#データ情報の変数の設定
Order_units = 1
Entry_price = 104.44
  
data_Limit = {
    "order": {
            "units": Order_units,
            "price": str(Entry_price),
            "instrument": CFG.INSTRUMENT,
            "timeInForce": "GTC",
            "type": "LIMIT",
            "positionFill": "DEFAULT",
            }
    }    
    
def order(data_Limit: dict):
    """
    order
    """
    # url
    url = get_url('order')

    # header
    headers = get_header('order')

    # data to json
    data = json.dumps(data_Limit)

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
            url = CFG.API_URL + "/v3/accounts/%s/orders/%s" %(str(CFG.API_AccountID), Order_No)

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
                        print("その他の場合: %s" %(response["order"]["state"]))                                
                        break
                        
                    time.sleep(60)
                #Loop Return                
                
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
    print('aaa')

if __name__ == "__main__":
    main()
