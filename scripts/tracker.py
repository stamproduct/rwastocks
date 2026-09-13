import csv
import json
import os
import requests
from datetime import datetime, timezone

HEADERS = {"User-Agent": "Mozilla/5.0"}


def load_config(path="data/tokens.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_stock_price(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    data = requests.get(url, headers=HEADERS, timeout=15).json()
    return data["chart"]["result"][0]["meta"]["regularMarketPrice"]


def gate_price(pair):
    url = f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={pair}"
    r = requests.get(url, headers=HEADERS, timeout=15).json()
    if not r:
        return None
    t = r[0]
    return {"last": float(t["last"]), "bid": float(t["highest_bid"]),
            "ask": float(t["lowest_ask"]), "vol_usdt": float(t["quote_volume"])}


def bitget_price(symbol):
    url = f"https://api.bitget.com/api/v2/spot/market/tickers?symbol={symbol}"
    d = requests.get(url, headers=HEADERS, timeout=15).json().get("data", [])
    if not d:
        return None
    t = d[0]
    return {"last": float(t["lastPr"]), "bid": float(t["bidPr"]),
            "ask": float(t["askPr"]), "vol_usdt": float(t.get("quoteVolume", 0))}


def mexc_price(symbol):
    url = f"https://api.mexc.com/api/v3/ticker/24hr?symbol={symbol}"
    r = requests.get(url, headers=HEADERS, timeout=15).json()
    if "lastPrice" not in r:
        return None
    return {"last": float(r["lastPrice"]), "bid": float(r["bidPrice"]),
            "ask": float(r["askPrice"]), "vol_usdt": float(r.get("quoteVolume", 0))}


FETCHERS = {
    "Gate": gate_price,
    "Bitget": bitget_price,
    "MEXC": mexc_price,
}


def calc_spread(bid, ask):
    """买卖价差，百分比。bid/ask 任一为 0 或异常则返回 None"""
    if bid and ask and bid > 0 and ask > 0:
        mid = (bid + ask) / 2
        return round((ask - bid) / mid * 100, 4)
    return None


def append_csv(rows, ts, symbol, underlying, stock_price, nav):
    """把本次所有交易所报价追加到 CSV（不存在则先写表头）"""
    path = "data/history/tracker_log.csv"
    os.makedirs("data/history", exist_ok=True)
    file_exists = os.path.exists(path) and os.path.getsize(path) > 0

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "timestamp", "symbol", "underlying", "stock_price", "nav",
                "exchange", "exchange_symbol", "last", "bid", "ask",
                "premium_pct", "spread_pct", "vol_usdt"
            ])
        for q in rows:
            writer.writerow([
                ts, symbol, underlying, stock_price, nav,
                q["exchange"], q["symbol"], q["last"], q.get("bid"), q.get("ask"),
                q["premium_pct"], q.get("spread_pct"), q["vol_usdt"]
            ])


def main():
    config = load_config()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    all_results = []

    for asset in config["assets"]:
        print(f'\n=== {asset["symbol"]} ({asset["underlying"]}) ===')
        stock_price = get_stock_price(asset["underlying"])
        shares_per_token = 1.0          # TODO: 核实 1 token = 1 股
        nav = stock_price * shares_per_token
        print(f"真实股价 ${stock_price}  |  NAV ${nav:.2f}")

        rows = []
        for exch in asset["exchanges"]:
            sym = asset.get("exchange_symbols", {}).get(exch)
            if not sym:
                print(f"  [{exch}] 未配置符号，跳过")
                continue
            try:
                q = FETCHERS[exch](sym)
            except Exception as e:
                print(f"  [{exch}] 请求出错: {e}")
                continue
            if not q:
                print(f"  [{exch}] 无数据（符号可能不对）")
                continue

            premium = (q["last"] - nav) / nav
            spread = calc_spread(q.get("bid"), q.get("ask"))
            q.update({
                "exchange": exch,
                "symbol": sym,
                "premium_pct": round(premium * 100, 4),
                "spread_pct": spread,
            })
            rows.append(q)
            spread_str = f"{spread:.3f}%" if spread is not None else "n/a"
            print(f'  [{exch}] {sym}  last={q["last"]}  '
                  f'premium={premium*100:+.3f}%  spread={spread_str}  '
                  f'vol=${q["vol_usdt"]:,.0f}')

        # 写 CSV（每个资产追加）
        append_csv(rows, ts, asset["symbol"], asset["underlying"], stock_price, round(nav, 4))

        all_results.append({
            "symbol": asset["symbol"],
            "underlying": asset["underlying"],
            "stock_price": stock_price,
            "nav": round(nav, 4),
            "quotes": rows,
        })

    # 写 JSON 快照（保留，方便单次查看）
    os.makedirs("data/history", exist_ok=True)
    with open(f"data/history/{ts}.json", "w", encoding="utf-8") as f:
        json.dump({"timestamp": ts, "results": all_results},
                  f, indent=2, ensure_ascii=False)

    print(f"\n已写入 data/history/{ts}.json")
    print(f"已追加 data/history/tracker_log.csv")


if __name__ == "__main__":
    main()
