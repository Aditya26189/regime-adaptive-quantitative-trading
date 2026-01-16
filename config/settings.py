import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Configuration
STUDENT_ROLL_NUMBER = os.getenv("STUDENT_ROLL_NUMBER", "23ME3EP03")

# Paths
DATA_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "output"
OPTIMIZER_PARAMS_FILE = OUTPUT_DIR / "optimal_params_per_symbol.json"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Symbols Configuration
SYMBOLS_CONFIG = {
    'NIFTY50': {
        'symbol': 'NSE:NIFTY50-INDEX',
        'file': DATA_DIR / 'NSE_NIFTY50_INDEX_1hour.csv',
        'timeframe': '60',
        'type': 'trending'
    },
    'RELIANCE': {
        'symbol': 'NSE:RELIANCE-EQ',
        'file': DATA_DIR / 'NSE_RELIANCE_EQ_1hour.csv',
        'timeframe': '60',
        'type': 'mean_reverting'
    },
    'VBL': {
        'symbol': 'NSE:VBL-EQ',
        'file': DATA_DIR / 'NSE_VBL_EQ_1hour.csv',
        'timeframe': '60',
        'type': 'mean_reverting'
    },
    'YESBANK': {
        'symbol': 'NSE:YESBANK-EQ',
        'file': DATA_DIR / 'NSE_YESBANK_EQ_1hour.csv',
        'timeframe': '60',
        'type': 'trending'
    },
    'SUNPHARMA': {
        'symbol': 'NSE:SUNPHARMA-EQ',
        'file': DATA_DIR / 'NSE_SUNPHARMA_EQ_1hour.csv',
        'timeframe': '60',
        'type': 'mean_reverting'
    }
}
