import ccxt
import pandas as pd
import time
import pprint
import requests

webhook_url = 'https://discordapp.com/api/webhooks/1095655937735413772/pmE27Cok8_W-arSpcpwfhE_uOm_h5VQZG-gbv-vWnUk1cs9H6x3TBPpWPo49KWaqTRo_'


exc = {'content': '오류발생'}
inlong={'content':'long진입'}
outlong={'content':'long close'}
inshort={'content':'short in'}
outshort={'content':'short close'}


def heiken_ashi(df):
    # 하이킨 아시 캔들 차트를 계산하는 함수

    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = (df['open'].shift(1) + df['close'].shift(1)) / 2
    ha_high = df[['high', 'close']].max(axis=1)
    ha_low = df[['low', 'close']].min(axis=1)

    df['ha_close'] = ha_close
    df['ha_open'] = ha_open
    df['ha_high'] = ha_high
    df['ha_low'] = ha_low

    return df

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



# 바이낸스 API 인스턴스 생성
exchange = ccxt.binance()
#*************************설정***************************************************************************
# 시장(symbol) 설정 (예: BTC/USDT)
symbol = 'CFX/USDT'#<<<<<<<<<<<<<<<<<<<<<코인 설정
inputper=25  #<<<<<<<<<<<<<진입량per
lev=20 #<<<<<<<<<<<<<<<<레버리지
limitprofit=0.005#<<<<<<<<<<<<<<<<<<<<<<<<<0.5퍼 먹으면 튀기
timeframe = '15m'# 타임프레임(timeframe) 설정 (예: 15분)



#editsym=symbol.replace("/","")
markets = binance.load_markets()
market = binance.market(symbol)
editsym=market['id']






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
    


try:
    while True:
        # 바이낸스 API로 OHLCV 데이터 가져오기
        ohlcvs = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcvs, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')  # 타임스탬프를 날짜/시간 형식으로 변환
        df.set_index('timestamp', inplace=True)  # 인덱스를 날짜/시간으로 설정

        # 하이킨 아시 캔들 차트로 변환
        heidf = heiken_ashi(df)

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
        
        

        # 현재 진행 중인 봉의 이전 봉
        current_candle = heidf.iloc[-1]
        previous_candle = heidf.iloc[-2]
        
        #진입코드 설정
        while posiamt==0:  #포지션이 존재하지않을 경우에만 진입
            print("포지션 진입루프")

            #long 
            if  previous_candle['ha_close'] > previous_candle['ha_open']:
                order = binance.create_market_buy_order(
                symbol=symbol,
                amount=amtper(inputper,lev))
                response = requests.post(webhook_url, json=inlong)
                time.sleep(15)
                break
        
            #short
            elif previous_candle['ha_close'] < previous_candle['ha_open']:         
                order = binance.create_market_sell_order(
                symbol=symbol,
                amount=amtper(inputper,lev))
                response = requests.post(webhook_url, json=inshort)
                time.sleep(15)
                break
            else :
                time.sleep(10)
                break


        #포지션 정리
        while posiamt!=0:
            #1불 먹튀 
            print("포지션 정리 루프")
            absposi=abs(posiamt)
            usdamt=entryprice*absposi
            print(usdamt*limitprofit)
            if unprofit>=usdamt*limitprofit:
                if posiamt>0:
                    order = binance.create_market_sell_order(
                    symbol=symbol,
                    amount=absposi)
                    response = requests.post(webhook_url, json=outlong)
                    time.sleep(300)
                    break
                elif posiamt<0:
                    order = binance.create_market_buy_order(
                    symbol=symbol,
                    amount=absposi)
                    response = requests.post(webhook_url, json=outshort)
                    time.sleep(300)
                    break
                    


            #long exit
            elif posiamt>0 and previous_candle['ha_close'] < previous_candle['ha_open']:
                order = binance.create_market_sell_order(
                symbol=symbol,
                amount=absposi)
                response = requests.post(webhook_url, json=outlong)
                time.sleep(10)
                break
            
            #short 정리
            elif posiamt<0 and previous_candle['ha_close'] > previous_candle['ha_open']:
                order = binance.create_market_buy_order(
                symbol=symbol,
                amount=absposi)
                response = requests.post(webhook_url, json=outshort)
                time.sleep(10)
                break
            else :
                time.sleep(10)
                break


except Exception as ex:
    print(ex)
    response = requests.post(webhook_url, json=exc)

            
            




























   

    
