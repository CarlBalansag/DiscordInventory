"""
/sales command implementation
"""
import discord
from discord import app_commands
import re
import config

class RecordSaleModal(discord.ui.Modal, title='Record Sale'):
    """Modal for recording a sale"""

    sold_date = discord.ui.TextInput(
        label='Sold Date (MM/DD/YYYY)',
        placeholder='e.g., 01/20/2025',
        required=True,
        style=discord.TextStyle.short,
        max_length=10
    )

    quantity_sold = discord.ui.TextInput(
        label='Quantity Sold',
        placeholder='e.g., 2',
        required=True,
        style=discord.TextStyle.short
    )

    price_per_unit = discord.ui.TextInput(
        label='Price Per Unit ($)',
        placeholder='e.g., 50.00',
        required=True,
        style=discord.TextStyle.short
    )

    shipping_cost = discord.ui.TextInput(
        label='Shipping/Handling Cost ($)',
        placeholder='e.g., 5.00 (or 0 for none)',
        required=True,
        style=discord.TextStyle.short
    )

    def __init__(self, product_name: str):
        super().__init__()
        self.product_name = product_name

    async def on_submit(self, interaction: discord.Interaction):
        """Submit the sale record"""
        await interaction.response.defer(ephemeral=True)

        try:
            # Validate date format
            if not re.match(r'^\d{2}/\d{2}/\d{4}$', self.sold_date.value):
                await interaction.followup.send(
                    "Invalid date format. Please use MM/DD/YYYY (e.g., 01/20/2025)",
                    ephemeral=True
                )
                return

            # Validate quantity
            try:
                quantity_val = int(self.quantity_sold.value)
                if quantity_val <= 0:
                    raise ValueError()
            except ValueError:
                await interaction.followup.send(
                    "Quantity must be a positive number",
                    ephemeral=True
                )
                return

            # Validate price and shipping cost
            try:
                price_val = float(self.price_per_unit.value)
                shipping_val = float(self.shipping_cost.value)
                if price_val < 0 or shipping_val < 0:
                    raise ValueError()
            except ValueError:
                await interaction.followup.send(
                    "Price and Shipping Cost must be valid numbers",
                    ephemeral=True
                )
                return

            # Import here to avoid circular imports
            from database import Database
            from google_sheets import GoogleSheetsManager

            db = Database()
            sheets_manager = GoogleSheetsManager()

            # Get user from database
            user = await db.get_user(str(interaction.user.id))
            if not user:
                await interaction.followup.send(
                    "You haven't set up your Google Sheets yet! Use `/setup` first.",
                    ephemeral=True
                )
                return

            # Call Apps Script to create new row in Sales sheet
            new_row = await sheets_manager.call_apps_script(
                user['spreadsheet_id'],
                config.SALES_SHEET_NAME,
                function_name='addRowAboveTotalSelective_Sales'
            )

            if not new_row:
                await interaction.followup.send(
                    "Failed to create new row in Sales sheet. Make sure your Apps Script has the addRowAboveTotalSelective_Sales function deployed.",
                    ephemeral=True
                )
                return

            # Prepare data to write
            data = {
                'product_name': self.product_name,
                'sold_date': self.sold_date.value,
                'quantity_sold': str(quantity_val),
                'price_per_unit': str(price_val),
                'shipping_cost': str(shipping_val)
            }

            # Write data to the new row
            sheets_manager.write_data_to_row(
                user['spreadsheet_id'],
                config.SALES_SHEET_NAME,
                new_row,
                data,
                column_mapping=config.SALES_COLUMN_MAPPING
            )

            await interaction.followup.send(
                f"**Successfully recorded sale to row {new_row}!**\n\n"
                f"**Product:** {self.product_name}\n"
                f"**Date Sold:** {self.sold_date.value}\n"
                f"**Quantity:** {quantity_val}\n"
                f"**Price Per Unit:** ${price_val}\n"
                f"**Shipping/Handling:** ${shipping_val}\n"
                f"**Total:** ${(price_val * quantity_val) + shipping_val:.2f}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"Error recording sale: {str(e)}",
                ephemeral=True
            )


class ProductSelectView(discord.ui.View):
    """Product selection dropdown"""

    def __init__(self, products: list):
        super().__init__(timeout=300)
        self.products = products

        # Create select menu with products (max 25 options)
        options = [
            discord.SelectOption(label=product['product_name'][:100], value=product['product_name'][:100])
            for product in products[:25]  # Discord limit is 25 options
        ]

        select = discord.ui.Select(
            placeholder="Select a product to record sale",
            options=options
        )
        select.callback = self.product_callback
        self.add_item(select)

    async def product_callback(self, interaction: discord.Interaction):
        """Handle product selection"""
        selected_product = interaction.data['values'][0]

        # Show sale modal
        modal = RecordSaleModal(product_name=selected_product)
        await interaction.response.send_modal(modal)
