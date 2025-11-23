"""
/edit-sale command implementation for sales entries
"""
import discord
from discord import app_commands
import re
import config


class EditSaleModal(discord.ui.Modal, title='Edit Sale'):
    """Modal for editing sale entry fields"""

    product_name = discord.ui.TextInput(
        label='Product Name',
        placeholder='e.g., Pokemon Card - Charizard',
        required=False,
        style=discord.TextStyle.short
    )

    sold_date = discord.ui.TextInput(
        label='Sold Date (MM/DD/YYYY)',
        placeholder='e.g., 01/20/2025',
        required=False,
        style=discord.TextStyle.short,
        max_length=10
    )

    quantity_sold = discord.ui.TextInput(
        label='Quantity Sold',
        placeholder='e.g., 2',
        required=False,
        style=discord.TextStyle.short
    )

    price_per_unit = discord.ui.TextInput(
        label='Price Per Unit ($)',
        placeholder='e.g., 50.00',
        required=False,
        style=discord.TextStyle.short
    )

    shipping_cost = discord.ui.TextInput(
        label='Shipping/Handling Cost ($)',
        placeholder='e.g., 5.00',
        required=False,
        style=discord.TextStyle.short
    )

    def __init__(self, item: dict):
        super().__init__()
        self.item = item

        # Pre-fill with current values
        self.product_name.default = item['product_name']
        self.sold_date.default = item['sold_date']
        self.quantity_sold.default = str(item.get('quantity_sold', ''))
        self.price_per_unit.default = str(item.get('price_per_unit', ''))
        self.shipping_cost.default = str(item.get('shipping_cost', ''))

    async def on_submit(self, interaction: discord.Interaction):
        """Submit the edited values"""
        await interaction.response.defer(ephemeral=True)

        try:
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

            # Prepare data to update (only fields that were changed)
            data = {}

            if self.product_name.value and self.product_name.value != self.item['product_name']:
                data['product_name'] = self.product_name.value

            if self.sold_date.value:
                # Validate date format
                if not re.match(r'^\d{2}/\d{2}/\d{4}$', self.sold_date.value):
                    await interaction.followup.send(
                        "Invalid date format. Please use MM/DD/YYYY (e.g., 01/20/2025)",
                        ephemeral=True
                    )
                    return
                data['sold_date'] = self.sold_date.value

            if self.quantity_sold.value:
                try:
                    quantity_val = int(self.quantity_sold.value)
                    if quantity_val <= 0:
                        raise ValueError()
                    data['quantity_sold'] = str(quantity_val)
                except ValueError:
                    await interaction.followup.send(
                        "Quantity must be a positive number",
                        ephemeral=True
                    )
                    return

            if self.price_per_unit.value:
                try:
                    price_val = float(self.price_per_unit.value)
                    if price_val < 0:
                        raise ValueError()
                    data['price_per_unit'] = str(price_val)
                except ValueError:
                    await interaction.followup.send(
                        "Price must be a valid number",
                        ephemeral=True
                    )
                    return

            if self.shipping_cost.value:
                try:
                    shipping_val = float(self.shipping_cost.value)
                    if shipping_val < 0:
                        raise ValueError()
                    data['shipping_cost'] = str(shipping_val)
                except ValueError:
                    await interaction.followup.send(
                        "Shipping cost must be a valid number",
                        ephemeral=True
                    )
                    return

            if not data:
                await interaction.followup.send(
                    "No changes were made.",
                    ephemeral=True
                )
                return

            # Update the row in Google Sheets
            sheets_manager.write_data_to_row(
                user['spreadsheet_id'],
                config.SALES_SHEET_NAME,
                self.item['row_number'],
                data,
                column_mapping=config.SALES_COLUMN_MAPPING
            )

            # Build update summary
            changes = '\n'.join([f"**{key.replace('_', ' ').title()}:** {value}" for key, value in data.items()])

            await interaction.followup.send(
                f"✅ **Successfully updated sale in row {self.item['row_number']}!**\n\n"
                f"**Changes made:**\n{changes}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Error updating sale: {str(e)}",
                ephemeral=True
            )


class SaleSelectView(discord.ui.View):
    """Sale selection dropdown for editing"""

    def __init__(self, sales: list):
        super().__init__(timeout=300)
        self.sales = sales

        # Create select menu with sales (max 25 options)
        options = [
            discord.SelectOption(
                label=f"{sale['product_name'][:70]}",
                description=f"Date: {sale['sold_date']} | Qty: {sale['quantity_sold']} | ${sale['price_per_unit']:.2f}",
                value=str(i)
            )
            for i, sale in enumerate(sales[:25])  # Discord limit is 25 options
        ]

        select = discord.ui.Select(
            placeholder="Select a sale to edit",
            options=options
        )
        select.callback = self.sale_callback
        self.add_item(select)

    async def sale_callback(self, interaction: discord.Interaction):
        """Handle sale selection"""
        selected_index = int(interaction.data['values'][0])
        selected_sale = self.sales[selected_index]

        # Show edit modal
        modal = EditSaleModal(item=selected_sale)
        await interaction.response.send_modal(modal)
