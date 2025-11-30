"""
/add command implementation with multi-step form
"""
import discord
from discord import app_commands
import re
import uuid
import config

class AddProductStep1Modal(discord.ui.Modal, title='Add Product - Step 1/3'):
    """First step: Basic product information"""

    product_name = discord.ui.TextInput(
        label='Product Name',
        placeholder='e.g., Pokemon Card - Charizard',
        required=True,
        style=discord.TextStyle.short
    )

    date_purchased = discord.ui.TextInput(
        label='Date Purchased (MM/DD/YYYY)',
        placeholder='e.g., 01/15/2025',
        required=True,
        style=discord.TextStyle.short,
        max_length=10
    )

    quantity = discord.ui.TextInput(
        label='Quantity Purchased',
        placeholder='e.g., 5',
        required=True,
        style=discord.TextStyle.short
    )

    cost_per_unit = discord.ui.TextInput(
        label='Cost Per Unit ($)',
        placeholder='e.g., 25.50',
        required=True,
        style=discord.TextStyle.short
    )

    tax = discord.ui.TextInput(
        label='Tax ($)',
        placeholder='e.g., 5.25',
        required=True,
        style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Validate and proceed to store selection"""
        # Validate date format
        if not re.match(r'^\d{2}/\d{2}/\d{4}$', self.date_purchased.value):
            await interaction.response.send_message(
                "❌ Invalid date format. Please use MM/DD/YYYY (e.g., 01/15/2025)",
                ephemeral=True
            )
            return

        # Validate quantity
        try:
            quantity_val = int(self.quantity.value)
            if quantity_val <= 0:
                raise ValueError()
        except ValueError:
            await interaction.response.send_message(
                "❌ Quantity must be a positive number",
                ephemeral=True
            )
            return

        # Validate cost and tax
        try:
            cost_val = float(self.cost_per_unit.value)
            tax_val = float(self.tax.value)
            if cost_val < 0 or tax_val < 0:
                raise ValueError()
        except ValueError:
            await interaction.response.send_message(
                "❌ Cost and Tax must be valid numbers",
                ephemeral=True
            )
            return

        # Store values and show store selection
        view = StoreSelectView(
            product_name=self.product_name.value,
            date_purchased=self.date_purchased.value,
            quantity=str(quantity_val),
            cost_per_unit=str(cost_val),
            tax=str(tax_val)
        )

        await interaction.response.send_message(
            "**Step 2/3:** Select the store where you purchased the product:",
            view=view,
            ephemeral=True
        )

class StoreSelectView(discord.ui.View):
    """Store selection dropdown"""

    def __init__(self, product_name, date_purchased, quantity, cost_per_unit, tax):
        super().__init__(timeout=300)
        self.product_name = product_name
        self.date_purchased = date_purchased
        self.quantity = quantity
        self.cost_per_unit = cost_per_unit
        self.tax = tax

    @discord.ui.select(
        placeholder="Select Store",
        options=[discord.SelectOption(label=store, value=store) for store in config.STORE_OPTIONS]
    )
    async def store_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle store selection and show optional fields"""
        selected_store = select.values[0]

        # Show optional fields modal
        modal = AddProductStep2Modal(
            product_name=self.product_name,
            date_purchased=self.date_purchased,
            quantity=self.quantity,
            cost_per_unit=self.cost_per_unit,
            tax=self.tax,
            store=selected_store
        )

        await interaction.response.send_modal(modal)

class AddProductStep2Modal(discord.ui.Modal, title='Add Product - Step 3/3 (Optional)'):
    """Third step: Optional fields"""

    links = discord.ui.TextInput(
        label='Links (Optional)',
        placeholder='e.g., https://example.com/product',
        required=False,
        style=discord.TextStyle.paragraph
    )

    retail_price = discord.ui.TextInput(
        label='Retail Price ($) (Optional)',
        placeholder='e.g., 50.00',
        required=False,
        style=discord.TextStyle.short
    )

    def __init__(self, product_name, date_purchased, quantity, cost_per_unit, tax, store):
        super().__init__()
        self.product_name = product_name
        self.date_purchased = date_purchased
        self.quantity = quantity
        self.cost_per_unit = cost_per_unit
        self.tax = tax
        self.store = store

    async def on_submit(self, interaction: discord.Interaction):
        """Final submission - add to Google Sheets"""
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
                    "❌ You haven't set up your Google Sheets yet! Use `/setup` first.",
                    ephemeral=True
                )
                return

            # Validate retail price if provided
            retail_price_val = ""
            if self.retail_price.value:
                try:
                    retail_val = float(self.retail_price.value)
                    if retail_val < 0:
                        raise ValueError()
                    retail_price_val = str(retail_val)
                except ValueError:
                    await interaction.followup.send(
                        "❌ Retail price must be a valid number",
                        ephemeral=True
                    )
                    return

            # Generate UUID for this product
            product_uuid = str(uuid.uuid4())

            # Call Apps Script to create new row
            new_row = await sheets_manager.call_apps_script(
                user['spreadsheet_id'],
                user['sheet_name']
            )

            if not new_row:
                await interaction.followup.send(
                    "❌ Failed to create new row in Google Sheets. Make sure your Apps Script is deployed correctly.",
                    ephemeral=True
                )
                return

            # Prepare data to write
            data = {
                'uuid': product_uuid,
                'product_name': self.product_name,
                'date_purchased': self.date_purchased,
                'quantity': self.quantity,
                'store': self.store,
                'links': self.links.value if self.links.value else "",
                'cost_per_unit': self.cost_per_unit,
                'tax': self.tax,
                'retail_price': retail_price_val
            }

            # Write data to the new row
            sheets_manager.write_data_to_row(
                user['spreadsheet_id'],
                user['sheet_name'],
                new_row,
                data
            )

            # Set UUID cell text color to white (invisible)
            sheets_manager.set_cell_text_color(
                user['spreadsheet_id'],
                user['sheet_name'],
                f"A{new_row}",
                {'red': 1.0, 'green': 1.0, 'blue': 1.0}  # White color
            )

            # Create dashboard URL
            dashboard_url = f"{config.DASHBOARD_BASE_URL}/product/{product_uuid}?s={user['spreadsheet_id']}"

            # Update column B with HYPERLINK formula
            hyperlink_formula = f'=HYPERLINK("{dashboard_url}", "{self.product_name}")'
            sheets_manager.write_formula(
                user['spreadsheet_id'],
                user['sheet_name'],
                f"B{new_row}",
                hyperlink_formula
            )

            await interaction.followup.send(
                f"✅ **Successfully added product to row {new_row}!**\n\n"
                f"**Product:** {self.product_name}\n"
                f"**Dashboard:** {dashboard_url}\n"
                f"**Date:** {self.date_purchased}\n"
                f"**Quantity:** {self.quantity}\n"
                f"**Store:** {self.store}\n"
                f"**Cost Per Unit:** ${self.cost_per_unit}\n"
                f"**Tax:** ${self.tax}" +
                (f"\n**Links:** {self.links.value}" if self.links.value else "") +
                (f"\n**Retail Price:** ${retail_price_val}" if retail_price_val else ""),
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Error adding product: {str(e)}",
                ephemeral=True
            )
