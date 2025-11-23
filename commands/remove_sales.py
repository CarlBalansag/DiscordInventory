"""
/remove-sale command implementation for sales entries
"""
import discord
from discord import app_commands
import config


class RemoveSaleConfirmView(discord.ui.View):
    """Confirmation view for removing a sale"""

    def __init__(self, item: dict):
        super().__init__(timeout=60)
        self.item = item
        self.confirmed = False

    @discord.ui.button(label="Yes, Delete", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm deletion"""
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

            # Delete the row from Google Sheets
            sheets_manager.delete_row(
                user['spreadsheet_id'],
                config.SALES_SHEET_NAME,
                self.item['row_number']
            )

            await interaction.followup.send(
                f"✅ **Successfully deleted sale!**\n\n"
                f"**Product:** {self.item['product_name']}\n"
                f"**Date Sold:** {self.item['sold_date']}\n"
                f"**Row:** {self.item['row_number']}",
                ephemeral=True
            )

            # Disable buttons
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)

        except Exception as e:
            await interaction.followup.send(
                f"❌ Error deleting sale: {str(e)}",
                ephemeral=True
            )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel deletion"""
        await interaction.response.send_message(
            "❌ Deletion cancelled.",
            ephemeral=True
        )

        # Disable buttons
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)


class RemoveSaleSelectView(discord.ui.View):
    """Sale selection dropdown for removal"""

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
            placeholder="Select a sale to remove",
            options=options
        )
        select.callback = self.sale_callback
        self.add_item(select)

    async def sale_callback(self, interaction: discord.Interaction):
        """Handle sale selection"""
        selected_index = int(interaction.data['values'][0])
        selected_sale = self.sales[selected_index]

        # Show confirmation
        view = RemoveSaleConfirmView(item=selected_sale)
        await interaction.response.send_message(
            f"⚠️ **Are you sure you want to delete this sale?**\n\n"
            f"**Product:** {selected_sale['product_name']}\n"
            f"**Date Sold:** {selected_sale['sold_date']}\n"
            f"**Qty Sold:** {selected_sale['quantity_sold']}\n"
            f"**Price:** ${selected_sale['price_per_unit']:.2f}\n"
            f"**Shipping:** ${selected_sale['shipping_cost']:.2f}\n\n"
            f"This action cannot be undone!",
            view=view,
            ephemeral=True
        )
