"""
Google Sheets API integration
"""
import aiohttp
from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import Dict, Optional
import config

class GoogleSheetsManager:
    """Handles all Google Sheets operations"""

    def __init__(self):
        self.credentials = None
        self.service = None
        self._initialize_credentials()

    def _initialize_credentials(self):
        """Initialize Google Sheets API credentials"""
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                config.SERVICE_ACCOUNT_FILE,
                scopes=SCOPES
            )
            self.service = build('sheets', 'v4', credentials=self.credentials)
        except Exception as e:
            raise Exception(f"Failed to initialize Google Sheets credentials: {e}")

    async def call_apps_script(self, spreadsheet_id: str, sheet_name: str, function_name: str = 'addRowAboveTotalSelective') -> Optional[int]:
        """
        Call the Google Apps Script Web App to create a new row

        Args:
            spreadsheet_id: The Google Spreadsheet ID
            sheet_name: The sheet tab name
            function_name: The Apps Script function to call (default: 'addRowAboveTotalSelective')

        Returns:
            The new row number, or None if failed
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    'spreadsheetId': spreadsheet_id,
                    'sheetName': sheet_name,
                    'functionName': function_name
                }

                async with session.post(config.GOOGLE_SCRIPT_URL, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        # Assuming the script returns {"newRow": <row_number>}
                        return result.get('newRow')
                    else:
                        error_text = await response.text()
                        raise Exception(f"Apps Script error: {error_text}")
        except Exception as e:
            raise Exception(f"Failed to call Apps Script: {e}")

    def write_data_to_row(self, spreadsheet_id: str, sheet_name: str, row_number: int, data: Dict[str, str], column_mapping: Dict[str, str] = None) -> bool:
        """
        Write data to specific cells in a row

        Args:
            spreadsheet_id: The Google Spreadsheet ID
            sheet_name: The sheet tab name
            row_number: The row number to write to
            data: Dictionary mapping field names to values
            column_mapping: Optional column mapping dict (defaults to config.COLUMN_MAPPING)

        Returns:
            True if successful
        """
        try:
            # Use provided column mapping or default to inventory mapping
            if column_mapping is None:
                column_mapping = config.COLUMN_MAPPING

            # Prepare batch update data
            update_data = []

            for field, value in data.items():
                if field in column_mapping and value is not None:
                    column = column_mapping[field]
                    cell_range = f"{sheet_name}!{column}{row_number}"
                    update_data.append({
                        'range': cell_range,
                        'values': [[value]]
                    })

            if not update_data:
                return False

            # Batch update
            body = {
                'valueInputOption': 'USER_ENTERED',
                'data': update_data
            }

            self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()

            return True

        except Exception as e:
            raise Exception(f"Failed to write data to sheet: {e}")

    def verify_sheet_access(self, spreadsheet_id: str, sheet_name: str) -> bool:
        """
        Verify that the bot has access to the spreadsheet and sheet exists

        Args:
            spreadsheet_id: The Google Spreadsheet ID
            sheet_name: The sheet tab name

        Returns:
            True if accessible, raises exception otherwise
        """
        try:
            # Get spreadsheet metadata
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()

            # Check if the sheet exists
            sheets = spreadsheet.get('sheets', [])
            sheet_exists = any(
                sheet['properties']['title'] == sheet_name
                for sheet in sheets
            )

            if not sheet_exists:
                raise Exception(f"Sheet '{sheet_name}' not found in the spreadsheet")

            return True

        except Exception as e:
            if '404' in str(e):
                raise Exception("Spreadsheet not found. Make sure you've shared it with the service account.")
            elif '403' in str(e):
                raise Exception("Permission denied. Please share the spreadsheet with the service account email.")
            else:
                raise Exception(f"Failed to access spreadsheet: {e}")

    def extract_spreadsheet_id(self, url_or_id: str) -> str:
        """
        Extract spreadsheet ID from URL or return ID if already provided

        Args:
            url_or_id: Google Sheets URL or spreadsheet ID

        Returns:
            The spreadsheet ID
        """
        # If it's already an ID (no slashes), return it
        if '/' not in url_or_id:
            return url_or_id

        # Extract from URL
        # Format: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit...
        try:
            if '/d/' in url_or_id:
                parts = url_or_id.split('/d/')
                spreadsheet_id = parts[1].split('/')[0]
                return spreadsheet_id
            else:
                raise ValueError("Invalid Google Sheets URL format")
        except Exception:
            raise ValueError("Could not extract spreadsheet ID from URL")

    def delete_row(self, spreadsheet_id: str, sheet_name: str, row_number: int) -> bool:
        """
        Delete a row from the sheet

        Args:
            spreadsheet_id: The Google Spreadsheet ID
            sheet_name: The sheet tab name
            row_number: The row number to delete

        Returns:
            True if successful
        """
        try:
            # Get the sheet ID (not the same as spreadsheet ID)
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()

            sheet_id = None
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break

            if sheet_id is None:
                raise Exception(f"Sheet '{sheet_name}' not found")

            # Delete the row using batch update
            request = {
                'requests': [
                    {
                        'deleteDimension': {
                            'range': {
                                'sheetId': sheet_id,
                                'dimension': 'ROWS',
                                'startIndex': row_number - 1,  # 0-indexed
                                'endIndex': row_number  # Exclusive
                            }
                        }
                    }
                ]
            }

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=request
            ).execute()

            return True

        except Exception as e:
            raise Exception(f"Failed to delete row: {e}")

    def read_inventory(self, spreadsheet_id: str, sheet_name: str, start_row: int = 8):
        """
        Read inventory data from the sheet

        Args:
            spreadsheet_id: The Google Spreadsheet ID
            sheet_name: The sheet tab name
            start_row: The starting row number (default 8)

        Returns:
            List of inventory items with product name, date, qty available, cost, tax per unit
        """
        try:
            # Get the last row by checking column B (where product names are)
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!B:B"
            ).execute()

            values = result.get('values', [])
            last_row = len(values)

            print(f"DEBUG: Sheet '{sheet_name}' has {last_row} total rows")
            print(f"DEBUG: Reading from row {start_row} to row {last_row - 1}")

            if last_row < start_row:
                print(f"DEBUG: Not enough rows. Last row ({last_row}) < start row ({start_row})")
                return []

            # Read from start_row to last_row - 1 (exclude Total row)
            # Columns: B (product), C (date), D (qty purchased), E (qty available), K (cost), L (tax), R (sold checkbox)
            range_to_read = f"{sheet_name}!B{start_row}:R{last_row - 1}"
            print(f"DEBUG: Reading range: {range_to_read}")

            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_to_read
            ).execute()

            values = result.get('values', [])
            print(f"DEBUG: Got {len(values)} rows of data")

            if values:
                print(f"DEBUG: First row data: {values[0]}")

            inventory_items = []

            for row_index, row in enumerate(values):
                # Pad row with empty strings if needed
                while len(row) < 17:  # B to R = 17 columns
                    row.append('')

                # Column indices (0-based within our read range B:R)
                product_name = row[0]  # B
                date_purchased = row[1]  # C
                qty_purchased = row[2]  # D
                qty_available = row[3]  # E
                cost_per_unit = row[9]  # K (position 9 in B:R range)
                tax_total = row[10]  # L (position 10 in B:R range)
                sold_checkbox = row[16]  # R (position 16 in B:R range)

                print(f"DEBUG: Row {start_row + row_index}: Product='{product_name}', Date='{date_purchased}', Qty Avail='{qty_available}', Sold='{sold_checkbox}'")

                # Skip empty rows (no product name)
                if not product_name or str(product_name).strip() == '':
                    print(f"DEBUG: Skipping row {start_row + row_index} - empty product name")
                    continue

                # Skip sold items (checkbox in column R is TRUE)
                if sold_checkbox and str(sold_checkbox).upper() in ['TRUE', 'YES', '1']:
                    print(f"DEBUG: Skipping row {start_row + row_index} - item is fully sold (checkbox TRUE)")
                    continue

                # Calculate tax per unit
                tax_per_unit = 0.0
                try:
                    if tax_total and qty_purchased:
                        tax_float = float(str(tax_total).replace('$', '').replace(',', ''))
                        qty_float = float(str(qty_purchased).replace(',', ''))
                        if qty_float > 0:
                            tax_per_unit = tax_float / qty_float
                except (ValueError, ZeroDivisionError):
                    tax_per_unit = 0.0

                # Clean up values
                try:
                    cost_clean = float(str(cost_per_unit).replace('$', '').replace(',', '')) if cost_per_unit else 0.0
                except ValueError:
                    cost_clean = 0.0

                try:
                    qty_avail_clean = int(str(qty_available).replace(',', '')) if qty_available else 0
                except ValueError:
                    qty_avail_clean = 0

                inventory_items.append({
                    'product_name': str(product_name).strip(),
                    'date_purchased': str(date_purchased).strip() if date_purchased else '',
                    'qty_available': qty_avail_clean,
                    'cost_per_unit': cost_clean,
                    'tax_per_unit': tax_per_unit,
                    'row_number': start_row + row_index
                })

            print(f"DEBUG: Returning {len(inventory_items)} items")
            return inventory_items

        except Exception as e:
            print(f"DEBUG: Exception occurred: {str(e)}")
            raise Exception(f"Failed to read inventory: {e}")

    def read_sales(self, spreadsheet_id: str, sheet_name: str, start_row: int = 8):
        """
        Read sales data from the sheet

        Args:
            spreadsheet_id: The Google Spreadsheet ID
            sheet_name: The sheet tab name (usually 'Sales')
            start_row: The starting row number (default 8)

        Returns:
            List of sales entries with product name, sold date, quantity, price, shipping
        """
        try:
            # Get the last row by checking column B (where product names are)
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!B:B"
            ).execute()

            values = result.get('values', [])
            last_row = len(values)

            if last_row < start_row:
                return []

            # Read from start_row to last_row - 1 (exclude Total row)
            # Columns: B (product), C (sold date), D (qty sold), F (price per unit), H (shipping cost)
            range_to_read = f"{sheet_name}!B{start_row}:H{last_row - 1}"

            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_to_read
            ).execute()

            values = result.get('values', [])
            sales_items = []

            for row_index, row in enumerate(values):
                # Pad row with empty strings if needed
                while len(row) < 7:  # B to H = 7 columns
                    row.append('')

                # Column indices (0-based within our read range B:H)
                product_name = row[0]  # B
                sold_date = row[1]  # C
                qty_sold = row[2]  # D
                price_per_unit = row[4]  # F (position 4 in B:H range)
                shipping_cost = row[6]  # H (position 6 in B:H range)

                # Skip empty rows (no product name)
                if not product_name or str(product_name).strip() == '':
                    continue

                # Clean up values
                try:
                    price_clean = float(str(price_per_unit).replace('$', '').replace(',', '')) if price_per_unit else 0.0
                except ValueError:
                    price_clean = 0.0

                try:
                    shipping_clean = float(str(shipping_cost).replace('$', '').replace(',', '')) if shipping_cost else 0.0
                except ValueError:
                    shipping_clean = 0.0

                try:
                    qty_clean = int(str(qty_sold).replace(',', '')) if qty_sold else 0
                except ValueError:
                    qty_clean = 0

                sales_items.append({
                    'product_name': str(product_name).strip(),
                    'sold_date': str(sold_date).strip() if sold_date else '',
                    'quantity_sold': qty_clean,
                    'price_per_unit': price_clean,
                    'shipping_cost': shipping_clean,
                    'row_number': start_row + row_index
                })

            return sales_items

        except Exception as e:
            raise Exception(f"Failed to read sales: {e}")
