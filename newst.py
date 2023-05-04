import ccxt
import pandas as pd
import time
import pprint
import requests
import numpy as np

webhook_url = 'https://discordapp.com/api/webhooks/1095655937735413772/pmE27Cok8_W-arSpcpwfhE_uOm_h5VQZG-gbv-vWnUk1cs9H6x3TBPpWPo49KWaqTRo_'


exc = {'content': '오류발생'}
inlong={'content':'long진입'}
outlong={'content':'long close'}
inshort={'content':'short in'}
outshort={'content':'short close'}


# def heiken_ashi(df):
#     # 하이킨 아시 캔들 차트를 계산하는 함수

#     ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
#     ha_open = (df['open'].shift(1) + df['close'].shift(1)) / 2
#     ha_high = df[['high', 'close']].max(axis=1)
#     ha_low = df[['low', 'close']].min(axis=1)

#     df['ha_close'] = ha_close
#     df['ha_open'] = ha_open
#     df['ha_high'] = ha_high
#     df['ha_low'] = ha_low

#     return df
def setema(ohlcvs,ema_period):
    prices = np.zeros(len(ohlcvs))
    ema_values = np.zeros(len(ohlcvs))
    # 종가만 추출하여 prices 배열에 저장
    for i in range(len(ohlcvs)):
        prices[i] = ohlcvs[i][4]

    # 첫 번째 EMA 값은 SMA(단순 이동 평균)으로 계산
    sma = np.sum(prices[:ema_period]) / ema_period
    ema_values[ema_period - 1] = sma

    # EMA 계산
    multiplier = 2 / (ema_period + 1)
    for i in range(ema_period, len(prices)):
        ema = (prices[i] - ema_values[i - 1]) * multiplier + ema_values[i - 1]
        ema_values[i] = ema
    return ema_values[-1]

api_key = ""
secret  = ""

binance = ccxt.binance(config={
    'apiKey': api_key, 
    'secret': secret,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'
    }
})





#*************************설정***************************************************************************
# 시장(symbol) 설정 (예: BTC/USDT)
symbol = 'DYDX/USDT'#<<<<<<<<<<<<<<<<<<<<<코인 설정
inputper=33  #<<<<<<<<<<<<<진입량per
lev=10 #<<<<<<<<<<<<<<<<레버리지

timeframe = '15m'# 타임프레임(timeframe) 설정 (예: 15분)
#슈퍼트렌드 설정
period = 10     
multiplier = 3



#editsym=symbol.replace("/","")
markets = binance.load_markets()
market = binance.market(symbol)
editsym=market['id']


#슈퍼트렌드 기모띠 Long==true
def Supertrend(df, atr_period, multiplier):
    
    high = df['high']
    low = df['low']
    close = df['close']
    
    # calculate ATR
    price_diffs = [high - low, 
                   high - close.shift(), 
                   close.shift() - low]
    true_range = pd.concat(price_diffs, axis=1)
    true_range = true_range.abs().max(axis=1)
    # default ATR calculation in supertrend indicator
    atr = true_range.ewm(alpha=1/atr_period,min_periods=atr_period).mean() 
    # df['atr'] = df['tr'].rolling(atr_period).mean()
    
    # HL2 is simply the average of high and low prices
    hl2 = (high + low) / 2
    # upperband and lowerband calculation
    # notice that final bands are set to be equal to the respective bands
    final_upperband = upperband = hl2 + (multiplier * atr)
    final_lowerband = lowerband = hl2 - (multiplier * atr)
    
    # initialize Supertrend column to True
    supertrend = [True] * len(df)
    
    for i in range(1, len(df.index)):
        curr, prev = i, i-1
        
        # if current close price crosses above upperband
        if close[curr] > final_upperband[prev]:
            supertrend[curr] = True
        # if current close price crosses below lowerband
        elif close[curr] < final_lowerband[prev]:
            supertrend[curr] = False
        # else, the trend continues
        else:
            supertrend[curr] = supertrend[prev]
            
            # adjustment to the final bands
            if supertrend[curr] == True and final_lowerband[curr] < final_lowerband[prev]:
                final_lowerband[curr] = final_lowerband[prev]
            if supertrend[curr] == False and final_upperband[curr] > final_upperband[prev]:
                final_upperband[curr] = final_upperband[prev]

        # to remove bands according to the trend direction
        if supertrend[curr] == True:
            final_upperband[curr] = np.nan
        else:
            final_lowerband[curr] = np.nan
    
    return pd.DataFrame({
        'Supertrend': supertrend,
        'Lowerband': final_lowerband,
        'Upperband': final_upperband
    }, index=df.index)






#레버리지 설정 코드
resp = binance.fapiPrivate_post_leverage({
    'symbol': editsym,
    'leverage': lev
})




# 데이터 개수 설정 (예: 최근 100개)
limit = 100
#자산 진입량 변환 함수
def amtper(a,c=1):#a==진입 퍼센트 c==leverage 현재사용가능한 자산에 a퍼센트만큼 c레버리지 양만큼 구매
    balance = binance.fetch_balance()
    b=(balance['USDT']['free'])
    totalinput=b*a*c/100
    ticker = binance.fetch_ticker(symbol)
    cur_price=ticker['close']
    amt=totalinput/cur_price
    return round(amt,4)
    
Lchecksupertrend=1
Schecksupertrend=1
divprofit=0
addamt=0
try:
    while True:
        print("루프시작")
        # 바이낸스 API로 OHLCV 데이터 가져오기
        ohlcvs = binance.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcvs, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')  # 타임스탬프를 날짜/시간 형식으로 변환
        df.set_index('timestamp', inplace=True)  # 인덱스를 날짜/시간으로 설정
        
        

        

        # 하이킨 아시 캔들 차트로 변환
        # heidf = heiken_ashi(df)

        #포지션 존재하는지 검증 코드
        balance = binance.fetch_balance()
        positions = balance['info']['positions']
        posiamt=0
        for position in positions:
            if position["symbol"] == editsym:
                # pprint.pprint(position)
                posiamt=position['positionAmt']
                unprofit=position['unrealizedProfit']
                entryprice=position['entryPrice']
        posiamt=float(posiamt)
        unprofit=float(unprofit)
        entryprice=float(entryprice)
        absposi=abs(posiamt)
        
        

        currentprice=df.iloc[-1]['close']

        cur_super=Supertrend(df, 10, 3)
        
        if cur_super.iloc[-1]['Supertrend']==True:
            supertrendprice=cur_super.iloc[-1]['Lowerband']
        else:
            supertrendprice=cur_super.iloc[-1]['Upperband']

        ema14=setema(ohlcvs,14)
        ema60=setema(ohlcvs,60)
        ema20=setema(ohlcvs,20)
        

        # 현재 진행 중인 봉의 이전 봉
        # current_candle = heidf.iloc[-1]
        # previous_candle = heidf.iloc[-2]
        
        #진입코드 설정
        while posiamt==0:  #포지션이 존재하지않을 경우에만 진입
            print("포지션 진입루프")

            #long 
            if  cur_super.iloc[-1]['Supertrend']==True and ema20>=currentprice:
                order = binance.create_market_buy_order(
                symbol=symbol,
                amount=amtper(inputper,lev))
                response = requests.post(webhook_url, json=inlong)
                time.sleep(10)
                break
            # elif cur_super.iloc[-1]['Supertrend']==True and ema14>=currentprice and Lchecksupertrend==0:
            #     order = binance.create_market_buy_order(
            #     symbol=symbol,
            #     amount=amtper(inputper,lev))
            #     response = requests.post(webhook_url, json=inlong)
            #     time.sleep(10)
            #     Lchecksupertrend+=1
            #     Schecksupertrend=0
            #     break
        
            #short
            elif cur_super.iloc[-1]['Supertrend']==False and ema20<=currentprice:         
                order = binance.create_market_sell_order(
                symbol=symbol,
                amount=amtper(inputper,lev))
                response = requests.post(webhook_url, json=inshort)
                time.sleep(10)
                break

            # elif cur_super.iloc[-1]['Supertrend']==False and ema14<=currentprice and Schecksupertrend==0:         
            #     order = binance.create_market_sell_order(
            #     symbol=symbol,
            #     amount=amtper(inputper,lev))
            #     response = requests.post(webhook_url, json=inshort)
            #     time.sleep(5)
            #     Schecksupertrend+=1
            #     Lchecksupertrend=0
            #     break
            
            else :
                time.sleep(5)
                break


        #스위칭
        while posiamt!=0:
            print("포지션 정리 루프")
            absposi=abs(posiamt)
            #short 스위칭
            if posiamt>0 and cur_super.iloc[-1]['Supertrend']==False and ema20<=currentprice:
                #long 정리
                order = binance.create_market_sell_order(
                symbol=symbol,
                amount=absposi, 
                )
                response = requests.post(webhook_url, json=inshort)
                addamt=0
                divprofit=0
                break

            #long 스위칭
            if posiamt<0 and cur_super.iloc[-1]['Supertrend']==True and ema14>=currentprice:
                #short 정리
                order = binance.create_market_buy_order(
                symbol=symbol,
                amount=absposi, 
                )
                response = requests.post(webhook_url, json=inlong)
                addamt=0
                divprofit=0
                break
            #profit 
            roe=(unprofit*100)/(entryprice*absposi)
            print(roe)
            if roe>=0.8 and divprofit==0 :
                print("1차 정리")
                if posiamt>0:
                    order = binance.create_market_sell_order(
                    symbol=symbol,
                    amount=round(absposi/3,3)
                    )
                    divprofit=1
                    addamt=1
                    break
                if posiamt<0:
                    order = binance.create_market_buy_order(
                    symbol=symbol,
                    amount=round(absposi/3,3)
                    )
                    divprofit=1
                    break
            if roe>=1.4 and divprofit==1 :
                if posiamt>0:
                    order = binance.create_market_sell_order(
                    symbol=symbol,
                    amount=round(absposi/2,3)
                    )
                    divprofit=2
                    break
                if posiamt<0:
                    order = binance.create_market_buy_order(
                    symbol=symbol,
                    amount=round(absposi/2,3)
                    )
                    divprofit=2
                    break
            if roe>=2.4 and divprofit==2 :
                if posiamt>0:
                    order = binance.create_market_sell_order(
                    symbol=symbol,
                    amount=round(absposi,3)
                    )
                    divprofit=0
                    break
                if posiamt<0:
                    order = binance.create_market_buy_order(
                    symbol=symbol,
                    amount=round(absposi,3)
                    )
                    divprofit=0
                    break
            #stoploss
            if roe<=-1.5 :
                print("stop loss")
                if posiamt>0:
                    order = binance.create_market_sell_order(
                    symbol=symbol,
                    amount=round(absposi,3)
                    )
                    divprofit=0
                    break
                if posiamt<0:
                    order = binance.create_market_buy_order(
                    symbol=symbol,
                    amount=round(absposi,3)
                    )
                    divprofit=0
                    break
            #추가 진입함수
                #long 
            if  cur_super.iloc[-1]['Supertrend']==True and ema20>=currentprice and addamt!=0:
                order = binance.create_market_buy_order(
                symbol=symbol,
                amount=round(amtper(inputper,lev)/3,3))
                response = requests.post(webhook_url, json=inlong)
                print("추가진입")
                addamt=0
                divprofit=0
                time.sleep(10)
                break
            if cur_super.iloc[-1]['Supertrend']==False and ema20<=currentprice and addamt!=0:         
                order = binance.create_market_sell_order(
                symbol=symbol,
                amount=round(amtper(inputper,lev)/3,3))
                response = requests.post(webhook_url, json=inshort)
                print("추가진입")
                addamt=0
                divprofit=0
                time.sleep(10)
                break
                    

                
            
           

            else:
                time.sleep(10)
                break
except Exception as ex:
    print(ex)
    response = requests.post(webhook_url, json=exc)

            
            




























   

    
