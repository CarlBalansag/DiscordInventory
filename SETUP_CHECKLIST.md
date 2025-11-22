# Setup Checklist

Use this checklist to ensure you've completed all setup steps correctly.

## Prerequisites

- [ ] Python 3.8+ installed
- [ ] Discord account
- [ ] Google account
- [ ] Google Sheets with inventory tracking set up

## Discord Bot Setup

- [ ] Created Discord application at https://discord.com/developers/applications
- [ ] Added bot to application
- [ ] Enabled "Message Content Intent" in bot settings
- [ ] Copied bot token
- [ ] Generated invite URL with bot + applications.commands scopes
- [ ] Invited bot to Discord server
- [ ] Bot shows as online in server

## Google Cloud Setup

- [ ] Created/selected Google Cloud project
- [ ] Enabled Google Sheets API
- [ ] Created service account
- [ ] Downloaded service account JSON credentials
- [ ] Renamed credentials file to `service_account.json`
- [ ] Placed `service_account.json` in project root
- [ ] Copied service account email (format: `name@project.iam.gserviceaccount.com`)

## Google Apps Script Setup

- [ ] Opened Google Sheet
- [ ] Opened Apps Script editor (Extensions > Apps Script)
- [ ] Copied code from `google_apps_script_template.gs`
- [ ] Customized `addRowAboveTotalSelective` function for your sheet
- [ ] Tested the function with "Run" button
- [ ] Clicked "Deploy" > "New deployment"
- [ ] Selected "Web app" as deployment type
- [ ] Set "Execute as" to "Me"
- [ ] Set "Who has access" to "Anyone"
- [ ] Completed authorization flow
- [ ] Copied Web App URL
- [ ] Tested Web App URL in browser (should return JSON)

## Google Sheets Permissions

- [ ] Opened your Google Sheet
- [ ] Clicked "Share" button
- [ ] Pasted service account email
- [ ] Granted "Editor" permissions
- [ ] Clicked "Send"

## Project Configuration

- [ ] Installed dependencies: `pip install -r requirements.txt`
- [ ] Copied `.env.example` to `.env`
- [ ] Added Discord bot token to `.env`
- [ ] Added Google Apps Script Web App URL to `.env`
- [ ] Verified `service_account.json` path in `.env`

## Test the Bot

- [ ] Run `python bot.py`
- [ ] See "Bot has connected to Discord!" message
- [ ] See "Database initialized" message
- [ ] See "Synced X command(s)" message
- [ ] DM the bot
- [ ] Run `/setup` command
- [ ] Enter spreadsheet URL
- [ ] Enter sheet name (tab name)
- [ ] Receive success message
- [ ] Run `/add` command
- [ ] Fill in product information
- [ ] Select store from dropdown
- [ ] Add optional fields
- [ ] Receive success confirmation
- [ ] Verify new row appears in Google Sheet
- [ ] Verify formulas are copied correctly
- [ ] Verify data is in correct columns

## Common Issues

### Bot not responding
- Check bot is online
- Verify commands are in DMs only
- Check console for errors

### "Permission denied" error
- Verify sheet is shared with service account email
- Verify "Editor" permissions were granted
- Wait 1-2 minutes for permissions to propagate

### "Apps Script error"
- Verify Web App URL is correct
- Check "Who has access" is set to "Anyone"
- Verify script was deployed (not just saved)
- Check Apps Script execution logs

### Wrong columns
- Verify column mapping in `config.py`
- Check your sheet structure matches expected layout

## Next Steps

Once everything works:

- [ ] Test with multiple products
- [ ] Test edge cases (special characters, long text, etc.)
- [ ] Review data in Google Sheet
- [ ] Share bot with other users (they need to run `/setup` individually)
- [ ] Consider adding custom stores to `config.py`
- [ ] Plan future features (/inventory, /stats, etc.)

## Security Reminders

- [ ] Never commit `.env` file
- [ ] Never commit `service_account.json` file
- [ ] Never share bot token publicly
- [ ] Keep Apps Script Web App URL private
- [ ] Only share service account email with trusted users

## Support

If you encounter issues:
1. Check the console output for error messages
2. Review the README.md troubleshooting section
3. Verify all checklist items are completed
4. Check Google Apps Script execution logs
5. Test each component individually (database, Google Sheets API, Discord)

---

**Setup complete?** Start using the bot with `/setup` and `/add` commands!
