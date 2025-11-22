/**
 * Google Apps Script Template for Discord Reselling Bot
 *
 * Instructions:
 * 1. Copy this code into your Google Apps Script editor
 * 2. Modify the addRowAboveTotalSelective function to match your needs
 * 3. Deploy as a Web App (Deploy > New deployment > Web app)
 * 4. Set "Execute as" to "Me" and "Who has access" to "Anyone"
 * 5. Copy the Web App URL to your .env file
 */

/**
 * Web App endpoint that receives POST requests from the Discord bot
 * Creates a new row and returns the row number
 */
function doPost(e) {
  try {
    // Parse the incoming JSON request
    var data = JSON.parse(e.postData.contents);
    var spreadsheetId = data.spreadsheetId;
    var sheetName = data.sheetName;
    var functionName = data.functionName || 'addRowAboveTotalSelective';

    Logger.log('Received request for spreadsheet: ' + spreadsheetId + ', sheet: ' + sheetName + ', function: ' + functionName);

    // Open the spreadsheet and sheet
    var spreadsheet = SpreadsheetApp.openById(spreadsheetId);
    var sheet = spreadsheet.getSheetByName(sheetName);

    if (!sheet) {
      Logger.log('Sheet not found: ' + sheetName);
      return ContentService.createTextOutput(
        JSON.stringify({error: 'Sheet "' + sheetName + '" not found'})
      ).setMimeType(ContentService.MimeType.JSON);
    }

    // Call the appropriate function based on functionName
    var newRow;
    if (functionName === 'addRowAboveTotalSelective_Sales') {
      newRow = addRowAboveTotalSelective_Sales(sheet);
    } else {
      newRow = addRowAboveTotalSelective(sheet);
    }

    Logger.log('Successfully created row: ' + newRow);

    // Return the new row number as JSON
    return ContentService.createTextOutput(
      JSON.stringify({newRow: newRow})
    ).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    Logger.log('Error: ' + error.toString());
    return ContentService.createTextOutput(
      JSON.stringify({error: error.toString()})
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Test function to verify the script works
 * Run this from the Apps Script editor to test
 */
function testAddRow() {
  var sheet = SpreadsheetApp.getActiveSheet();
  var newRow = addRowAboveTotalSelective(sheet);
  Logger.log('Created new row: ' + newRow);
}

/**
 * Creates a new row with formulas and formatting copied from the row above
 *
 * CUSTOMIZE THIS FUNCTION to match your specific spreadsheet structure
 *
 * @param {Sheet} sheet - The Google Sheet object
 * @return {number} The new row number
 */
function addRowAboveTotalSelective(sheet) {
  // OPTION 1: Simple implementation - inserts after last row
  // Uncomment this if your data doesn't have a totals row
  /*
  var lastRow = sheet.getLastRow();
  sheet.insertRowAfter(lastRow);
  var newRow = lastRow + 1;
  */

  // OPTION 2: Insert before a "Totals" row
  // This example assumes your totals are in the last row
  // Modify this to match your sheet structure
  var lastRow = sheet.getLastRow();
  var newRow = lastRow; // Insert before the last row (totals)
  sheet.insertRowBefore(newRow);

  // Copy formatting from the row above
  var sourceRow = newRow - 1; // The row above the new row
  var lastColumn = sheet.getLastColumn();

  var sourceRange = sheet.getRange(sourceRow, 1, 1, lastColumn);
  var targetRange = sheet.getRange(newRow, 1, 1, lastColumn);

  // Copy formatting (colors, borders, fonts, etc.)
  sourceRange.copyFormatToRange(sheet, 1, lastColumn, newRow, newRow);

  // Copy formulas (not values)
  for (var col = 1; col <= lastColumn; col++) {
    var sourceCell = sheet.getRange(sourceRow, col);
    var targetCell = sheet.getRange(newRow, col);

    var formula = sourceCell.getFormula();
    if (formula) {
      // Has a formula - copy it
      targetCell.setFormula(formula);
    } else {
      // No formula - clear the cell (don't copy values)
      targetCell.clearContent();

      // OPTIONAL: Keep data validation (like dropdowns)
      var validation = sourceCell.getDataValidation();
      if (validation) {
        targetCell.setDataValidation(validation);
      }
    }
  }

  // Clear specific columns that should be empty for new entries
  // Modify these column letters to match YOUR spreadsheet
  // These correspond to the data columns the bot will fill in
  var columnsToClear = ['B', 'C', 'D', 'H', 'I', 'K', 'L', 'N'];
  for (var i = 0; i < columnsToClear.length; i++) {
    var cell = sheet.getRange(columnsToClear[i] + newRow);
    cell.clearContent();

    // Keep data validation for dropdown columns
    if (columnsToClear[i] === 'H') { // Store column - keep dropdown
      var sourceCell = sheet.getRange(columnsToClear[i] + sourceRow);
      var validation = sourceCell.getDataValidation();
      if (validation) {
        cell.setDataValidation(validation);
      }
    }
  }

  return newRow;
}

/**
 * Alternative implementation if you want to insert at a specific position
 * based on a marker or search criteria
 */
function addRowAboveTotalSelectiveAdvanced(sheet) {
  // Find the "Total" row (customize the search term)
  var data = sheet.getDataRange().getValues();
  var totalRow = -1;

  for (var i = 0; i < data.length; i++) {
    // Check if first column contains "Total" (case-insensitive)
    if (data[i][0] && data[i][0].toString().toLowerCase().includes('total')) {
      totalRow = i + 1; // Convert to 1-indexed
      break;
    }
  }

  if (totalRow === -1) {
    // No total row found, insert at end
    totalRow = sheet.getLastRow() + 1;
  }

  // Insert new row before the total
  sheet.insertRowBefore(totalRow);
  var newRow = totalRow;

  // Copy from the row above (now at newRow - 1)
  var sourceRow = newRow - 1;
  var lastColumn = sheet.getLastColumn();

  var sourceRange = sheet.getRange(sourceRow, 1, 1, lastColumn);
  sourceRange.copyFormatToRange(sheet, 1, lastColumn, newRow, newRow);

  // Copy formulas
  for (var col = 1; col <= lastColumn; col++) {
    var sourceCell = sheet.getRange(sourceRow, col);
    var targetCell = sheet.getRange(newRow, col);

    var formula = sourceCell.getFormula();
    if (formula) {
      targetCell.setFormula(formula);
    } else {
      targetCell.clearContent();
    }
  }

  return newRow;
}

/**
 * Sales Sheet Function - Creates a new row in the Sales sheet
 * Based on the user's provided addRowAboveTotalSelective_Sales function
 *
 * This function should match the structure and configuration provided by the user
 * @param {Sheet} sheet - The Sales sheet object
 * @return {number} The new row number
 */
function addRowAboveTotalSelective_Sales(sheet) {
  // User's existing implementation goes here
  // This is just a placeholder - the user should paste their actual function

  // Find the "Total" row in column B (SALES_LABEL_COLUMN = 2)
  var lastRow = sheet.getLastRow();
  var lastCol = sheet.getLastColumn();
  var firstDataRow = 7; // SALES_HEADER_ROW = 6, so data starts at 7

  if (lastRow < firstDataRow) {
    throw new Error("No data rows found below the header in Sales.");
  }

  // Find the "Total" row
  var needle = "total";
  var searchRange = sheet.getRange(firstDataRow, 2, lastRow - 6, 1); // Column B
  var colVals = searchRange.getValues().map(function(r) {
    return String(r[0]).trim().toLowerCase();
  });
  var relIdx = colVals.findIndex(function(v) { return v === needle; });

  if (relIdx === -1) {
    throw new Error("Total not found in column B on Sales sheet.");
  }

  var totalRow = firstDataRow + relIdx;

  // Insert a blank row directly above Total
  sheet.insertRowBefore(totalRow);
  var newRow = totalRow;
  var templateRow = newRow - 1;

  if (templateRow < firstDataRow) {
    throw new Error("No template row above the new Sales row.");
  }

  var templateRange = sheet.getRange(templateRow, 1, 1, lastCol);
  var newRange = sheet.getRange(newRow, 1, 1, lastCol);

  // Copy styles for entire row
  templateRange.copyTo(newRange, SpreadsheetApp.CopyPasteType.PASTE_FORMAT, false);

  // Copy ALL data validations
  templateRange.copyTo(newRange, SpreadsheetApp.CopyPasteType.PASTE_DATA_VALIDATION, false);

  // Copy formulas for columns G, I, J (7, 9, 10)
  var formulaCols = [7, 9, 10];
  var templateFormulasR1C1 = sheet.getRange(templateRow, 1, 1, lastCol).getFormulasR1C1()[0];

  formulaCols.forEach(function(col) {
    var f = templateFormulasR1C1[col - 1];
    var target = sheet.getRange(newRow, col, 1, 1);

    if (f && String(f).trim() !== "") {
      var offset = 1 - col; // Column A = 1
      var keyRef = "R[0]C[" + offset + "]";
      var inner = f[0] === "=" ? f.slice(1) : f;
      var wrapped = "=IF(LEN(" + keyRef + ")=0,\"\",IFERROR(" + inner + ",\"\"))";
      target.setFormulasR1C1([[wrapped]]);
    } else {
      target.clearContent();
    }
  });

  return newRow;
}

/**
 * GET request handler (for testing in browser)
 */
function doGet(e) {
  return ContentService.createTextOutput(
    JSON.stringify({
      status: 'ok',
      message: 'Discord Reselling Bot Apps Script is running',
      timestamp: new Date().toISOString()
    })
  ).setMimeType(ContentService.MimeType.JSON);
}
