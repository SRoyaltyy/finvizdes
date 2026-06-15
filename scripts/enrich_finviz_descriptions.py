import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from tqdm import tqdm
import sys

INPUT_FILE = "finviz.csv"
OUTPUT_FILE = "finviz_with_descriptions.csv"
CHECKPOINT_EVERY = 50          # Save more frequently
DELAY = 2.0                    # Increased delay to reduce blocking
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def get_short_description(ticker: str) -> str:
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return f"HTTP_{resp.status_code}"
        
        soup = BeautifulSoup(resp.text, "lxml")
        
        # Try to get the main description text
        text = ""
        for td in soup.find_all("td", class_="snapshot-td2-cp"):
            t = td.get_text(" ", strip=True)
            if len(t) > 80:
                text = t
                break
        
        if not text:
            profile = soup.find("div", {"id": "quote-profile"})
            if profile:
                text = profile.get_text(" ", strip=True)
        
        # Return a clean snippet
        if text:
            return text[:350].strip() + "..."
        else:
            return "No description found"
            
    except Exception as e:
        return f"Error: {str(e)[:80]}"

# ====================== MAIN ======================
print("=== Finviz Short Description Scraper ===")

if not os.path.exists(INPUT_FILE):
    print(f"ERROR: {INPUT_FILE} not found!")
    sys.exit(1)

df = pd.read_csv(INPUT_FILE, low_memory=False)

# Filter ETFs
etf_mask = df["ETF Type"].notna() | (df.get("Asset Type", "") == "Exchange Traded Fund")
stocks_df = df[~etf_mask].copy()

if "Finviz_Description_Snippet" not in stocks_df.columns:
    stocks_df["Finviz_Description_Snippet"] = ""

to_process = stocks_df[stocks_df["Finviz_Description_Snippet"].str.len() < 10]
print(f"Total stocks: {len(stocks_df)} | Remaining to process: {len(to_process)}")

for i, (idx, row) in enumerate(tqdm(to_process.iterrows(), total=len(to_process))):
    ticker = str(row["Ticker"]).strip()
    if not ticker:
        continue

    snippet = get_short_description(ticker)
    stocks_df.at[idx, "Finviz_Description_Snippet"] = snippet

    if (i + 1) % CHECKPOINT_EVERY == 0:
        stocks_df.to_csv(OUTPUT_FILE, index=False)
        print(f"Progress saved at {i+1}/{len(to_process)}")

stocks_df.to_csv(OUTPUT_FILE, index=False)
print(f"\n✅ Finished! Output saved to: {OUTPUT_FILE}")
