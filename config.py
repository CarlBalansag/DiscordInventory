"""
Configuration management for the Discord Reselling Bot
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Discord Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Google Sheets Configuration
GOOGLE_SCRIPT_URL = os.getenv('GOOGLE_SCRIPT_URL')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE', 'service_account.json')

# Gemini AI Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-pro-latest')

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL')

# Dashboard Configuration
DASHBOARD_BASE_URL = os.getenv('DASHBOARD_BASE_URL', 'http://localhost:10000')

# Google Sheets Column Mapping (Inventory Sheet)
COLUMN_MAPPING = {
    'uuid': 'A',
    'product_name': 'B',
    'date_purchased': 'C',
    'quantity': 'D',
    'store': 'H',
    'links': 'J',
    'cost_per_unit': 'L',
    'tax': 'M',
    'retail_price': 'O'
}

# Sales Sheet Configuration
SALES_SHEET_NAME = 'Sales'
SALES_COLUMN_MAPPING = {
    'product_name': 'B',
    'sold_date': 'C',
    'quantity_sold': 'D',
    'price_per_unit': 'F',
    'shipping_cost': 'H'
}

# Store dropdown options
STORE_OPTIONS = [
    'Amazon',
    'Walmart',
    'Target',
    'Best Buy',
    'Costco',
    'Pokemon Store',
    'Other'
]

# Validate required environment variables
def validate_config():
    """Check if all required environment variables are set"""
    errors = []

    if not DISCORD_TOKEN:
        errors.append("DISCORD_TOKEN is not set in .env file")

    if not GOOGLE_SCRIPT_URL:
        errors.append("GOOGLE_SCRIPT_URL is not set in .env file")

    if not DATABASE_URL:
        errors.append("DATABASE_URL is not set in .env file")

    if not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY is not set in .env file")

    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        errors.append(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")

    if errors:
        raise ValueError("Configuration errors:\n" + "\n".join(f"- {e}" for e in errors))

    return True
