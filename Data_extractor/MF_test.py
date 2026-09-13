import pandas as pd
import requests

def scrape_advisorkhoj_dividends(fund_url):
    # Advisorkhoj may block automated scripts, so we use a standard browser User-Agent
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    try:
        # Fetch the webpage
        response = requests.get(fund_url, headers=headers)
        response.raise_for_status() 
        
        # pandas read_html automatically finds all <table> tags in the HTML
        tables = pd.read_html(response.text)
        
        # Advisorkhoj's dividend data is typically in the first main table on the page
        # We can iterate through the tables to find the one with the right columns
        for table in tables:
            if 'Dividend Record Date' in table.columns:
                print("Successfully extracted the IDCW History Table!")
                
                # Clean up the bottom rows if there is pagination text mixed in
                # Sometimes the last row contains "Showing 1 to 25 of 41 entries"
                clean_table = table.dropna(subset=['Dividend Record Date'])
                
                return clean_table
                
        print("Could not find a dividend table on this page. Check the URL.")
        return None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

mflist = ['Bandhan%20Aggressive%20Hyb Fund%20Dir%20IDCW','Edelweiss%20Aggressive%20Hybrid%20Dir%20IDCW','Sundaram%20Aggressive%20Hybrid Fund%20Dir%20Mly%20IDCW']

# --- Execution ---
# Replace this URL with the exact Advisorkhoj URL for your target fund
for mf in mflist:
    print((mf[:6]))
    t = mf[:5]
    url = f"https://www.advisorkhoj.com/mutual-funds-research/mutual-funds-historical-dividends/{mf}"

    df = scrape_advisorkhoj_dividends(url)

    if df is not None:
        print(df.head(10))
    # Optional: Save it to a CSV file for your own database
        df.to_csv(f"advisorkhoj_dividends_{t}.csv", index=False)