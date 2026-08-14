import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path('log-digitizer-vite/public/capital-flow/investment-flow.json')
DATA = Path('log-digitizer-vite/public/capital-flow/data.json')

UA = {'User-Agent': 'Mozilla/5.0 ThinkingLabCapitalFlow/1.0'}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode('utf-8', errors='ignore')


def has_all(text, words):
    low = re.sub(r'\s+', ' ', text.lower())
    return all(w.lower() in low for w in words)


def clamp(x, lo=-2.0, hi=2.0):
    return max(lo, min(hi, x))


def main():
    reg = json.loads(OUT.read_text(encoding='utf-8'))
    checks = {
        'japan-550': ['550 billion', 'united states'],
        'korea-strategic': ['200 billion', 'strategic investments'],
        'doe-smr': ['800 million', 'tva', 'holtec'],
        'doe-uranium': ['2.7 billion', 'uranium'],
        'nvidia-compute-finance': ['500 billion', 'nvidia'],
        'hyperscaler-capex': ['730 billion', 'big tech']
    }

    for item in reg['items']:
        try:
            body = fetch(item['url'])
            item['verified'] = has_all(body, checks.get(item['id'], []))
            item['lastChecked'] = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            item['verified'] = False
            item['lastChecked'] = datetime.now(timezone.utc).isoformat()
            item['checkError'] = str(e)[:180]

    # Directional category scores. Amounts are logarithmically damped and discounted by stage,
    # so a $500B announcement never acts like $500B of QE.
    cats = {}
    for item in reg['items']:
        if not item.get('verified'):
            continue
        amount = max(float(item.get('amountB', 0)), 0.001)
        stage = float(item.get('weight', 0.1))
        contribution = stage * min(1.0, (amount / 100.0) ** 0.35)
        cats.setdefault(item['category'], 0.0)
        cats[item['category']] += contribution

    category_scores = {
        'Private Credit': clamp(cats.get('Private Credit', 0) * 1.8),
        'Foreign Investment': clamp(cats.get('Foreign Investment', 0) * 1.45),
        'Hyperscaler CAPEX': clamp(cats.get('Hyperscaler CAPEX', 0) * 1.6),
        'Federal Policy': clamp(cats.get('Federal Policy', 0) * 1.8),
    }
    inv = clamp(
        category_scores['Private Credit'] * 0.30 +
        category_scores['Foreign Investment'] * 0.25 +
        category_scores['Hyperscaler CAPEX'] * 0.30 +
        category_scores['Federal Policy'] * 0.15
    )
    reg['categoryScores'] = {k: round(v, 2) for k, v in category_scores.items()}
    reg['investmentFlowScore'] = round(inv, 2)
    reg['updatedAt'] = datetime.now(timezone.utc).isoformat()
    OUT.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    if DATA.exists():
        d = json.loads(DATA.read_text(encoding='utf-8'))
        d['investmentFlowScore'] = reg['investmentFlowScore']
        fin = float(d.get('financialLiquidityScore', 0))
        cond = float(d.get('financialConditionsScore', 0))
        # Keep monetary liquidity, investment flow, and financial conditions distinct,
        # then combine only at the headline layer.
        d['capitalFlowScore'] = round(clamp(fin * 0.45 + inv * 0.35 + cond * 0.20), 2)
        d['investmentUpdatedAt'] = reg['updatedAt']
        DATA.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
