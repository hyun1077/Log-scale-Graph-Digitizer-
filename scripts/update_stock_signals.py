import json, math, statistics, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

WATCHLIST = ['NVDA','SMR','IONQ','SOXL','GOOGL','MSFT']
OUT = Path('log-digitizer-vite/public/capital-flow/stocks.json')

def get_chart(ticker):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}?range=1y&interval=1d&events=history'
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        obj = json.load(r)['chart']['result'][0]
    q = obj['indicators']['quote'][0]
    adj = obj['indicators'].get('adjclose',[{'adjclose':q['close']}])[0]['adjclose']
    rows=[]
    for ts,c,v in zip(obj['timestamp'],adj,q['volume']):
        if c is not None:
            rows.append((ts,float(c),float(v or 0)))
    return rows

def rss_news(ticker, limit=5):
    q = urllib.parse.quote(f'{ticker} stock when:7d')
    url = f'https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en'
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=20) as r:
            root=ET.fromstring(r.read())
        out=[]
        for item in root.findall('.//item')[:limit]:
            out.append({'title':item.findtext('title','').strip(),'link':item.findtext('link','').strip(),'published':item.findtext('pubDate','').strip()})
        return out
    except Exception:
        return []

def ma(xs,n): return sum(xs[-n:])/n if len(xs)>=n else None

def pct(a,b): return (a/b-1)*100 if b else 0

spy = get_chart('SPY')
spy_prices=[x[1] for x in spy]
spy20=pct(spy_prices[-1],spy_prices[-21]) if len(spy_prices)>21 else 0

items=[]
for t in WATCHLIST:
    try:
        rows=get_chart(t); prices=[x[1] for x in rows]; vols=[x[2] for x in rows]
        last=prices[-1]; m20=ma(prices,20); m60=ma(prices,60); high52=max(prices[-252:]); v20=ma(vols,20) or 0
        r20=pct(last,prices[-21]) if len(prices)>21 else 0
        conds=[
          {'key':'above_ma20','label':'주가 > 20일선','pass': bool(m20 and last>m20)},
          {'key':'ma20_above_ma60','label':'20일선 > 60일선','pass': bool(m20 and m60 and m20>m60)},
          {'key':'near_52w_high','label':'52주 고점 대비 -10% 이내','pass': last>=high52*0.90},
          {'key':'relative_strength','label':'20일 수익률 > S&P500','pass': r20>spy20},
          {'key':'volume','label':'거래량 > 20일 평균','pass': bool(v20 and vols[-1]>v20)},
        ]
        passed=sum(1 for c in conds if c['pass'])
        items.append({'ticker':t,'price':round(last,2),'ma20':round(m20,2) if m20 else None,'ma60':round(m60,2) if m60 else None,
          'high52':round(high52,2),'return20':round(r20,2),'spyReturn20':round(spy20,2),'volumeRatio':round(vols[-1]/v20,2) if v20 else None,
          'conditions':conds,'passed':passed,'total':len(conds),'signal':'strong' if passed>=4 else ('watch' if passed>=3 else 'weak'),'news':rss_news(t)})
    except Exception as e:
        items.append({'ticker':t,'error':str(e),'conditions':[],'passed':0,'total':5,'signal':'error','news':[]})

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({'updatedAt':datetime.now(timezone.utc).isoformat(),'items':items},ensure_ascii=False,indent=2),encoding='utf-8')
print('updated',OUT)
