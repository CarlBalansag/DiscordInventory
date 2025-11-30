"""
Migration script to backfill UUIDs for existing products
Run this once after deploying the UUID feature
"""
import asyncio
import os
import sys
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from google_sheets import GoogleSheetsManager
import config

async def backfill_uuids():
    """Add UUIDs to all existing products that don't have one"""

    # Validate config
    config.validate_config()

    db = Database()
    await db.initialize()

    sheets_manager = GoogleSheetsManager()

    print("=" * 60)
    print("Starting UUID backfill migration...")
    print("=" * 60)

    # Get all users
    from sqlalchemy import select
    from database import User

    async with db.SessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        print(f"\nFound {len(users)} users to process\n")

        total_updated = 0

        for user_idx, user in enumerate(users, 1):
            print(f"[{user_idx}/{len(users)}] Processing user: {user.discord_id}")
            print(f"  Spreadsheet: {user.spreadsheet_id}")
            print(f"  Sheet: {user.sheet_name}")

            try:
                # Read inventory
                items = sheets_manager.read_inventory(
                    user.spreadsheet_id,
                    user.sheet_name,
                    start_row=8
                )

                print(f"  Found {len(items)} items")

                updates = 0
                for item in items:
                    # Check if UUID exists
                    if not item.get('uuid') or item['uuid'].strip() == '':
                        # Generate UUID
                        new_uuid = str(uuid.uuid4())
                        row = item['row_number']

                        print(f"    Row {row}: Adding UUID to '{item['product_name']}'")

                        # Write UUID to column A
                        sheets_manager.write_data_to_row(
                            user.spreadsheet_id,
                            user.sheet_name,
                            row,
                            {'uuid': new_uuid}
                        )

                        # Set UUID cell text color to white (invisible)
                        sheets_manager.set_cell_text_color(
                            user.spreadsheet_id,
                            user.sheet_name,
                            f"A{row}",
                            {'red': 1.0, 'green': 1.0, 'blue': 1.0}  # White color
                        )

                        # Update column B with HYPERLINK
                        dashboard_url = f"{config.DASHBOARD_BASE_URL}/product/{new_uuid}?s={user.spreadsheet_id}"
                        hyperlink_formula = f'=HYPERLINK("{dashboard_url}", "{item["product_name"]}")'
                        sheets_manager.write_formula(
                            user.spreadsheet_id,
                            user.sheet_name,
                            f"B{row}",
                            hyperlink_formula
                        )

                        print(f"      ✓ UUID: {new_uuid}")
                        updates += 1

                print(f"  ✅ Updated {updates} products for this user")
                total_updated += updates

            except Exception as e:
                print(f"  ❌ Error processing user {user.discord_id}: {e}")
                continue

    print("\n" + "=" * 60)
    print(f"UUID backfill complete! Total products updated: {total_updated}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(backfill_uuids())
