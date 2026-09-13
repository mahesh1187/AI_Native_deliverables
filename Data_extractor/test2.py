import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import os

def extract_fund_data(fund_url):
    # Standard User-Agent to prevent getting blocked by the server
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    try:
        print(f"Fetching data from Advisorkhoj...")
        response = requests.get(fund_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Extract the Fund Name
        h1_tag = soup.find('h1')
        fund_name = h1_tag.text.strip() if h1_tag else "Unknown_Mutual_Fund"
        
        safe_filename = re.sub(r'[\\/*?:"<>|]', "", fund_name).replace(" ", "_")
        excel_filename = f"{safe_filename}.xlsx"
        
        # 2. Extract Latest NAV cleanly (FIXED LOGIC)
        latest_nav = "N/A"
        
        # Search specifically for the label "NAV as on" to avoid table headers
        nav_label = soup.find(string=re.compile(r'NAV as on', re.IGNORECASE))
        
        if nav_label:
            # Get the text of the parent element (in case the number is in the same tag)
            parent_text = nav_label.parent.text.strip()
            
            # Find all decimal numbers in this block of text (e.g., 14.057)
            # This regex avoids matching dates like 24-05-2024 by ensuring no dashes are attached
            matches = re.findall(r'(?<!-)\b\d+\.\d+\b(?!-)', parent_text)
            
            if matches:
                latest_nav = matches[-1] # Usually the last decimal in the string is the NAV
            else:
                # If not found in the same tag, check the next adjacent HTML tag
                next_tag = nav_label.parent.find_next_sibling()
                if next_tag:
                    match_sibling = re.search(r'\d+\.\d+', next_tag.text)
                    if match_sibling:
                        latest_nav = match_sibling.group(0)

        # 3. Parse the tables to find the Dividend History
        tables = pd.read_html(response.text)
        dividend_df = None
        
        for table in tables:
            # Identify the table by checking if it has a typical dividend column header
            if 'Dividend Record Date' in table.columns or 'Record Date' in table.columns:
                # Drop rows where the first column is empty (cleans up website pagination text)
                dividend_df = table.dropna(subset=[table.columns[0]]).copy()
                break
                
        if dividend_df is None or dividend_df.empty:
            print("Could not find the dividend table on this page.")
            return None
            
        # 4. Add the Latest NAV and Fund Name to every row
        dividend_df['Fund Name'] = fund_name
        dividend_df['Latest NAV'] = latest_nav
        
        # Reorder the columns to place 'Fund Name' and 'Latest NAV' at the front
        cols = dividend_df.columns.tolist()
        cols = ['Fund Name', 'Latest NAV'] + [c for c in cols if c not in ['Fund Name', 'Latest NAV']]
        dividend_df = dividend_df[cols]
        
        # 5. Print Output to Terminal
        print("\n" + "="*90)
        print(f"FUND NAME : {fund_name}")
        print(f"LATEST NAV: {latest_nav}")
        print("="*90)
        print("\nDividend History Table with New Columns (Top 5 rows):")
        print(dividend_df.head(5).to_string(index=False)) 
        
        # 6. Save directly to Excel
        dividend_df.to_excel(excel_filename, index=False, sheet_name="IDCW History")
        
        print("\n" + "-"*90)
        print(f"Success! Full data saved to Excel: {os.path.abspath(excel_filename)}")
        print("-" * 90)
        
        return dividend_df

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# --- Execution ---
url = "https://www.advisorkhoj.com/mutual-funds-research/mutual-funds-historical-dividends/Edelweiss%20Aggressive%20Hybrid%20Dir%20IDCW"
df = extract_fund_data(url)