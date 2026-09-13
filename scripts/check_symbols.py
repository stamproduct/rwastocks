import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}
KEYWORD = "TSLA"

def check_gate():
    print("\n=== Gate ===")
    url = "https://api.gateio.ws/api/v4/spot/currency_pairs"
    for p in requests.get(url, headers=HEADERS, timeout=15).json():
        if KEYWORD in (p["base"] + p["quote"]).upper():
            print(f'  {p["id"]}   (base={p["base"]}, quote={p["quote"]})')

def check_bitget():
    print("\n=== Bitget ===")
    url = "https://api.bitget.com/api/v2/spot/public/symbols"
    for p in requests.get(url, headers=HEADERS, timeout=15).json()["data"]:
        if KEYWORD in (p.get("baseCoin", "") + p.get("quoteCoin", "")).upper():
            print(f'  {p["symbol"]}   (base={p["baseCoin"]}, quote={p["quoteCoin"]})')

def check_mexc():
    print("\n=== MEXC ===")
    url = "https://api.mexc.com/api/v3/exchangeInfo"
    for p in requests.get(url, headers=HEADERS, timeout=15).json()["symbols"]:
        if KEYWORD in (p.get("baseAsset", "") + p.get("quoteAsset", "")).upper():
            print(f'  {p["symbol"]}   (base={p["baseAsset"]}, quote={p["quoteAsset"]})')

if __name__ == "__main__":
    check_gate()
    check_bitget()
    check_mexc()
