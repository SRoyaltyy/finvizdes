import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import sys

INPUT_FILE = "finviz.csv"
OUTPUT_FILE = "finviz_with_descriptions.csv"
DELAY = 1.6
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def get_first_20_words(ticker: str) -> str:
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return f"HTTP_{resp.status_code}"

        soup = BeautifulSoup(resp.text, "lxml")

        # === Correct selector based on your HTML ===
        bio_div = soup.find("div", class_="quote_profile-bio")
        
        if bio_div:
            text = bio_div.get_text(" ", strip=True)
            words = text.split()[:20]
            return " ".join(words) + "..."
        else:
            return "No description found"

    except Exception as e:
        return f"Error: {str(e)[:70]}"

# ====================== MAIN ======================
print("=== Finviz Live Description Scraper ===\n")

if not os.path.exists(INPUT_FILE):
    print(f"ERROR: {INPUT_FILE} not found!")
    sys.exit(1)

df = pd.read_csv(INPUT_FILE, low_memory=False)

# Filter ETFs
etf_mask = df["ETF Type"].notna() | (df.get("Asset Type", "") == "Exchange Traded Fund")
stocks_df = df[~etf_mask].copy()

if "Finviz_Description_Snippet" not in stocks_df.columns:
    stocks_df["Finviz_Description_Snippet"] = ""

to_process = stocks_df[stocks_df["Finviz_Description_Snippet"].str.len() < 5]

print(f"Total stocks to process: {len(to_process)}\n")

for idx, row in to_process.iterrows():
    ticker = str(row["Ticker"]).strip()
    if not ticker:
        continue

    snippet = get_first_20_words(ticker)
    
    # Live output
    print(f"{ticker} | {snippet}", flush=True)

    stocks_df.at[idx, "Finviz_Description_Snippet"] = snippet
    time.sleep(DELAY)

stocks_df.to_csv(OUTPUT_FILE, index=False)
print(f"\n✅ Finished! Saved to: {OUTPUT_FILE}")
