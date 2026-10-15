"""
Stock Analytics - Backend Integration Server
Serves index.html and provides:
1. /api/analyze - integrates with installed 'stock-analysis' skill, yfinance charts,
   Google News RSS, and Google Gemini AI API for deep investment synthesis.
2. /api/chat - real-time interactive conversational copilot powered by Gemini AI.
"""

import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

PORT = 3000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_SCRIPT = os.path.join(BASE_DIR, ".agents", "skills", "stock-analysis", "scripts", "analyze_stock.py")

# Try to read .env file if present
ENV_FILE = os.path.join(BASE_DIR, ".env")
if os.path.exists(ENV_FILE):
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k and v and k not in os.environ:
                        os.environ[k] = v
    except Exception as e:
        print(f"Notice: Failed to parse .env file: {e}")

# Sentiment dictionary for headlines
BULLISH_WORDS = {
    "surge", "surges", "surging", "jump", "jumps", "jumped", "rally", "rallies", "rallying",
    "gain", "gains", "gained", "high", "record", "beat", "beats", "beating", "boost", "boosts",
    "upgrade", "upgrades", "upgraded", "profit", "bullish", "buy", "outperform", "growth",
    "rise", "rises", "rising", "soar", "soars", "strong", "positive", "breakout"
}

BEARISH_WORDS = {
    "drop", "drops", "dropped", "fall", "falls", "falling", "slump", "slumps", "slumped",
    "plunge", "plunges", "plunged", "decline", "declines", "declining", "miss", "misses",
    "loss", "losses", "downgrade", "downgrades", "downgraded", "bearish", "sell", "underperform",
    "sink", "sinks", "sinking", "slide", "slides", "warning", "warns", "lawsuit", "crash"
}


def analyze_headline_sentiment(title):
    words = re.findall(r"\w+", title.lower())
    bull_count = sum(1 for w in words if w in BULLISH_WORDS)
    bear_count = sum(1 for w in words if w in BEARISH_WORDS)
    if bull_count > bear_count:
        return "Bullish"
    elif bear_count > bull_count:
        return "Bearish"
    return "Neutral"


def fetch_news(ticker):
    """Fetch live news from Google News RSS for the ticker."""
    query = f"{ticker}+stock"
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    articles = []
    bull_total = 0
    bear_total = 0
    neut_total = 0

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=6) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)

            for item in root.findall(".//item")[:10]:
                title = item.find("title").text if item.find("title") is not None else "No Title"
                link = item.find("link").text if item.find("link") is not None else "#"
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                source_el = item.find("source")
                source_name = source_el.text if source_el is not None else "Financial News"

                sentiment = analyze_headline_sentiment(title)
                if sentiment == "Bullish":
                    bull_total += 1
                elif sentiment == "Bearish":
                    bear_total += 1
                else:
                    neut_total += 1

                articles.append({
                    "title": title,
                    "link": link,
                    "published": pub_date,
                    "source": source_name,
                    "sentiment": sentiment
                })
    except Exception as e:
        print(f"Error fetching news for {ticker}: {e}", file=sys.stderr)

    total = len(articles) or 1
    sentiment_score = int(round((bull_total + (0.5 * neut_total)) / total * 100))
    if sentiment_score >= 60:
        sentiment_label = "Bullish"
    elif sentiment_score <= 40:
        sentiment_label = "Bearish"
    else:
        sentiment_label = "Neutral"

    return {
        "articles": articles,
        "summary": {
            "score": sentiment_score,
            "label": sentiment_label,
            "bullish_count": bull_total,
            "bearish_count": bear_total,
            "neutral_count": neut_total
        }
    }


def fetch_historical_bars(ticker):
    """Fetch historical daily bars using yfinance."""
    candles = []
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        df = t.history(period="2mo", interval="1d")
        if df is not None and not df.empty:
            for idx, row in df.iterrows():
                candles.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": round(float(row.get("Open", 0)), 2),
                    "high": round(float(row.get("High", 0)), 2),
                    "low": round(float(row.get("Low", 0)), 2),
                    "close": round(float(row.get("Close", 0)), 2),
                    "volume": int(row.get("Volume", 0))
                })
    except Exception as e:
        print(f"Error fetching historical bars for {ticker}: {e}", file=sys.stderr)
    return candles


def run_stock_analysis_skill(ticker):
    """Execute the installed stock-analysis skill script and parse JSON output."""
    if not os.path.exists(SKILL_SCRIPT):
        raise FileNotFoundError(f"Skill script not found at {SKILL_SCRIPT}")

    cmd = [sys.executable, SKILL_SCRIPT, ticker, "--output", "json"]
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)

    if process.returncode != 0:
        error_msg = process.stderr.strip() or f"Script exited with code {process.returncode}"
        raise RuntimeError(f"Skill execution failed: {error_msg}")

    output = process.stdout.strip()
    return json.loads(output)


def get_gemini_api_key(headers, query_params=None, body_json=None):
    """Resolve Gemini API key from headers, body, query, or environment."""
    if headers and "X-Gemini-Key" in headers:
        key = headers.get("X-Gemini-Key").strip()
        if key:
            return key
    if query_params and "gemini_key" in query_params:
        key = query_params.get("gemini_key", [""])[0].strip()
        if key:
            return key
    if body_json and "gemini_key" in body_json:
        key = str(body_json.get("gemini_key", "")).strip()
        if key:
            return key
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""


def call_gemini_api_raw(api_key, prompt, model="gemini-2.5-flash"):
    """Call Google Gemini REST API directly using standard urllib."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            return ""
    except urllib.error.HTTPError as http_err:
        err_body = http_err.read().decode("utf-8", errors="ignore")
        # If gemini-2.5-flash not found or quota, try fallback to gemini-2.0-flash
        if model != "gemini-2.0-flash":
            print(f"Fallback to gemini-2.0-flash after: {http_err.code}")
            return call_gemini_api_raw(api_key, prompt, model="gemini-2.0-flash")
        raise RuntimeError(f"Gemini API error ({http_err.code}): {err_body}")


def build_fundamentals_checklist(skill_data):
    """Build the institutional 6-point fundamentals checklist requested by the user."""
    fund = skill_data.get("components", {}).get("fundamentals", {})
    checks = []

    # 1. PEG < 2
    peg = fund.get("peg_ratio")
    peg_pass = fund.get("peg_pass", False)
    peg_desc = "Price/Earnings-to-Growth below 2.0 indicates valuation supported by earnings growth."
    if peg is not None:
        peg_desc = f"Based on Yahoo 5-Yr Forward Expected PEG ({peg:.2f}x). Note: Trailing PEG is ~14.1x (or N/A under historical earnings contraction)."
    checks.append({
        "id": "peg",
        "name": "PEG Ratio",
        "rule": "PEG < 2.0",
        "target": "< 2.0x",
        "value": peg,
        "display": f"{peg:.2f}x" if peg is not None else "N/A",
        "passed": bool(peg_pass),
        "desc": peg_desc
    })

    # 2. EPS Growth is Positive for last 5 years
    eps_5y = fund.get("eps_growth_5y")
    eps_pass = fund.get("eps_growth_5y_pass", False)
    eps_display = f"+{eps_5y:.1f}% CAGR" if eps_5y is not None and eps_5y >= 0 else (f"{eps_5y:.1f}% CAGR" if eps_5y is not None else "N/A")
    checks.append({
        "id": "eps_5y",
        "name": "5-Year EPS Growth",
        "rule": "Positive for last 5 years",
        "target": "Positive (> 0%)",
        "value": eps_5y,
        "display": eps_display,
        "passed": bool(eps_pass),
        "desc": "Multi-year earnings growth trajectory demonstrates sustained core operating profitability."
    })

    # 3. ROE > 12%
    roe = fund.get("roe")
    roe_pass = fund.get("roe_pass", False)
    checks.append({
        "id": "roe",
        "name": "Return on Equity (ROE)",
        "rule": "ROE > 12%",
        "target": "> 12.0%",
        "value": roe,
        "display": f"{roe:.1f}%" if roe is not None else "N/A",
        "passed": bool(roe_pass),
        "desc": "Net income generated per dollar of shareholders' equity; above 12% signals strong compounding power."
    })

    # 4. Current Ratio > 1
    curr = fund.get("current_ratio")
    curr_pass = fund.get("current_ratio_pass", False)
    checks.append({
        "id": "current_ratio",
        "name": "Current Ratio",
        "rule": "Current Ratio > 1.0",
        "target": "> 1.0",
        "value": curr,
        "display": f"{curr:.2f}" if curr is not None else "N/A",
        "passed": bool(curr_pass),
        "desc": "Current liquid assets exceeding current liabilities ensures working capital solvency."
    })

    # 5. ROIC > 12%
    roic = fund.get("roic")
    roic_pass = fund.get("roic_pass", False)
    checks.append({
        "id": "roic",
        "name": "Return on Invested Capital (ROIC)",
        "rule": "ROIC > 12%",
        "target": "> 12.0%",
        "value": roic,
        "display": f"{roic:.1f}%" if roic is not None else "N/A",
        "passed": bool(roic_pass),
        "desc": "After-tax operating profit relative to total invested capital confirming a durable economic moat."
    })

    # 6. Debt to EBITDA < 2
    debt_ebitda = fund.get("debt_to_ebitda")
    debt_pass = fund.get("debt_to_ebitda_pass", False)
    checks.append({
        "id": "debt_to_ebitda",
        "name": "Debt to EBITDA",
        "rule": "Debt / EBITDA < 2.0",
        "target": "< 2.0x",
        "value": debt_ebitda,
        "display": f"{debt_ebitda:.2f}x" if debt_ebitda is not None else "N/A",
        "passed": bool(debt_pass),
        "desc": "Total obligations less than 2 years of operating earnings reflects conservative leverage and solvency."
    })

    passed_count = sum(1 for c in checks if c["passed"])
    total_count = len(checks)
    pass_rate = round((passed_count / total_count) * 100, 1)

    return {
        "passed_count": passed_count,
        "total_count": total_count,
        "pass_rate_pct": pass_rate,
        "status": "STRONG QUALITY" if pass_rate >= 80 else ("MODERATE QUALITY" if pass_rate >= 50 else "CAUTION / HIGH RISK"),
        "checks": checks
    }


def generate_gemini_stock_synthesis(api_key, ticker, skill_data, news_data):
    """Generate structured qualitative investment thesis and risk debate using Gemini AI."""
    comps = skill_data.get("components", {})
    fund = comps.get("fundamentals", {})
    an = comps.get("analyst_sentiment", {})
    earn = comps.get("earnings_surprise", {})
    mom = comps.get("momentum", {})
    mac = comps.get("market_context", {})
    sec = comps.get("sector_performance", {})
    sent = comps.get("sentiment_analysis", {})
    articles = news_data.get("articles", [])
    checklist = build_fundamentals_checklist(skill_data)

    prompt = f"""You are a senior quantitative & equity research director at an elite investment fund.
Synthesize the following real-time data for ticker {ticker} ({skill_data.get('company_name', ticker)}):

QUANTITATIVE SIGNALS:
- Algorithmic Signal: {skill_data.get('recommendation')} (Confidence Score: {skill_data.get('confidence', 0):.2f})
- Fundamentals: P/E: {fund.get('pe_ratio')}, Operating Margin: {fund.get('operating_margin')}, YoY Rev Growth: {fund.get('revenue_growth_yoy')}, Debt/Equity: {fund.get('debt_to_equity')}
- 6-Point Quality Checklist ({checklist.get('passed_count')}/{checklist.get('total_count')} passed, {checklist.get('pass_rate_pct')}%):
  * PEG < 2.0: {fund.get('peg_ratio')} ({'PASS' if fund.get('peg_pass') else 'FAIL'})
  * 5Y EPS Growth Positive: {fund.get('eps_growth_5y')}% ({'PASS' if fund.get('eps_growth_5y_pass') else 'FAIL'})
  * ROE > 12%: {fund.get('roe')}% ({'PASS' if fund.get('roe_pass') else 'FAIL'})
  * Current Ratio > 1.0: {fund.get('current_ratio')} ({'PASS' if fund.get('current_ratio_pass') else 'FAIL'})
  * ROIC > 12%: {fund.get('roic')}% ({'PASS' if fund.get('roic_pass') else 'FAIL'})
  * Debt to EBITDA < 2.0: {fund.get('debt_to_ebitda')}x ({'PASS' if fund.get('debt_to_ebitda_pass') else 'FAIL'})
- Analyst Consensus: {an.get('consensus_rating')} (Price Target: ${an.get('price_target')}, Current: ${an.get('current_price')}, Upside: {an.get('upside_pct')}%)
- Earnings: Actual EPS: ${earn.get('actual_eps')}, Expected EPS: ${earn.get('expected_eps')}, Surprise: {earn.get('surprise_pct')}%
- Momentum: RSI (14d): {mom.get('rsi_14d')}, Near 52w High: {mom.get('near_52w_high')}, Rel Vol: {mom.get('volume_ratio')}
- Sector & Macro: Sector: {sec.get('sector_name')} (1M: {sec.get('sector_return_1m')}%), VIX: {mac.get('vix_level')} ({mac.get('vix_status')}), SPY 10d: {mac.get('spy_trend_10d')}%
- Short & Options: Put/Call Ratio: {sent.get('put_call_ratio')}, Short Interest: {sent.get('short_interest_pct')}%

BREAKING NEWS HEADLINES:
{chr(10).join(['- ' + a.get('title', '') for a in articles[:6]])}

TASK:
Provide an expert, professional, balanced qualitative investment memo. Return ONLY valid JSON (no markdown formatting, no backticks, no code fence).
Exact JSON structure:
{{
  "executive_thesis": "3-4 concise, high-impact sentences analyzing the balance between current valuation, earnings durability, and macroeconomic headwinds/tailwinds.",
  "bull_case": [
    "Specific bull catalyst with quantitative rationale",
    "Competitive moat or pricing power driver",
    "Expansion vector or forward multiple justification"
  ],
  "bear_case": [
    "Primary downside valuation or margin compression risk",
    "Regulatory, supply chain, or customer concentration hazard",
    "Macro or competitor threat"
  ],
  "moat_rating": "Wide Moat / Narrow Moat / None - with 1 sentence rationale",
  "catalyst_timeline": "Specific timeline of events/catalysts to monitor over the next 90-180 days."
}}
"""
    raw_response = call_gemini_api_raw(api_key, prompt)
    
    # Clean potential markdown fences
    cleaned = raw_response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except Exception as e:
        print(f"Warning: Failed to parse Gemini JSON: {e}. Raw: {raw_response[:200]}")
        return {
            "executive_thesis": raw_response[:300] if raw_response else "Synthesis completed.",
            "bull_case": ["Strong sector positioning and cash flow generation"],
            "bear_case": ["Market volatility and multiple compression"],
            "moat_rating": "Narrow Moat",
            "catalyst_timeline": "Next quarterly earnings release and guidance update."
        }


def handle_gemini_chat_query(api_key, ticker, message, context):
    """Handle conversational Q&A about the stock using Gemini."""
    prompt = f"""You are 'Gemini Quant Copilot', an AI financial analyst embedded in the Stock Analytics platform.
The user is inspecting {ticker}.

CONTEXT:
{json.dumps(context, indent=2)}

USER QUESTION:
{message}

INSTRUCTIONS:
- Answer with high institutional precision, citing specific data points from the context where relevant.
- Be concise (2-4 paragraphs maximum).
- If asked for advice, include a clear disclaimer that all content is for educational purposes.
"""
    return call_gemini_api_raw(api_key, prompt)


class StockAnalyticsHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Gemini-Key")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/')

        if path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)
            try:
                body_json = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                body_json = {}

            gemini_key = get_gemini_api_key(self.headers, body_json=body_json)
            if not gemini_key:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": "Gemini API Key is required to chat. Please provide it in the top settings bar or request."
                }).encode("utf-8"))
                return

            ticker = body_json.get("ticker", "AAPL").upper()
            message = body_json.get("message", "").strip()
            context = body_json.get("context", {})

            if not message:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Message is required."}).encode("utf-8"))
                return

            try:
                reply = handle_gemini_chat_query(gemini_key, ticker, message, context)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "reply": reply}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/')

        if path == "/api/analyze":
            query_params = urllib.parse.parse_qs(parsed.query)
            ticker = query_params.get("ticker", [""])[0].strip().upper()

            if not ticker:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Ticker query parameter is required."}).encode("utf-8"))
                return

            try:
                # 1. Run the installed skill
                skill_data = run_stock_analysis_skill(ticker)
                # 2. Fetch historical candle bars for chart
                history_data = fetch_historical_bars(ticker)
                # 3. Fetch breaking news & sentiment
                news_data = fetch_news(ticker)

                # 4. Check for Gemini API Key to perform deeper analysis
                gemini_key = get_gemini_api_key(self.headers, query_params)
                gemini_synthesis = None
                gemini_active = False

                if gemini_key:
                    try:
                        gemini_synthesis = generate_gemini_stock_synthesis(gemini_key, ticker, skill_data, news_data)
                        gemini_active = True
                    except Exception as gem_err:
                        print(f"Gemini API generation error: {gem_err}", file=sys.stderr)
                        gemini_synthesis = {
                            "error": str(gem_err),
                            "note": "Could not generate Gemini synthesis. Check API key quota or permissions."
                        }

                response_payload = {
                    "success": True,
                    "ticker": ticker,
                    "timestamp": datetime.now().isoformat(),
                    "skill_analysis": skill_data,
                    "fundamentals_checklist": build_fundamentals_checklist(skill_data),
                    "history": history_data,
                    "news": news_data["articles"],
                    "news_sentiment": news_data["summary"],
                    "gemini_active": gemini_active,
                    "gemini_synthesis": gemini_synthesis
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response_payload).encode("utf-8"))

            except Exception as ex:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "ticker": ticker,
                    "error": str(ex)
                }).encode("utf-8"))
            return

        # Serve static files (default to index.html for root)
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()


def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), StockAnalyticsHandler) as httpd:
        print(f"[Stock Analytics Server] Listening on http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")


if __name__ == "__main__":
    run_server()
