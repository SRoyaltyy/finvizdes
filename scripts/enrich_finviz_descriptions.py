import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from tqdm import tqdm
import sys

# ====================== CONFIG (Root level) ======================
INPUT_FILE = "finviz.csv"
OUTPUT_FILE = "finviz_with_descriptions.csv"
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
        
        candidates = []
        for td in soup.find_all("td", class_="snapshot-td2-cp"):
            text = td.get_text(" ", strip=True)
            if len(text) > 100:
                candidates.append(text)
        
        profile = soup.find("div", {"id": "quote-profile"})
        if profile:
            candidates.append(profile.get_text(" ", strip=True))
        
        for text in sorted(candidates, key=len, reverse=True):
            if len(text) > 80 and any(word in text.lower() for word in ["provides", "engages", "operates", "develops", "manufactures", "offers"]):
                return text[:1200]
        
        return "Description not found"
        
    except Exception as e:
        return f"Error: {str(e)[:100]}"

# ====================== MAIN ======================
print("=== Finviz Description Enricher ===")
print(f"Looking for: {INPUT_FILE}")

if not os.path.exists(INPUT_FILE):
    print(f"ERROR: {INPUT_FILE} not found in root!")
    sys.exit(1)

df = pd.read_csv(INPUT_FILE, low_memory=False)

# Filter out ETFs
etf_mask = df["ETF Type"].notna() | (df.get("Asset Type", "") == "Exchange Traded Fund")
stocks_df = df[~etf_mask].copy()
print(f"Total rows: {len(df)} | Processing {len(stocks_df)} stocks")

if "Finviz_Business_Description" not in stocks_df.columns:
    stocks_df["Finviz_Business_Description"] = ""

to_process = stocks_df[stocks_df["Finviz_Business_Description"].str.len() < 20]
print(f"Need to fetch: {len(to_process)} descriptions\n")

for i, (idx, row) in enumerate(tqdm(to_process.iterrows(), total=len(to_process))):
    ticker = str(row["Ticker"]).strip()
    if not ticker or ticker == "nan":
        continue
    
    desc = get_finviz_description(ticker)
    stocks_df.at[idx, "Finviz_Business_Description"] = desc
    
    if (i + 1) % CHECKPOINT_EVERY == 0:
        stocks_df.to_csv(OUTPUT_FILE, index=False)
        print(f"Checkpoint saved at {i+1}")

stocks_df.to_csv(OUTPUT_FILE, index=False)
print(f"\n✅ Done! Output saved as: {OUTPUT_FILE}")
