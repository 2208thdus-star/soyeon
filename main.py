from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

STOCKS = [
    ("005930.KS","삼성전자","KOSPI"),("000660.KS","SK하이닉스","KOSPI"),
    ("005380.KS","현대차","KOSPI"),("000270.KS","기아","KOSPI"),
    ("035420.KS","NAVER","KOSPI"),("035720.KS","카카오","KOSPI"),
    ("068270.KS","셀트리온","KOSPI"),("051910.KS","LG화학","KOSPI"),
    ("006400.KS","삼성SDI","KOSPI"),("105560.KS","KB금융","KOSPI"),
    ("055550.KS","신한지주","KOSPI"),("267260.KS","HD현대일렉트릭","KOSPI"),
    ("010120.KS","LS ELECTRIC","KOSPI"),("034020.KS","두산에너빌리티","KOSPI"),
    ("003670.KS","포스코퓨처엠","KOSPI"),("015760.KS","한국전력","KOSPI"),
    ("259960.KS","크래프톤","KOSPI"),("012330.KS","현대모비스","KOSPI"),
    ("066570.KS","LG전자","KOSPI"),("086790.KS","하나금융지주","KOSPI"),
    ("247540.KQ","에코프로비엠","KOSDAQ"),("086520.KQ","에코프로","KOSDAQ"),
    ("028300.KQ","HLB","KOSDAQ"),("196170.KQ","알테오젠","KOSDAQ"),
    ("141080.KQ","리가켐바이오","KOSDAQ"),("214450.KQ","파마리서치","KOSDAQ"),
    ("214150.KQ","클래시스","KOSDAQ"),("403870.KQ","HPSP","KOSDAQ"),
    ("277810.KQ","레인보우로보틱스","KOSDAQ"),("039030.KQ","이오테크닉스","KOSDAQ"),
    ("240810.KQ","원익IPS","KOSDAQ"),("145020.KQ","휴젤","KOSDAQ"),
    ("145720.KQ","덴티움","KOSDAQ"),("005420.KQ","코스모화학","KOSDAQ"),
    ("450080.KQ","에코프로머티","KOSDAQ"),("263750.KQ","펄어비스","KOSDAQ"),
    ("293490.KQ","카카오게임즈","KOSDAQ"),("357780.KQ","솔브레인","KOSDAQ"),
    ("214370.KQ","케어젠","KOSDAQ"),("091990.KQ","셀트리온헬스케어","KOSDAQ"),
]

def slow_stoch(df, k_period, smooth=3, d_period=3):
    low_min  = df['Low'].rolling(k_period).min()
    high_max = df['High'].rolling(k_period).max()
    fast_k   = 100 * (df['Close'] - low_min) / (high_max - low_min + 1e-9)
    slow_k   = fast_k.rolling(smooth).mean()
    slow_d   = slow_k.rolling(d_period).mean()
    return slow_k, slow_d

def find_local_lows(series, pivot=5):
    lows = []
    arr = series.dropna().values
    for i in range(pivot, len(arr) - pivot):
        if arr[i] == np.min(arr[i-pivot:i+pivot+1]):
            lows.append(arr[i])
    return lows

def find_local_highs(series, pivot=5):
    highs = []
    arr = series.dropna().values
    for i in range(pivot, len(arr) - pivot):
        if arr[i] == np.max(arr[i-pivot:i+pivot+1]):
            highs.append(arr[i])
    return highs

def is_rising_lows(series, pivot=5):
    lows = find_local_lows(series, pivot)
    if len(lows) < 2:
        return False
    recent = lows[-3:]
    return all(recent[i] > recent[i-1] for i in range(1, len(recent)))

def is_bearish_div(price, stoch, pivot=5):
    ph = find_local_highs(price, pivot)
    sh = find_local_highs(stoch, pivot)
    if len(ph) < 2 or len(sh) < 2:
        return False
    return ph[-1] > ph[-2] and sh[-1] < sh[-2]

def to_weekly(df):
    return df.resample('W').agg({
        'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'
    }).dropna()

def analyze(ticker, name, market):
    try:
        end = datetime.today()
        start_long  = end - timedelta(days=365*4)
        start_short = end - timedelta(days=365*2)

        df = yf.download(ticker, start=start_long, end=end, progress=False, auto_adjust=True)
        if df is None or len(df) < 60:
            return None

        df.index = pd.to_datetime(df.index)
        wdf = to_weekly(df)
        ddf = df[df.index >= str(start_short.date())].copy()

        if len(wdf) < 30 or len(ddf) < 40:
            return None

        current_price = int(ddf['Close'].iloc[-1])

        # 주봉 스토캐스틱
        wK1, wD1 = slow_stoch(wdf, 20, 3, 10)
        wK2, wD2 = slow_stoch(wdf, 10, 3, 5)
        w_rising = is_rising_lows(wK1.dropna()) or is_rising_lows(wK2.dropna())
        w_bearish = is_bearish_div(wdf['Close'], wK1.dropna())

        # 일봉 스토캐스틱
        dK1, dD1 = slow_stoch(ddf, 20, 3, 10)
        dK2, dD2 = slow_stoch(ddf, 10, 3, 5)
        dK3, dD3 = slow_stoch(ddf, 5,  3, 3)
        d_rising = is_rising_lows(dK1.dropna()) and is_rising_lows(dK2.dropna())

        # 골든크로스
        golden = (
            (dK1.iloc[-2] < dD1.iloc[-2] and dK1.iloc[-1] >= dD1.iloc[-1]) or
            (dK2.iloc[-2] < dD2.iloc[-2] and dK2.iloc[-1] >= dD2.iloc[-1])
        )

        cur_wK1 = round(float(wK1.dropna().iloc[-1]), 1)
        cur_wK2 = round(float(wK2.dropna().iloc[-1]), 1)
        cur_dK1 = round(float(dK1.dropna().iloc[-1]), 1)
        cur_dK2 = round(float(dK2.dropna().iloc[-1]), 1)
        cur_dK3 = round(float(dK3.dropna().iloc[-1]), 1)

        # 판정
        if w_bearish:
            verdict = "warn"
            reason = f"주가 고점 상승 중인데 스토캐스틱 고점이 낮아지고 있어요. 베어리시 다이버전스 — 진입 위험."
        elif w_rising and d_rising and golden:
            verdict = "entry"
            reason = f"주봉 저점 상승 확인 + 일봉 (20,10)·(10,5) 저점 동시 상승 + 골든크로스 발생. 진입 타이밍이에요."
        elif w_rising and d_rising:
            verdict = "wait"
            reason = f"주봉·일봉 저점 상승 패턴 모두 확인됐어요. 골든크로스 나오는 시점 기다리면 돼요."
        elif w_rising:
            verdict = "wait"
            reason = f"주봉 저점 상승 패턴 보여요. 일봉에서도 패턴 형성되면 진입 검토하세요."
        else:
            verdict = "none"
            reason = f"아직 주봉·일봉 모두 패턴 미형성이에요."

        return {
            "name": name,
            "market": market,
            "ticker": ticker,
            "price": current_price,
            "verdict": verdict,
            "reason": reason,
            "w_rising": w_rising,
            "d_rising": d_rising,
            "golden": golden,
            "bearish": w_bearish,
            "wK1": cur_wK1,
            "wK2": cur_wK2,
            "dK1": cur_dK1,
            "dK2": cur_dK2,
            "dK3": cur_dK3,
        }
    except Exception as e:
        return None

@app.get("/scan")
def scan():
    results = []
    for ticker, name, market in STOCKS:
        r = analyze(ticker, name, market)
        if r:
            results.append(r)

    order = {"entry": 0, "wait": 1, "none": 2, "warn": 3}
    results.sort(key=lambda x: order.get(x["verdict"], 4))
    return {"results": results, "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M")}

@app.get("/")
def root():
    return {"status": "ok", "message": "소연 스캐너 서버 실행 중"}
