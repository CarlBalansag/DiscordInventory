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

    def write_formula(self, spreadsheet_id: str, sheet_name: str, cell: str, formula: str) -> bool:
        """
        Write a formula to a specific cell

        Args:
            spreadsheet_id: The Google Spreadsheet ID
            sheet_name: The sheet tab name
            cell: Cell reference (e.g., 'B8')
            formula: Formula to write (e.g., '=HYPERLINK(...)')

        Returns:
            True if successful
        """
        try:
            body = {
                'valueInputOption': 'USER_ENTERED',  # Interprets formulas
                'data': [{
                    'range': f"{sheet_name}!{cell}",
                    'values': [[formula]]
                }]
            }
            self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            return True
        except Exception as e:
            raise Exception(f"Failed to write formula: {e}")

    def read_cell(self, spreadsheet_id: str, sheet_name: str, cell: str) -> str:
        """
        Read a single cell value

        Args:
            spreadsheet_id: The Google Spreadsheet ID
            sheet_name: The sheet tab name
            cell: Cell reference (e.g., 'A8')

        Returns:
            Cell value as string, or empty string if cell is empty
        """
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!{cell}"
            ).execute()
            values = result.get('values', [])
            if values and values[0]:
                return str(values[0][0])
            return ""
        except Exception as e:
            raise Exception(f"Failed to read cell: {e}")

    def set_cell_text_color(self, spreadsheet_id: str, sheet_name: str, cell: str, color: Dict[str, float]) -> bool:
        """
        Set text color for a specific cell

        Args:
            spreadsheet_id: The Google Spreadsheet ID
            sheet_name: The sheet tab name
            cell: Cell reference (e.g., 'A8')
            color: RGB color dict, e.g., {'red': 1.0, 'green': 1.0, 'blue': 1.0} for white

        Returns:
            True if successful
        """
        try:
            # Get sheet ID
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

            # Parse cell reference (e.g., 'A8' -> column 0, row 7)
            import re
            match = re.match(r'([A-Z]+)(\d+)', cell)
            if not match:
                raise Exception(f"Invalid cell reference: {cell}")

            col_letter, row_num = match.groups()
            # Convert column letter to index (A=0, B=1, etc.)
            col_index = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(col_letter))) - 1
            row_index = int(row_num) - 1

            # Update cell format
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': row_index,
                        'endRowIndex': row_index + 1,
                        'startColumnIndex': col_index,
                        'endColumnIndex': col_index + 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {
                                'foregroundColor': color
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.textFormat.foregroundColor'
                }
            }]

            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()

            return True
        except Exception as e:
            raise Exception(f"Failed to set cell text color: {e}")

    def read_product_by_uuid(self, spreadsheet_id: str, sheet_name: str, product_uuid: str, start_row: int = 8):
        """
        Find product by UUID and return all data

        Args:
            spreadsheet_id: The Google Spreadsheet ID
            sheet_name: The sheet tab name
            product_uuid: UUID to search for
            start_row: Starting row number (default 8)

        Returns:
            Product data dict, or None if not found
        """
        try:
            # Read column A to find UUID
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A:A"
            ).execute()

            values = result.get('values', [])

            # Find row with matching UUID
            for row_index, row in enumerate(values[start_row - 1:], start=start_row):
                if row and row[0] == product_uuid:
                    # Found it! Read full row data
                    row_data_result = self.service.spreadsheets().values().get(
                        spreadsheetId=spreadsheet_id,
                        range=f"{sheet_name}!A{row_index}:T{row_index}"
                    ).execute()

                    data = row_data_result.get('values', [[]])[0]

                    # Pad if needed
                    while len(data) < 20:
                        data.append('')

                    # Parse into product dict
                    return {
                        'uuid': data[0],  # A
                        'product_name': data[1],  # B
                        'date_purchased': data[2],  # C
                        'qty_purchased': data[3],  # D
                        'qty_available': data[4],  # E
                        'store': data[7] if len(data) > 7 else '',  # H
                        'links': data[9] if len(data) > 9 else '',  # J
                        'cost_per_unit': float(str(data[11]).replace('$', '').replace(',', '')) if len(data) > 11 and data[11] else 0.0,  # L
                        'tax': float(str(data[12]).replace('$', '').replace(',', '')) if len(data) > 12 and data[12] else 0.0,  # M
                        'retail_price': float(str(data[14]).replace('$', '').replace(',', '')) if len(data) > 14 and data[14] else 0.0,  # O
                        'row_number': row_index
                    }

            return None  # UUID not found

        except Exception as e:
            raise Exception(f"Failed to read product by UUID: {e}")

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
            # Columns: A (uuid), B (product), C (date), D (qty purchased), E (qty available), L (cost), M (tax), T (sold checkbox)
            range_to_read = f"{sheet_name}!A{start_row}:T{last_row - 1}"
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
                while len(row) < 20:  # A to T = 20 columns
                    row.append('')

                # Column indices (0-based within our read range A:T)
                uuid_val = row[0]  # A
                product_name = row[1]  # B
                date_purchased = row[2]  # C
                qty_purchased = row[3]  # D
                qty_available = row[4]  # E
                cost_per_unit = row[11]  # L (position 11 in A:T range)
                tax_total = row[12]  # M (position 12 in A:T range)
                sold_checkbox = row[19]  # T (position 19 in A:T range)

                print(f"DEBUG: Row {start_row + row_index}: Product='{product_name}', Date='{date_purchased}', Qty Avail='{qty_available}', Sold='{sold_checkbox}'")

                # Skip empty rows (no product name)
                if not product_name or str(product_name).strip() == '':
                    print(f"DEBUG: Skipping row {start_row + row_index} - empty product name")
                    continue

                # Skip sold items (checkbox in column T is TRUE)
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
                    'uuid': str(uuid_val).strip() if uuid_val else '',
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
