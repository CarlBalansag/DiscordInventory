"""
/remove command implementation for inventory items
"""
import discord
from discord import app_commands


class RemoveConfirmView(discord.ui.View):
    """Confirmation view for removing an item"""

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
                user['sheet_name'],
                self.item['row_number']
            )

            await interaction.followup.send(
                f"✅ **Successfully deleted product!**\n\n"
                f"**Product:** {self.item['product_name']}\n"
                f"**Row:** {self.item['row_number']}",
                ephemeral=True
            )

            # Disable buttons
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)

        except Exception as e:
            await interaction.followup.send(
                f"❌ Error deleting product: {str(e)}",
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


class RemoveInventorySelectView(discord.ui.View):
    """Product selection dropdown for removal"""

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
            placeholder="Select a product to remove",
            options=options
        )
        select.callback = self.product_callback
        self.add_item(select)

    async def product_callback(self, interaction: discord.Interaction):
        """Handle product selection"""
        selected_index = int(interaction.data['values'][0])
        selected_product = self.products[selected_index]

        # Show confirmation
        view = RemoveConfirmView(item=selected_product)
        await interaction.response.send_message(
            f"⚠️ **Are you sure you want to delete this product?**\n\n"
            f"**Product:** {selected_product['product_name']}\n"
            f"**Date:** {selected_product['date_purchased']}\n"
            f"**Qty Available:** {selected_product['qty_available']}\n"
            f"**Cost:** ${selected_product['cost_per_unit']:.2f}\n\n"
            f"This action cannot be undone!",
            view=view,
            ephemeral=True
        )
