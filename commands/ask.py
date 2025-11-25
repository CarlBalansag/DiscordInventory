"""
/ask command implementation - AI-powered spreadsheet analysis using Gemini
"""
import discord
from discord import app_commands
import google.generativeai as genai
import config
from datetime import datetime

class AskCommand:
    """AI-powered spreadsheet analysis"""

    @staticmethod
    def format_inventory_data(items: list) -> str:
        """Format inventory data for AI consumption"""
        if not items:
            return "No inventory data available."

        # Create a comprehensive data format
        output = "INVENTORY DATA:\n"
        output += "Product | Date Purchased | Qty Purchased | Qty Available | Store | Cost/Unit | Tax Total | Total Cost | Retail Cost | Cashback | Listed | Sold\n"
        output += "-" * 150 + "\n"

        for item in items:
            output += f"{item['product_name']} | "
            output += f"{item.get('date_purchased', 'N/A')} | "
            output += f"{item.get('qty_purchased', 0)} | "
            output += f"{item.get('qty_available', 0)} | "
            output += f"{item.get('store_purchased', 'N/A')} | "
            output += f"${item.get('cost_per_unit', 0):.2f} | "
            output += f"${item.get('tax_total', 0):.2f} | "
            output += f"${item.get('total_cost', 0):.2f} | "
            output += f"${item.get('retail_cost', 0):.2f} | "
            output += f"${item.get('cashback_total', 0):.2f} | "
            output += f"{'Yes' if item.get('is_listed', False) else 'No'} | "
            output += f"{'Yes' if item.get('is_sold', False) else 'No'}\n"

        return output

    @staticmethod
    def format_sales_data(items: list) -> str:
        """Format sales data for AI consumption"""
        if not items:
            return "No sales data available."

        output = "\nSALES DATA:\n"
        output += "Product | Date Sold | Qty Sold | Price/Unit | Total Revenue | Shipping Cost | Net Profit | ROI\n"
        output += "-" * 120 + "\n"

        for item in items:
            output += f"{item['product_name']} | "
            output += f"{item.get('sold_date', 'N/A')} | "
            output += f"{item.get('quantity_sold', 0)} | "
            output += f"${item.get('price_per_unit', 0):.2f} | "
            output += f"${item.get('total_revenue', 0):.2f} | "
            output += f"${item.get('shipping_cost', 0):.2f} | "
            output += f"${item.get('net_profit', 0):.2f} | "
            output += f"{item.get('roi', 0):.1f}%\n"

        return output

    @staticmethod
    async def ask_gemini(inventory_data: str, sales_data: str, user_question: str) -> str:
        """
        Send data and question to Gemini API

        Args:
            inventory_data: Formatted inventory data string
            sales_data: Formatted sales data string
            user_question: User's question

        Returns:
            AI-generated answer
        """
        try:
            # Configure Gemini
            genai.configure(api_key=config.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')

            # Create the prompt
            current_date = datetime.now().strftime("%m/%d/%Y")
            prompt = f"""You are a helpful financial assistant analyzing a reselling business spreadsheet.

Today's date is: {current_date}

Here is the data from the user's inventory and sales:

{inventory_data}

{sales_data}

IMPORTANT NOTES:
- The inventory data includes total_cost (already calculated in spreadsheet)
- The sales data includes net_profit and ROI (already calculated in spreadsheet)
- For spending calculations, use the total_cost from inventory
- For profit calculations, use the net_profit from sales
- Cashback should be subtracted from total spending when relevant
- Items marked as "Sold: Yes" have been fully sold out
- Items marked as "Listed: Yes" are currently listed for sale

When calculating monthly totals:
- Match dates in MM/DD/YYYY format
- For "this month", use {current_date} to determine the current month and year

User's Question: {user_question}

Please provide a clear, concise answer with specific numbers. Show your calculations when relevant. If you need to make assumptions, state them clearly.
"""

            # Generate response
            response = model.generate_content(prompt)
            return response.text

        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")


class AskModal(discord.ui.Modal, title='Ask AI About Your Data'):
    """Modal for asking questions"""

    question = discord.ui.TextInput(
        label='Your Question',
        placeholder='e.g., How much did I spend on 11/24/2025?',
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Handle question submission"""
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

            # Send "thinking" message
            await interaction.followup.send(
                "🤔 Analyzing your data and thinking...",
                ephemeral=True
            )

            # Read inventory data
            inventory_items = sheets_manager.read_inventory(
                user['spreadsheet_id'],
                user['sheet_name'],
                start_row=8
            )

            # Read sales data (starts at row 7)
            sales_items = sheets_manager.read_sales(
                user['spreadsheet_id'],
                config.SALES_SHEET_NAME,
                start_row=7
            )

            # Format data for AI
            inventory_text = AskCommand.format_inventory_data(inventory_items)
            sales_text = AskCommand.format_sales_data(sales_items)

            # Get AI response
            answer = await AskCommand.ask_gemini(
                inventory_text,
                sales_text,
                self.question.value
            )

            # Send answer (split if too long)
            if len(answer) > 1900:
                # Split into chunks
                chunks = [answer[i:i+1900] for i in range(0, len(answer), 1900)]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await interaction.edit_original_response(
                            content=f"**Question:** {self.question.value}\n\n**Answer:**\n{chunk}"
                        )
                    else:
                        await interaction.followup.send(
                            content=chunk,
                            ephemeral=True
                        )
            else:
                await interaction.edit_original_response(
                    content=f"**Question:** {self.question.value}\n\n**Answer:**\n{answer}"
                )

        except Exception as e:
            await interaction.edit_original_response(
                content=f"Error: {str(e)}\n\nMake sure:\n1. You have GEMINI_API_KEY in your .env file\n2. You have both Inventory and Sales sheets set up\n3. The sheets are accessible to the bot"
            )
