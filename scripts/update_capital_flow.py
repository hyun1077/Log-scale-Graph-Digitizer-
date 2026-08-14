from __future__ import annotations
import csv, io, json, urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path('log-digitizer-vite/public/capital-flow/data.json')
SERIES = {
    'fedAssetsB': 'WALCL',
    'reservesB': 'WRESBAL',
    'tgaB': 'WTREGEN',
    'rrpOthersB': 'RRPONTSYD',
}

def observations(series):
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}'
    req = urllib.request.Request(url, headers={'User-Agent':'capital-flow-dashboard/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        text = r.read().decode('utf-8')
    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        raw = row.get(series, '')
        if raw not in ('', '.'):
            rows.append((row['DATE'], float(raw)))
    return rows

def latest_pair(series):
    rows = observations(series)
    return rows[-1], rows[-2]

data = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}
dates=[]
for key, series in SERIES.items():
    (date, value), (_, previous) = latest_pair(series)
    dates.append(date)
    # WALCL/WRESBAL/WTREGEN are millions USD; RRPONTSYD is billions USD.
    if series in ('WALCL','WRESBAL','WTREGEN'):
        value /= 1000.0
        previous /= 1000.0
    data[key] = round(value, 3)
    if key != 'rrpOthersB':
        data[key.replace('B','DeltaB')] = round(value-previous, 3)

data['asOf'] = max(dates)
data['updatedAt'] = datetime.now(timezone.utc).isoformat()

# Transparent mechanical liquidity sub-score. Investment/conditions remain separate model layers.
# Weekly changes are scaled and clipped so one indicator cannot dominate the score.
def clip(x, lo=-2, hi=2): return max(lo, min(hi, x))
asset = clip(data.get('fedAssetsDeltaB',0)/50)
reserve = clip(data.get('reservesDeltaB',0)/50)
tga = clip(-data.get('tgaDeltaB',0)/50)
rrp_buffer = -0.25 if data.get('rrpOthersB',0) < 20 else 0
financial = clip(0.25*asset + 0.35*reserve + 0.35*tga + rrp_buffer)
data['financialLiquidityScore'] = round(financial,2)
inv = float(data.get('investmentFlowScore',0))
cond = float(data.get('financialConditionsScore',0))
data['capitalFlowScore'] = round(clip(0.45*financial + 0.35*inv + 0.20*cond),2)
data['note'] = 'Fed/FRED values update automatically. Investment Flow and Financial Conditions are separate model layers.'
OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(data, ensure_ascii=False, indent=2))
