# Discord Reselling Bot

A Discord bot that helps resellers track their inventory and transactions using Google Sheets. Users can add products via Discord slash commands, and the bot automatically updates their personal Google Sheets.

## Features

- **DM-Only Commands** - Privacy-focused, all commands work in DMs only
- **Google Sheets Integration** - Seamlessly integrates with your existing Google Sheets
- **Multi-Step Forms** - Easy-to-use Discord modals for data entry
- **Automatic Row Creation** - Preserves formulas and styling when adding new entries
- **Custom Store Dropdown** - Quick selection from predefined stores
- **Optional Fields** - Support for links and retail price tracking

## Commands

- `/setup` - Connect your Google Sheets to the bot
- `/add` - Add a new product to your inventory

## Prerequisites

Before setting up the bot, you need:

1. Python 3.8 or higher
2. A Discord account and server
3. A Google account
4. Your existing Google Sheets with inventory tracking

## Installation

### Step 1: Clone and Install Dependencies

```bash
cd inventory
pip install -r requirements.txt
```

### Step 2: Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
5. Click "Reset Token" and copy your bot token (save this for later)
6. Go to the "OAuth2" > "URL Generator" tab
7. Select scopes:
   - `bot`
   - `applications.commands`
8. Select bot permissions:
   - Send Messages
   - Use Slash Commands
9. Copy the generated URL and open it to invite the bot to your server

### Step 3: Set Up Google Cloud Project

#### Create Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Sheets API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"
4. Create Service Account credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Give it a name (e.g., "discord-bot-sheets")
   - Click "Create and Continue"
   - Skip the optional steps
   - Click "Done"
5. Download the credentials:
   - Click on the service account you just created
   - Go to the "Keys" tab
   - Click "Add Key" > "Create New Key"
   - Select "JSON" format
   - Click "Create" (a JSON file will download)
6. Rename the downloaded file to `service_account.json` and place it in your project root
7. **IMPORTANT**: Copy the service account email (it looks like `bot-name@project-id.iam.gserviceaccount.com`). You'll need this later.

### Step 4: Deploy Google Apps Script

Your existing `addRowAboveTotalSelective` function needs to be deployed as a Web App so Python can call it.

#### Modify Your Apps Script

1. Open your Google Sheet
2. Go to **Extensions** > **Apps Script**
3. Add this code (or modify your existing script):

```javascript
/**
 * Web App endpoint that creates a new row and returns the row number
 */
function doPost(e) {
  try {
    // Parse the request
    var data = JSON.parse(e.postData.contents);
    var spreadsheetId = data.spreadsheetId;
    var sheetName = data.sheetName;

    // Open the spreadsheet and sheet
    var spreadsheet = SpreadsheetApp.openById(spreadsheetId);
    var sheet = spreadsheet.getSheetByName(sheetName);

    if (!sheet) {
      return ContentService.createTextOutput(
        JSON.stringify({error: 'Sheet not found'})
      ).setMimeType(ContentService.MimeType.JSON);
    }

    // Call your existing function to add a row
    var newRow = addRowAboveTotalSelective(sheet);

    // Return the new row number
    return ContentService.createTextOutput(
      JSON.stringify({newRow: newRow})
    ).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(
      JSON.stringify({error: error.toString()})
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Your existing function (modify as needed)
 * This should create a new row, copy formulas and styling, and return the row number
 */
function addRowAboveTotalSelective(sheet) {
  // Your existing implementation here
  // Make sure it returns the new row number

  // Example implementation:
  var lastRow = sheet.getLastRow();
  sheet.insertRowAfter(lastRow);
  var newRow = lastRow + 1;

  // Copy formulas and formatting from the row above
  var sourceRange = sheet.getRange(lastRow, 1, 1, sheet.getLastColumn());
  var targetRange = sheet.getRange(newRow, 1, 1, sheet.getLastColumn());
  sourceRange.copyTo(targetRange, SpreadsheetApp.CopyPasteType.PASTE_FORMAT, false);
  sourceRange.copyTo(targetRange, SpreadsheetApp.CopyPasteType.PASTE_FORMULA, false);

  // Clear the data values (keep formulas)
  // Add your logic here to clear only data cells, not formula cells

  return newRow;
}
```

#### Deploy the Script

1. Click the **Deploy** button (top right)
2. Select **New deployment**
3. Click the gear icon ⚙️ next to "Select type"
4. Choose **Web app**
5. Configure the deployment:
   - **Description**: "Discord Bot Integration"
   - **Execute as**: Me
   - **Who has access**: Anyone
6. Click **Deploy**
7. **Authorize** the script (you may see a security warning - click Advanced > Go to [project name])
8. **Copy the Web App URL** (it will look like `https://script.google.com/macros/s/XXXXX/exec`)
9. Click **Done**

### Step 5: Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your values:
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   GOOGLE_SCRIPT_URL=https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec
   SERVICE_ACCOUNT_FILE=service_account.json
   DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DBNAME
   ```

### Step 6: Share Your Google Sheet

Each user needs to share their Google Sheet with the service account:

1. Open your Google Sheet
2. Click the **Share** button
3. Paste the service account email (from Step 3.7)
4. Give it **Editor** permissions
5. Click **Send**

## Usage

### Running the Bot

```bash
python bot.py
```

You should see:
```
Bot has connected to Discord!
Database initialized
Synced 2 command(s)
```

### User Workflow

1. **Setup**
   - DM the bot
   - Run `/setup`
   - Enter your Google Spreadsheet URL (e.g., `https://docs.google.com/spreadsheets/d/YOUR_ID/edit`)
   - Enter your sheet name (the tab name, e.g., "Transactions")
   - Bot confirms connection

2. **Add Products**
   - Run `/add`
   - **Step 1**: Fill in basic info:
     - Product Name
     - Date Purchased (MM/DD/YYYY)
     - Quantity
     - Cost Per Unit
     - Tax
   - **Step 2**: Select store from dropdown
   - **Step 3**: Add optional fields:
     - Links
     - Retail Price
   - Bot confirms the product was added

## Column Mapping

The bot writes to these columns in your Google Sheet:

| Column | Field |
|--------|-------|
| B | Product Name |
| C | Date Purchased |
| D | Quantity Purchased |
| H | Store Purchased |
| J | Links (optional) |
| L | Cost Per Unit |
| M | Tax |
| O | Retail Price (optional) |

If your sheet uses different columns, modify the `COLUMN_MAPPING` in [config.py](config.py).

## Store Options

Default stores in the dropdown:
- Amazon
- Walmart
- Target
- Best Buy
- Costco
- Pokemon Store
- Other

To modify stores, edit the `STORE_OPTIONS` list in [config.py](config.py).

## Troubleshooting

### Bot doesn't respond to commands

- Make sure the bot is online
- Verify you're using commands in DMs (not in a server channel)
- Check that commands are synced (see bot console output)

### "Permission denied" error

- Make sure you've shared your Google Sheet with the service account email
- Give the service account **Editor** permissions

### "Sheet not found" error

- Double-check the sheet name (tab name) you entered
- Sheet names are case-sensitive

### "Apps Script error"

- Verify your Apps Script is deployed as a Web App
- Check the Web App URL in your `.env` file
- Make sure "Who has access" is set to "Anyone"

### Date format error

- Use MM/DD/YYYY format (e.g., 01/15/2025)
- Leading zeros are required

## Project Structure

```
inventory/
??? bot.py                    # Main bot file
??? config.py                 # Configuration settings
??? database.py               # Postgres database operations
??? google_sheets.py          # Google Sheets API integration
??? commands/
?   ??? __init__.py
?   ??? add.py                # /add command implementation
??? requirements.txt          # Python dependencies
??? .env                      # Environment variables (create from .env.example)
??? .env.example              # Environment template
??? .gitignore                # Git ignore file
??? service_account.json      # Google credentials (git-ignored)
??? README.md                 # This file
```

## Security Notes

- Never commit `.env` or `service_account.json` to version control
- The bot only works in DMs to protect user privacy
- Each user has their own Google Sheet
- Service account only has access to sheets explicitly shared with it

## Future Enhancements

- `/inventory` command to view all items
- `/stats` command for profit calculations
- `/edit` and `/delete` commands
- Data export functionality
- Multi-sheet support (separate transactions and sales)

## License

This project is open source and available for personal and commercial use.

## Support

For issues or questions, please create an issue in the repository.
