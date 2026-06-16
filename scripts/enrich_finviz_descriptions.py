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

def get_description(ticker: str):
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return f"HTTP_{resp.status_code}", f"HTTP_{resp.status_code}"

        soup = BeautifulSoup(resp.text, "lxml")
        bio_div = soup.find("div", class_="quote_profile-bio")

        if bio_div:
            full_text = bio_div.get_text(" ", strip=True)
            # First 20 words for live output
            words = full_text.split()[:20]
            short_snippet = " ".join(words) + "..."
            return full_text, short_snippet
        else:
            return "No description found", "No description found"

    except Exception as e:
        error_msg = f"Error: {str(e)[:70]}"
        return error_msg, error_msg

# ====================== MAIN ======================
print("=== Finviz Description Scraper ===\n")

if not os.path.exists(INPUT_FILE):
    print(f"ERROR: {INPUT_FILE} not found!")
    sys.exit(1)

df = pd.read_csv(INPUT_FILE, low_memory=False)

# Filter ETFs
etf_mask = df["ETF Type"].notna() | (df.get("Asset Type", "") == "Exchange Traded Fund")
stocks_df = df[~etf_mask].copy()

if "Finviz_Description" not in stocks_df.columns:
    stocks_df["Finviz_Description"] = ""

to_process = stocks_df[stocks_df["Finviz_Description"].str.len() < 5]

print(f"Total stocks to process: {len(to_process)}\n")

for idx, row in to_process.iterrows():
    ticker = str(row["Ticker"]).strip()
    if not ticker:
        continue

    full_description, short_snippet = get_description(ticker)

    # === LIVE OUTPUT (only first 20 words) ===
    print(f"{ticker} | {short_snippet}", flush=True)

    # === SAVE FULL DESCRIPTION to CSV ===
    stocks_df.at[idx, "Finviz_Description"] = full_description

    time.sleep(DELAY)

stocks_df.to_csv(OUTPUT_FILE, index=False)
print(f"\n✅ Finished! Full descriptions saved to: {OUTPUT_FILE}")
