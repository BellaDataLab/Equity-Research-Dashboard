"""
美股分析網站 - 後端
用法：python app.py
然後開瀏覽器到 http://localhost:5000
"""

from flask import Flask, jsonify, send_from_directory
import yfinance as yf
import pandas as pd
import requests
import os

FINNHUB_KEY = "d7r6o6hr01qtpsm199mgd7r6o6hr01qtpsm199n0"

app = Flask(__name__, static_folder='.')

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/stock/<ticker>')
def get_stock(ticker):
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        if not info or (not info.get("regularMarketPrice") and not info.get("currentPrice")):
            return jsonify({"error": "找不到此股票代碼"}), 404

        price      = info.get("currentPrice") or info.get("regularMarketPrice")
        prev_close = info.get("previousClose") or 0
        change     = price - prev_close if price and prev_close else 0
        change_pct = change / prev_close * 100 if prev_close else 0

        basic = {
            "name":         info.get("longName", ticker.upper()),
            "symbol":       info.get("symbol", ticker.upper()),
            "sector":       info.get("sector", "N/A"),
            "industry":     info.get("industry", "N/A"),
            "website":      info.get("website", ""),
            "description":  (info.get("longBusinessSummary") or "")[:300],
            "employees":    info.get("fullTimeEmployees"),
            "price":        price,
            "prev_close":   prev_close,
            "change":       round(change, 2),
            "change_pct":   round(change_pct, 2),
            "open":         info.get("open"),
            "day_high":     info.get("dayHigh"),
            "day_low":      info.get("dayLow"),
            "week52_high":  info.get("fiftyTwoWeekHigh"),
            "week52_low":   info.get("fiftyTwoWeekLow"),
            "volume":       info.get("volume"),
            "avg_volume":   info.get("averageVolume"),
        }

        fundamentals = {
            "market_cap":       info.get("marketCap"),
            "pe_trailing":      info.get("trailingPE"),
            "pe_forward":       info.get("forwardPE"),
            "pb_ratio":         info.get("priceToBook"),
            "eps_trailing":     info.get("trailingEps"),
            "eps_forward":      info.get("forwardEps"),
            "dividend_yield":   round(info.get("dividendYield", 0) * 100, 2) if info.get("dividendYield") else None,
            "beta":             info.get("beta"),
            "revenue_growth":   round(info.get("revenueGrowth", 0) * 100, 2) if info.get("revenueGrowth") else None,
            "earnings_growth":  round(info.get("earningsGrowth", 0) * 100, 2) if info.get("earningsGrowth") else None,
            "gross_margin":     round(info.get("grossMargins", 0) * 100, 2) if info.get("grossMargins") else None,
            "operating_margin": round(info.get("operatingMargins", 0) * 100, 2) if info.get("operatingMargins") else None,
            "profit_margin":    round(info.get("profitMargins", 0) * 100, 2) if info.get("profitMargins") else None,
            "roe":              round(info.get("returnOnEquity", 0) * 100, 2) if info.get("returnOnEquity") else None,
            "roa":              round(info.get("returnOnAssets", 0) * 100, 2) if info.get("returnOnAssets") else None,
            "target_mean":      info.get("targetMeanPrice"),
            "target_high":      info.get("targetHighPrice"),
            "target_low":       info.get("targetLowPrice"),
            "recommendation":   info.get("recommendationKey", "N/A").upper(),
            "analyst_count":    info.get("numberOfAnalystOpinions"),
        }

        hist = stock.history(period="1y")
        price_history = []
        if not hist.empty:
            for date, row in hist.iterrows():
                price_history.append({
                    "date":   date.strftime("%Y-%m-%d"),
                    "close":  round(float(row["Close"]), 2),
                    "open":   round(float(row["Open"]), 2),
                    "high":   round(float(row["High"]), 2),
                    "low":    round(float(row["Low"]), 2),
                    "volume": int(row["Volume"]),
                })

        income_stmt = []
        try:
            fin = stock.quarterly_financials
            if not fin.empty:
                cols = fin.columns[:4]
                metrics = ["Total Revenue", "Gross Profit", "Operating Income", "Net Income"]
                labels  = ["總營收", "毛利", "營業利益", "淨利"]
                for eng, zh in zip(metrics, labels):
                    if eng in fin.index:
                        row_data = {"label": zh}
                        for c in cols:
                            val = fin.loc[eng, c]
                            row_data[c.strftime("%Y-Q")] = None if pd.isna(val) else int(val)
                        income_stmt.append(row_data)
        except:
            pass

        balance = {}
        try:
            bs = stock.quarterly_balance_sheet
            if not bs.empty:
                latest = bs.columns[0]
                items = {
                    "Total Assets": "總資產",
                    "Total Liabilities Net Minority Interest": "總負債",
                    "Stockholders Equity": "股東權益",
                    "Cash And Cash Equivalents": "現金",
                    "Long Term Debt": "長期負債",
                }
                for eng, zh in items.items():
                    if eng in bs.index:
                        val = bs.loc[eng, latest]
                        balance[zh] = None if pd.isna(val) else int(val)
        except:
            pass

        return jsonify({
            "basic":         basic,
            "fundamentals":  fundamentals,
            "price_history": price_history,
            "income_stmt":   income_stmt,
            "balance":       balance,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/analysts/<ticker>')
def get_analysts(ticker):
    try:
        symbol = ticker.upper()
        stock  = yf.Ticker(symbol)
        info   = stock.info

        rec_trend = []
        try:
            rec = stock.recommendations
            if rec is not None and not rec.empty:
                if 'period' in rec.columns:
                    for _, r in rec.tail(4).iterrows():
                        rec_trend.append({
                            "period":     str(r.get("period", "")),
                            "strongBuy":  int(r.get("strongBuy", 0)),
                            "buy":        int(r.get("buy", 0)),
                            "hold":       int(r.get("hold", 0)),
                            "sell":       int(r.get("sell", 0)),
                            "strongSell": int(r.get("strongSell", 0)),
                        })
        except:
            pass

        price_target = {
            "current": info.get("currentPrice") or info.get("regularMarketPrice"),
            "mean":    info.get("targetMeanPrice"),
            "high":    info.get("targetHighPrice"),
            "low":     info.get("targetLowPrice"),
            "median":  info.get("targetMedianPrice"),
            "count":   info.get("numberOfAnalystOpinions"),
        }

        latest_ratings = []
        try:
            ud = stock.upgrades_downgrades
            if ud is not None and not ud.empty:
                ud = ud.reset_index()
                date_col = 'GradeDate' if 'GradeDate' in ud.columns else ud.columns[0]
                ud = ud.sort_values(date_col, ascending=False)
                for _, r in ud.head(20).iterrows():
                    date_val = r.get(date_col, "")
                    try:
                        date_str = pd.Timestamp(date_val).strftime("%Y-%m-%d")
                    except:
                        date_str = str(date_val)[:10]
                    latest_ratings.append({
                        "date":       date_str,
                        "firm":       str(r.get("Firm", "") or ""),
                        "from_grade": str(r.get("FromGrade", "") or ""),
                        "to_grade":   str(r.get("ToGrade", "") or ""),
                        "action":     str(r.get("Action", "") or ""),
                    })
        except:
            pass

        return jsonify({
            "rec_trend":      rec_trend,
            "price_target":   price_target,
            "latest_ratings": latest_ratings,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("✅ 伺服器啟動中...")
    print("🌐 請開瀏覽器前往：http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)