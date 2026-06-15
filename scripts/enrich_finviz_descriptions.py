import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from tqdm import tqdm
import sys

# ====================== CONFIG (GitHub Actions friendly) ======================
INPUT_FILE = os.getenv("INPUT_FILE", "data/finviz.csv")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "data/finviz_with_descriptions.csv")
CHECKPOINT_EVERY = 100
DELAY = 1.3
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FinvizEnrichBot/1.0)"}

def get_finviz_description(ticker: str) -> str:
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return f"HTTP {resp.status_code}"
        
        soup = BeautifulSoup(resp.text, "lxml")
        
        # Finviz description is usually in one of these locations
        candidates = []
        
        # Method 1: Look for long text in snapshot table cells
        for td in soup.find_all("td", class_="snapshot-td2-cp"):
            text = td.get_text(" ", strip=True)
            if len(text) > 100:
                candidates.append(text)
        
        # Method 2: Main profile area
        profile = soup.find("div", {"id": "quote-profile"})
        if profile:
            candidates.append(profile.get_text(" ", strip=True))
        
        # Pick the longest reasonable candidate
        for text in sorted(candidates, key=len, reverse=True):
            if len(text) > 80 and any(word in text.lower() for word in ["provides", "engages", "operates", "develops", "manufactures", "offers"]):
                return text[:1200]  # cap length
        
        return "Description not found"
        
    except Exception as e:
        return f"Error: {str(e)[:100]}"

# ====================== MAIN ======================
print("=== Finviz Description Enricher (GitHub Actions) ===")
print(f"Input:  {INPUT_FILE}")
print(f"Output: {OUTPUT_FILE}")

if not os.path.exists(INPUT_FILE):
    print(f"ERROR: {INPUT_FILE} not found!")
    sys.exit(1)

df = pd.read_csv(INPUT_FILE, low_memory=False)

# Filter ETFs
etf_mask = df["ETF Type"].notna() | (df.get("Asset Type", "") == "Exchange Traded Fund")
stocks_df = df[~etf_mask].copy()
print(f"Total rows: {len(df)} | Stocks to process: {len(stocks_df)} | ETFs excluded: {etf_mask.sum()}")

if "Finviz_Business_Description" not in stocks_df.columns:
    stocks_df["Finviz_Business_Description"] = ""

to_process = stocks_df[stocks_df["Finviz_Business_Description"].str.len() < 20]
print(f"Need to fetch: {len(to_process)} descriptions\n")

success = 0
for i, (idx, row) in enumerate(tqdm(to_process.iterrows(), total=len(to_process), desc="Fetching")):
    ticker = str(row["Ticker"]).strip()
    if not ticker or ticker == "nan":
        continue
    
    desc = get_finviz_description(ticker)
    stocks_df.at[idx, "Finviz_Business_Description"] = desc
    success += 1
    
    if (i + 1) % CHECKPOINT_EVERY == 0:
        stocks_df.to_csv(OUTPUT_FILE, index=False)
        print(f"Checkpoint saved ({i+1}/{len(to_process)})")

# Final save
stocks_df.to_csv(OUTPUT_FILE, index=False)
print(f"\n✅ Done! Enriched file saved to: {OUTPUT_FILE}")
print(f"Successfully processed: {success} tickers")
