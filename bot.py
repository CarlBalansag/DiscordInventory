"""
Discord Reselling Bot - Main Bot File
"""
import asyncio
import os

import discord
from aiohttp import web
from discord import app_commands
from discord.ext import commands
import config
from database import Database
from google_sheets import GoogleSheetsManager
from commands.add import AddProductStep1Modal
from commands.sales import ProductSelectView
from commands.ask import AskModal
from commands.edit import InventorySelectView
from commands.remove import RemoveInventorySelectView
from commands.edit_sales import SaleSelectView
from commands.remove_sales import RemoveSaleSelectView

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize database and Google Sheets manager
db = Database()
sheets_manager = GoogleSheetsManager()

@bot.event
async def on_ready():
    """Called when the bot is ready"""
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')

    # Initialize database
    await db.initialize()
    print('Database initialized')

    # Sync commands
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

def is_dm_only():
    """Check if command is used in DMs only"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is not None:
            await interaction.response.send_message(
                "This command can only be used in DMs for privacy reasons. Please DM me!",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

# ===== /SETUP COMMAND =====

class SetupModal(discord.ui.Modal, title='Setup Google Sheets'):
    """Modal for setting up user's Google Sheets"""

    spreadsheet_url = discord.ui.TextInput(
        label='Google Spreadsheet URL or ID',
        placeholder='https://docs.google.com/spreadsheets/d/YOUR_ID/edit...',
        required=True,
        style=discord.TextStyle.short
    )

    sheet_name = discord.ui.TextInput(
        label='Sheet Name (Tab Name)',
        placeholder='e.g., Transactions',
        required=True,
        style=discord.TextStyle.short,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        await interaction.response.defer(ephemeral=True)

        try:
            # Extract spreadsheet ID
            spreadsheet_id = sheets_manager.extract_spreadsheet_id(self.spreadsheet_url.value)

            # Verify access to the spreadsheet
            sheets_manager.verify_sheet_access(spreadsheet_id, self.sheet_name.value)

            # Save to database
            await db.add_user(
                discord_id=str(interaction.user.id),
                spreadsheet_id=spreadsheet_id,
                sheet_name=self.sheet_name.value
            )

            await interaction.followup.send(
                f"Successfully connected to your Google Sheet!\n"
                f"Spreadsheet ID: `{spreadsheet_id}`\n"
                f"Sheet Name: `{self.sheet_name.value}`\n\n"
                "You can now use `/add` to add products to your inventory!",
                ephemeral=True
            )

        except ValueError as e:
            await interaction.followup.send(
                f"Invalid spreadsheet URL/ID: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            error_message = str(e)
            if "not found" in error_message or "404" in error_message:
                await interaction.followup.send(
                    "Could not access the spreadsheet.\n\n"
                    "**Please make sure you've shared the spreadsheet with:**\n"
                    f"`{sheets_manager.credentials.service_account_email}`\n\n"
                    "Give it 'Editor' permissions.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"Error: {error_message}",
                    ephemeral=True
                )

@bot.tree.command(name="setup", description="Set up your Google Sheets connection")
@is_dm_only()
async def setup(interaction: discord.Interaction):
    """Setup command to register user's Google Sheets"""
    modal = SetupModal()
    await interaction.response.send_modal(modal)

# ===== /ADD COMMAND =====

@bot.tree.command(name="add", description="Add a product to your inventory")
@is_dm_only()
async def add(interaction: discord.Interaction):
    """Add product command"""
    # Check if user is registered
    user = await db.get_user(str(interaction.user.id))
    if not user:
        await interaction.response.send_message(
            "You haven't set up your Google Sheets yet! Use `/setup` first.",
            ephemeral=True
        )
        return

    # Show first step modal
    modal = AddProductStep1Modal()
    await interaction.response.send_modal(modal)

# ===== /SALES COMMAND =====

@bot.tree.command(name="sales", description="Record a sale")
@is_dm_only()
async def sales(interaction: discord.Interaction):
    """Record sale command"""
    await interaction.response.defer(ephemeral=True)

    try:
        # Check if user is registered
        user = await db.get_user(str(interaction.user.id))
        if not user:
            await interaction.followup.send(
                "You haven't set up your Google Sheets yet! Use `/setup` first.",
                ephemeral=True
            )
            return

        # Read inventory from Google Sheets to get available products
        items = sheets_manager.read_inventory(
            user['spreadsheet_id'],
            user['sheet_name'],
            start_row=8
        )

        if not items:
            await interaction.followup.send(
                "Your inventory is empty! Use `/add` to add products first.",
                ephemeral=True
            )
            return

        # Show product selection dropdown
        view = ProductSelectView(items)
        await interaction.followup.send(
            "Select the product you sold:",
            view=view,
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(
            f"Error loading products: {str(e)}",
            ephemeral=True
        )

# ===== /INVENTORY COMMAND =====

class InventoryPaginationView(discord.ui.View):
    """Pagination view for inventory display"""

    def __init__(self, items: list, items_per_page: int = 10):
        super().__init__(timeout=300)  # 5 minute timeout
        self.items = items
        self.items_per_page = items_per_page
        self.current_page = 0
        self.max_page = max(0, (len(items) - 1) // items_per_page)

    def create_embed(self, page: int) -> discord.Embed:
        """Create an embed for the current page"""
        start_idx = page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.items))
        page_items = self.items[start_idx:end_idx]

        embed = discord.Embed(
            title=f"Your Inventory ({len(self.items)} items)",
            color=discord.Color.blue()
        )

        for item in page_items:
            # Format the item display
            product_name = item['product_name']
            date = item['date_purchased'] if item['date_purchased'] else 'N/A'
            qty = item['qty_available']
            cost = item['cost_per_unit']
            tax = item['tax_per_unit']

            # Create field value
            value = (
                f"**Date:** {date}\n"
                f"**Qty Available:** {qty}\n"
                f"**Cost:** ${cost:.2f} | **Tax:** ${tax:.2f}"
            )

            embed.add_field(
                name=product_name,
                value=value,
                inline=False
            )

        # Add footer with page info
        embed.set_footer(text=f"Page {page + 1} of {self.max_page + 1}")

        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous page"""
        self.current_page = max(0, self.current_page - 1)
        await self.update_view(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next page"""
        self.current_page = min(self.max_page, self.current_page + 1)
        await self.update_view(interaction)

    async def update_view(self, interaction: discord.Interaction):
        """Update the message with new page"""
        # Update button states
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page == self.max_page)

        # Create new embed
        embed = self.create_embed(self.current_page)

        # Update message
        await interaction.response.edit_message(embed=embed, view=self)

@bot.tree.command(name="inventory", description="View your inventory")
@is_dm_only()
async def inventory(interaction: discord.Interaction):
    """View inventory command"""
    await interaction.response.defer(ephemeral=True)

    try:
        # Check if user is registered
        print(f"DEBUG: Checking user {interaction.user.id}")
        user = await db.get_user(str(interaction.user.id))

        if not user:
            print(f"DEBUG: User not found in database")
            await interaction.followup.send(
                "You haven't set up your Google Sheets yet! Use `/setup` first.",
                ephemeral=True
            )
            return

        print(f"DEBUG: User found - Spreadsheet ID: {user['spreadsheet_id']}, Sheet Name: {user['sheet_name']}")

        # Read inventory from Google Sheets
        print(f"DEBUG: Calling read_inventory...")
        items = sheets_manager.read_inventory(
            user['spreadsheet_id'],
            user['sheet_name'],
            start_row=8
        )
        print(f"DEBUG: read_inventory returned {len(items) if items else 0} items")

        if not items:
            print(f"DEBUG: No items returned, showing empty message")
            await interaction.followup.send(
                "Your inventory is empty! Use `/add` to add products.",
                ephemeral=True
            )
            return

        # Create pagination view
        view = InventoryPaginationView(items, items_per_page=10)
        embed = view.create_embed(0)

        # Update button states for first page
        view.previous_button.disabled = True
        if len(items) <= 10:
            view.next_button.disabled = True

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    except Exception as e:
        await interaction.followup.send(
            f"Error reading inventory: {str(e)}",
            ephemeral=True
        )

# ===== /ASK COMMAND =====

@bot.tree.command(name="ask", description="Ask AI questions about your inventory and sales data")
@is_dm_only()
async def ask(interaction: discord.Interaction):
    """Ask AI about spreadsheet data"""
    # Check if user is registered
    user = await db.get_user(str(interaction.user.id))
    if not user:
        await interaction.response.send_message(
            "You haven't set up your Google Sheets yet! Use `/setup` first.",
            ephemeral=True
        )
        return

    # Show question modal
    modal = AskModal()
    await interaction.response.send_modal(modal)

# ===== /EDIT COMMAND =====

@bot.tree.command(name="edit", description="Edit an inventory item")
@is_dm_only()
async def edit(interaction: discord.Interaction):
    """Edit inventory item command"""
    await interaction.response.defer(ephemeral=True)

    try:
        # Check if user is registered
        user = await db.get_user(str(interaction.user.id))
        if not user:
            await interaction.followup.send(
                "You haven't set up your Google Sheets yet! Use `/setup` first.",
                ephemeral=True
            )
            return

        # Read inventory from Google Sheets
        items = sheets_manager.read_inventory(
            user['spreadsheet_id'],
            user['sheet_name'],
            start_row=8
        )

        if not items:
            await interaction.followup.send(
                "Your inventory is empty! Use `/add` to add products first.",
                ephemeral=True
            )
            return

        # Show product selection dropdown
        view = InventorySelectView(items)
        await interaction.followup.send(
            "Select the product you want to edit:",
            view=view,
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(
            f"Error loading products: {str(e)}",
            ephemeral=True
        )

# ===== /REMOVE COMMAND =====

@bot.tree.command(name="remove", description="Remove an inventory item")
@is_dm_only()
async def remove(interaction: discord.Interaction):
    """Remove inventory item command"""
    await interaction.response.defer(ephemeral=True)

    try:
        # Check if user is registered
        user = await db.get_user(str(interaction.user.id))
        if not user:
            await interaction.followup.send(
                "You haven't set up your Google Sheets yet! Use `/setup` first.",
                ephemeral=True
            )
            return

        # Read inventory from Google Sheets
        items = sheets_manager.read_inventory(
            user['spreadsheet_id'],
            user['sheet_name'],
            start_row=8
        )

        if not items:
            await interaction.followup.send(
                "Your inventory is empty! Nothing to remove.",
                ephemeral=True
            )
            return

        # Show product selection dropdown
        view = RemoveInventorySelectView(items)
        await interaction.followup.send(
            "Select the product you want to remove:",
            view=view,
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(
            f"Error loading products: {str(e)}",
            ephemeral=True
        )

# ===== /EDIT-SALE COMMAND =====

@bot.tree.command(name="edit-sale", description="Edit a sale entry")
@is_dm_only()
async def edit_sale(interaction: discord.Interaction):
    """Edit sale entry command"""
    await interaction.response.defer(ephemeral=True)

    try:
        # Check if user is registered
        user = await db.get_user(str(interaction.user.id))
        if not user:
            await interaction.followup.send(
                "You haven't set up your Google Sheets yet! Use `/setup` first.",
                ephemeral=True
            )
            return

        # Read sales from Google Sheets
        sales = sheets_manager.read_sales(
            user['spreadsheet_id'],
            config.SALES_SHEET_NAME,
            start_row=8
        )

        if not sales:
            await interaction.followup.send(
                "You have no sales records! Use `/sales` to add sales first.",
                ephemeral=True
            )
            return

        # Show sale selection dropdown
        view = SaleSelectView(sales)
        await interaction.followup.send(
            "Select the sale you want to edit:",
            view=view,
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(
            f"Error loading sales: {str(e)}",
            ephemeral=True
        )

# ===== /REMOVE-SALE COMMAND =====

@bot.tree.command(name="remove-sale", description="Remove a sale entry")
@is_dm_only()
async def remove_sale(interaction: discord.Interaction):
    """Remove sale entry command"""
    await interaction.response.defer(ephemeral=True)

    try:
        # Check if user is registered
        user = await db.get_user(str(interaction.user.id))
        if not user:
            await interaction.followup.send(
                "You haven't set up your Google Sheets yet! Use `/setup` first.",
                ephemeral=True
            )
            return

        # Read sales from Google Sheets
        sales = sheets_manager.read_sales(
            user['spreadsheet_id'],
            config.SALES_SHEET_NAME,
            start_row=8
        )

        if not sales:
            await interaction.followup.send(
                "You have no sales records! Nothing to remove.",
                ephemeral=True
            )
            return

        # Show sale selection dropdown
        view = RemoveSaleSelectView(sales)
        await interaction.followup.send(
            "Select the sale you want to remove:",
            view=view,
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(
            f"Error loading sales: {str(e)}",
            ephemeral=True
        )

# ===== /CLEAR COMMAND =====

@bot.tree.command(name="clear", description="Delete all bot messages in this DM")
@is_dm_only()
async def clear(interaction: discord.Interaction):
    """Clear bot messages in DM"""
    await interaction.response.defer(ephemeral=True)

    try:
        # Get the DM channel
        channel = interaction.channel

        # Fetch recent messages (Discord limits to 100 per request)
        deleted_count = 0

        # Fetch messages in batches
        async for message in channel.history(limit=100):
            # Only delete messages sent by the bot
            if message.author.id == bot.user.id:
                try:
                    await message.delete()
                    deleted_count += 1
                except discord.errors.NotFound:
                    # Message already deleted, skip
                    pass
                except discord.errors.Forbidden:
                    # No permission to delete (shouldn't happen for bot's own messages)
                    pass

        # Send confirmation
        if deleted_count > 0:
            await interaction.followup.send(
                f"Cleared {deleted_count} bot message(s) from this DM.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "No bot messages found to clear.",
                ephemeral=True
            )

    except Exception as e:
        await interaction.followup.send(
            f"Error clearing messages: {str(e)}",
            ephemeral=True
        )

# ===== HEALTHCHECK HTTP SERVER (for Render free tier) =====

async def health(request):
    """Simple health endpoint for platform port checks."""
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"[HEALTH CHECK] Pinged at {timestamp}", flush=True)
    return web.Response(text=f"ok - {timestamp}")

async def run_http_server():
    """Run a minimal HTTP server so Render can detect a bound port."""
    app = web.Application()
    app.router.add_get("/", health)
    port = int(os.getenv("PORT", 10000))
    print(f"[HTTP SERVER] Starting on port {port}...", flush=True)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[HTTP SERVER] Running on http://0.0.0.0:{port}", flush=True)

# ===== RUN BOT =====

async def main_async():
    """Main entrypoint: validate config, init DB, start bot and HTTP server."""
    # Validate configuration (also checks service account file)
    config.validate_config()

    # Initialize database schema
    await db.initialize()

    # Run Discord bot and HTTP health server concurrently
    bot_task = asyncio.create_task(bot.start(config.DISCORD_TOKEN))
    http_task = asyncio.create_task(run_http_server())

    await asyncio.gather(bot_task, http_task)

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"Error running bot: {e}")
