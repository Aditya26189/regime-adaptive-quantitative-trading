from fyers_apiv3 import fyersModel
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# ============================================
# CONFIGURATION
# ============================================
CLIENT_ID = "PLE8T7ZKRQ-100"

try:
    with open("access_token.txt", "r") as f:
        ACCESS_TOKEN = f.read().strip()
except FileNotFoundError:
    ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiZDoxIiwiZDoyIiwieDowIiwieDoxIiwieDoyIl0sImF0X2hhc2giOiJnQUFBQUFCcGFTZGJ5ZXpCbFpVY19OSDFvVl9ZMWZrOEpTWGd4aHlYeHdJRVRady00M2RVUy01Q3V2Y3dmUW9YUlJXLU9taGgtc0dRcEkxLXBPb1pHeUVFWHluQl90MDV4Y3lucVRUN0tNSHZEeEdaZm9UWjBvaz0iLCJkaXNwbGF5X25hbWUiOiIiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiI5ZjViM2Q2NTQ4N2I4MTJiNDg3NGRhMjdhZjM0NWJiYzI4NWQ5ZjI2OWExMmRlNzU4ZDE5MTgxZCIsImlzRGRwaUVuYWJsZWQiOiJOIiwiaXNNdGZFbmFibGVkIjoiTiIsImZ5X2lkIjoiRkFIOTQ3MjAiLCJhcHBUeXBlIjoxMDAsImV4cCI6MTc2ODUyMzQwMCwiaWF0IjoxNzY4NDk5MDM1LCJpc3MiOiJhcGkuZnllcnMuaW4iLCJuYmYiOjE3Njg0OTkwMzUsInN1YiI6ImFjY2Vzc190b2tlbiJ9.4RNbgFBKkbSCo_lbqZjjQsiXMdIWbND24PfiYwrRHrw"

# ============================================
# HACKATHON PARAMETERS
# ============================================
ALLOWED_SYMBOLS = [
    "NSE:NIFTY50-INDEX",
    "NSE:RELIANCE-EQ",
    "NSE:VBL-EQ",
    "NSE:YESBANK-EQ",
    "NSE:SUNPHARMA-EQ"
]

START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 12, 31)

RESOLUTIONS = {
    "5min": "5",
    "15min": "15", 
    "1hour": "60",
    "1day": "D"
}

# ============================================
# INITIALIZE FYERS
# ============================================
fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=ACCESS_TOKEN, log_path="")
output_dir = "fyers_data"
os.makedirs(output_dir, exist_ok=True)

# ============================================
# HELPER FUNCTION: FETCH DATA IN CHUNKS
# ============================================
def fetch_data_in_chunks(symbol, resolution, start_date, end_date, chunk_days=90):
    """
    Fetch intraday data in chunks (FYERS limits intraday to ~100 days)
    Daily data has no such limit
    """
    all_candles = []
    current_start = start_date
    
    while current_start < end_date:
        # Calculate chunk end date (max 90 days to be safe)
        current_end = min(current_start + timedelta(days=chunk_days), end_date)
        
        data = {
            "symbol": symbol,
            "resolution": resolution,
            "date_format": "1",
            "range_from": current_start.strftime("%Y-%m-%d"),
            "range_to": current_end.strftime("%Y-%m-%d"),
            "cont_flag": "1"
        }
        
        try:
            response = fyers.history(data=data)
            
            if response.get('s') == 'ok' and 'candles' in response:
                candles = response['candles']
                all_candles.extend(candles)
                print(f"  Chunk {current_start.date()} to {current_end.date()}: {len(candles)} candles")
            else:
                error_msg = response.get('message', 'Unknown error')
                print(f"  Chunk {current_start.date()} failed: {error_msg}")
            
            # Rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  Exception: {str(e)}")
        
        # Move to next chunk
        current_start = current_end + timedelta(days=1)
    
    return all_candles

# ============================================
# DOWNLOAD DATA
# ============================================
print("=" * 80)
print("QUANT GAMES HACKATHON - DATA DOWNLOAD (CHUNKED)")
print("=" * 80)
print(f"\nPeriod: {START_DATE.date()} to {END_DATE.date()}")
print(f"Symbols: {len(ALLOWED_SYMBOLS)}")
print(f"Output: {output_dir}/\n")
print("=" * 80)

total_files = len(ALLOWED_SYMBOLS) * len(RESOLUTIONS)
current_file = 0

for symbol in ALLOWED_SYMBOLS:
    for res_name, res_code in RESOLUTIONS.items():
        current_file += 1
        print(f"\n[{current_file}/{total_files}] {symbol} @ {res_name}")
        
        # For daily data, no chunking needed
        if res_code == "D":
            data = {
                "symbol": symbol,
                "resolution": res_code,
                "date_format": "1",
                "range_from": START_DATE.strftime("%Y-%m-%d"),
                "range_to": END_DATE.strftime("%Y-%m-%d"),
                "cont_flag": "1"
            }
            
            try:
                response = fyers.history(data=data)
                
                if response.get('s') == 'ok' and 'candles' in response:
                    all_candles = response['candles']
                else:
                    print(f"  Error: {response.get('message', 'Unknown error')}")
                    continue
                    
            except Exception as e:
                print(f"  Exception: {str(e)}")
                continue
        else:
            # For intraday data, fetch in chunks
            all_candles = fetch_data_in_chunks(symbol, res_code, START_DATE, END_DATE, chunk_days=90)
        
        if all_candles:
            # Convert to DataFrame
            df = pd.DataFrame(all_candles)
            df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            
            # Convert timestamp
            df['datetime'] = pd.to_datetime(df['datetime'], unit='s')
            df['datetime'] = df['datetime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
            
            # Remove duplicates (can happen at chunk boundaries)
            df = df.drop_duplicates(subset=['datetime']).sort_values('datetime')
            
            # Save to CSV
            clean_symbol = symbol.replace(":", "_").replace("-", "_")
            filename = f"{clean_symbol}_{res_name}.csv"
            filepath = os.path.join(output_dir, filename)
            df.to_csv(filepath, index=False)
            
            print(f"  ✓ Saved: {len(df)} total candles → {filename}")
        else:
            print(f"  ✗ No data retrieved")
        
        time.sleep(0.5)

# ============================================
# SUMMARY
# ============================================
print("\n" + "=" * 80)
print("DOWNLOAD COMPLETE!")
print("=" * 80)

csv_files = [f for f in os.listdir(output_dir) if f.endswith('.csv')]
print(f"\nTotal files: {len(csv_files)}")
print(f"Location: {os.path.abspath(output_dir)}/")
print("\n" + "=" * 80)
