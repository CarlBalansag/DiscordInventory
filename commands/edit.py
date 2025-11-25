"""
/edit command implementation for inventory items
"""
import discord
from discord import app_commands
import re
import config


class EditInventoryModal(discord.ui.Modal, title='Edit Product'):
    """Modal for editing inventory item fields"""

    product_name = discord.ui.TextInput(
        label='Product Name',
        placeholder='e.g., Pokemon Card - Charizard',
        required=False,
        style=discord.TextStyle.short
    )

    date_purchased = discord.ui.TextInput(
        label='Date Purchased (MM/DD/YYYY)',
        placeholder='e.g., 01/15/2025',
        required=False,
        style=discord.TextStyle.short,
        max_length=10
    )

    quantity = discord.ui.TextInput(
        label='Quantity Available',
        placeholder='e.g., 5',
        required=False,
        style=discord.TextStyle.short
    )

    cost_per_unit = discord.ui.TextInput(
        label='Cost Per Unit ($)',
        placeholder='e.g., 25.50',
        required=False,
        style=discord.TextStyle.short
    )

    tax = discord.ui.TextInput(
        label='Tax ($)',
        placeholder='e.g., 5.25',
        required=False,
        style=discord.TextStyle.short
    )

    def __init__(self, item: dict):
        super().__init__()
        self.item = item

        # Pre-fill with current values
        self.product_name.default = item['product_name']
        self.date_purchased.default = item['date_purchased']
        self.quantity.default = str(item.get('qty_available', ''))
        self.cost_per_unit.default = str(item.get('cost_per_unit', ''))

        # Calculate total tax from tax per unit
        tax_total = item.get('tax_per_unit', 0) * item.get('qty_available', 0)
        self.tax.default = str(tax_total) if tax_total > 0 else ''

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

            if self.date_purchased.value:
                # Validate date format
                if not re.match(r'^\d{2}/\d{2}/\d{4}$', self.date_purchased.value):
                    await interaction.followup.send(
                        "Invalid date format. Please use MM/DD/YYYY (e.g., 01/15/2025)",
                        ephemeral=True
                    )
                    return
                data['date_purchased'] = self.date_purchased.value

            if self.quantity.value:
                try:
                    quantity_val = int(self.quantity.value)
                    if quantity_val < 0:
                        raise ValueError()
                    data['quantity'] = str(quantity_val)
                except ValueError:
                    await interaction.followup.send(
                        "Quantity must be a valid number",
                        ephemeral=True
                    )
                    return

            if self.cost_per_unit.value:
                try:
                    cost_val = float(self.cost_per_unit.value)
                    if cost_val < 0:
                        raise ValueError()
                    data['cost_per_unit'] = str(cost_val)
                except ValueError:
                    await interaction.followup.send(
                        "Cost must be a valid number",
                        ephemeral=True
                    )
                    return

            if self.tax.value:
                try:
                    tax_val = float(self.tax.value)
                    if tax_val < 0:
                        raise ValueError()
                    data['tax'] = str(tax_val)
                except ValueError:
                    await interaction.followup.send(
                        "Tax must be a valid number",
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
                user['sheet_name'],
                self.item['row_number'],
                data
            )

            # Build update summary
            changes = '\n'.join([f"**{key.replace('_', ' ').title()}:** {value}" for key, value in data.items()])

            await interaction.followup.send(
                f"✅ **Successfully updated product in row {self.item['row_number']}!**\n\n"
                f"**Changes made:**\n{changes}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"Error updating product: {str(e)}",
                ephemeral=True
            )


class InventorySelectView(discord.ui.View):
    """Product selection dropdown for editing"""

    def __init__(self, products: list):
        super().__init__(timeout=300)
        self.products = products

        # Create select menu with products (max 25 options)
        options = [
            discord.SelectOption(
                label=f"{product['product_name'][:80]}",
                description=f"Qty: {product['qty_available']} | Cost: ${product['cost_per_unit']:.2f}",
                value=str(i)
            )
            for i, product in enumerate(products[:25])  # Discord limit is 25 options
        ]

        select = discord.ui.Select(
            placeholder="Select a product to edit",
            options=options
        )
        select.callback = self.product_callback
        self.add_item(select)

    async def product_callback(self, interaction: discord.Interaction):
        """Handle product selection"""
        selected_index = int(interaction.data['values'][0])
        selected_product = self.products[selected_index]

        # Show edit modal
        modal = EditInventoryModal(item=selected_product)
        await interaction.response.send_modal(modal)
