# Signature Submission Testing Guide

## Overview

This guide walks through the complete signature capture and submission flow to verify everything is working end-to-end.

## Part 1: Frontend Verification (Browser Console)

### Step 1a: Open Developer Tools

- Press `F12` (Windows/Linux) or `Cmd+Option+I` (Mac)
- Click on **Console** tab
- Keep this open while testing

### Step 1b: Test Signature Pad Initialization

1. Refresh the page
2. In Console, you should see:

```
[PAGE LOAD] DOMContentLoaded fired
[PAGE LOAD] Initializing Select2...
[PAGE LOAD] [✓] Select2 initialized for linked_item_id
[PAGE LOAD] Initializing signature pads...
[PAGE LOAD] [✓] TSP pad initialized
[PAGE LOAD] [✓] Customer pad initialized
[PAGE LOAD] [✓] BIOMED pad initialized
[PAGE LOAD] [✓] TSP Co-worker pad initialized
[PAGE LOAD] Canvas resizing configured
[PAGE LOAD] Restoring form data...
[PAGE LOAD] Restoring signatures...
[PAGE LOAD] Initialization complete ✓
```

**If you don't see these logs:**

- Check that SignaturePad CDN link is loading
- Check browser Network tab for 404 errors on CDN scripts
- Try a hard refresh (Ctrl+Shift+R)

### Step 1c: Test Signature Drawing & Capture

1. **Fill in mandatory fields:**
   - Item Name: "Test Service Call 123"
   - Service Request Number: Select any option
   - Service Email: your_email@test.com

2. **Draw on TSP Signature Pad:**
   - Click anywhere on the TSP canvas
   - Your cursor should change to a **crosshair**
   - Draw a simple signature (e.g., zigzag)
   - If drawing doesn't work:
     - Check canvas has white background
     - Try a different browser
     - Check CSS in `<head>` for canvas styles

3. **Click "✓ Use Signature" button:**
   - Status below canvas should change to **"✓ Saved"** (green text)
   - Console should show:

   ```
   [SIGNATURE] useSignature("tsp") called
   [SIGNATURE] TSP signature saved (5432 bytes)
   ```

   - The byte count indicates successful base64 encoding

4. **Verify Hidden Input Field:**
   - In Console, run:
   ```javascript
   console.log(document.getElementById("input-tsp").value.substring(0, 50));
   ```

   - Output should start with: `data:image/png;base64,iPV`

**If signature doesn't save:**

- Check console for errors (red text)
- Verify canvas element exists: `document.getElementById('pad-tsp')`
- Make sure you actually drew something (blank canvas = isEmpty() returns true)

### Step 1d: Test Auto-Capture on Submit

1. **Fill in the form again** (different Item Name)
2. **Draw on Customer signature pad** (but DON'T click button)
3. **Immediately click "Submit to Monday.com"**
4. **Console should show:**

```
[FORM SUBMIT] Form submission detected
[FORM SUBMIT] Checking for unsaved signatures...
[FORM SUBMIT] [Customer] Pad empty: false, Input has data: false
[FORM SUBMIT] [Customer] Auto-capturing unsaved signature...
[FORM SUBMIT] [Customer] ✓ Auto-captured (5789 bytes)
[FORM SUBMIT] Total auto-captured: 1
[FORM SUBMIT] === Final Signature State ===
[FORM SUBMIT] Customer: ✓ Has data (5789 bytes)
[FORM SUBMIT] Form ready to submit
```

**This confirms:**

- Form submission handler intercepted the submit
- Detected unsaved signature
- Automatically captured it to hidden input
- Form then submitted with signature data

---

## Part 2: Backend Verification (Flask Server Logs)

### Requirements

- Flask server running (check terminal)
- Form successfully submitted (visible success message on page)

### Where to Look

1. **Terminal where Flask is running**
2. Scroll up to find lines starting with `[SUBMIT]`

### What to Expect

**After form submission, you should see:**

```
================================================================================
[SUBMIT] === NEW FORM SUBMISSION ===
================================================================================
[SUBMIT] Item name: 'Test Service Call 123'
[SUBMIT] Linked ID: '12345'

[DEBUG] === PROCESSING FORM DATA ===
[DEBUG] Processing COL_EMAIL:
  Column ID: a1b2c3d4
  Form Value: 'your_email@test.com'
  Value Type: str
  ✓ FORMATTED TO: {'email': 'your_email@test.com', 'text': 'your_email@test.com'}

... (more field processing) ...

[SUCCESS] Created item with ID: 789456

[SUBMIT] === UPLOADING SIGNATURES ===
[SUBMIT] Processing tsp_signature.png: b64_data=YES, col_id=x1y2z3
[SUBMIT] Processing customer_signature.png: b64_data=YES, col_id=x1y2z4
[SUBMIT] Processing biomed_signature.png: b64_data=NO, col_id=x1y2z5
[SUBMIT] Processing tsp_workwith_signature.png: b64_data=NO, col_id=x1y2z6

[SIGNATURE] Uploading signature to column x1y2z3...
[SIGNATURE] Decoded 5432 bytes for tsp_signature.png
[SIGNATURE] Upload response status: 200
[SIGNATURE] ✓ Successfully uploaded tsp_signature.png

[SIGNATURE] Uploading signature to column x1y2z4...
[SIGNATURE] Decoded 5789 bytes for customer_signature.png
[SIGNATURE] Upload response status: 200
[SIGNATURE] ✓ Successfully uploaded customer_signature.png

[SUBMIT] Uploaded 2 signatures
[SUBMIT] === SIGNATURES COMPLETE ===
```

### Interpretation

| Log Output                    | Meaning                                   |
| ----------------------------- | ----------------------------------------- |
| `b64_data=YES`                | Hidden input had base64 data ✓            |
| `b64_data=NO`                 | Hidden input was empty (user didn't draw) |
| `col_id=x1y2z3`               | Environment variable found ✓              |
| `col_id=None`                 | Environment variable NOT SET ✗            |
| `Upload response status: 200` | Monday.com accepted the file ✓            |
| `Upload response status: 400` | Bad data format or column ID issue        |
| `Upload response status: 401` | Authorization token issue                 |

**If signatures aren't uploading:**

1. Check `b64_data=YES` - if NO, signatures didn't reach backend
   - Fix: Frontend issue (console problem)
2. Check `col_id=x1y2z3` - if None, env var not set
   - Fix: Add to `.env`: `COL_TSP_SIGNATURE=your_column_id`
   - Get column IDs from Monday.com board settings
3. Check `Upload response status` - if not 200
   - Fix: Verify API key and column ID are correct

---

## Part 3: Monday.com Verification

### Step 1: Find Your New Item

1. Log into Monday.com
2. Find your MAIN board (Service Report)
3. Look for the item you just created (search by name)

### Step 2: Check Signature Columns

1. Scroll right to find "TSP Signature" column
2. You should see a **thumbnail of your signature image**
3. Click to expand and verify it's your actual signature
4. Do the same for "Customer Signature" column

### Step 3: Download & Inspect

1. Right-click on signature image
2. Select "Save image as..."
3. Verify it's a valid PNG file (opens in image viewer)

---

## Complete Test Scenario

Follow this exact workflow to verify everything:

### Setup

```
1. Refresh page F5
2. Watch Console for [PAGE LOAD] initialization
3. Fill in form fields:
   - Item Name: "Signature Test - <current date>"
   - Service Request Number: Select any
   - Service Email: test@example.com
```

### Draw & Capture

```
4. Draw on TSP signature pad
5. Click "✓ Use Signature"
6. Verify: Status shows "✓ Saved" (green)
7. Console shows: "[SIGNATURE] TSP signature saved (XXXX bytes)"
```

### Submit

```
8. Click "Submit to Monday.com"
9. Console shows: "[FORM SUBMIT] Total auto-captured: 0"
   (0 because we already captured TSP)
10. Success message appears on page
```

### Monitor Server

```
11. Check Flask terminal logs
12. Look for "[SUBMIT] Processing tsp_signature.png: b64_data=YES"
13. Look for "[SIGNATURE] Upload response status: 200"
```

### Verify

```
14. Log into Monday.com
15. Find your new item
16. Check TSP Signature column contains thumbnail
17. Click to verify it's your signature
```

---

## Troubleshooting Checklist

### Signatures Not Drawing

- [ ] Canvas element visible on page?
- [ ] Cursor changes to crosshair when hovering?
- [ ] Browser is not in "reader mode" or similar?
- [ ] Try different browser (Chrome, Firefox, etc.)?

### "Use Signature" Button Not Working

- [ ] Console shows error (red text)?
- [ ] Status shows "⚠️ Please draw a signature first"?
  - → You need to actually draw something on canvas
- [ ] Console shows "[SIGNATURE] Config not found"?
  - → Pad label doesn't match config (should be "tsp", "customer", etc.)

### Form Submission Issues

- [ ] Green success message appears?
  - NO → Check form required fields are filled
- [ ] Console shows "[FORM SUBMIT]" logs?
  - NO → Check JavaScript loaded properly

### Server Logs Show b64_data=NO

- [ ] Did you click "✓ Use Signature" button?
  - NO → Try clicking it before submit
- [ ] Check Console: Is hidden input empty?
  ```javascript
  console.log(document.getElementById("input-tsp").value);
  ```

  - Should output: `data:image/png;base64,iPV...`

### Signatures Upload but Image is Blank

- [ ] Pad canvas was actually empty when captured?
  - → Draw more visible signature (use larger strokes)
- [ ] Check API response in server logs:
  ```
  [SIGNATURE] Upload response status: 200
  ```

  - If 200 but image blank → likely empty canvas issue

### "Warning: env var not set" in Server Logs

- [ ] Check `.env` file has these variables:
  ```
  COL_TSP_SIGNATURE=your_column_id
  COL_CUSTOMER_SIGNATURE=your_column_id
  COL_BIOMED_SIGNATURE=your_column_id
  COL_TSP_WORKWITH_SIGNATURE=your_column_id
  ```
- [ ] Get correct column IDs from Monday.com board settings
- [ ] Restart Flask after updating `.env`

---

## Quick Debug Commands

Run these in Browser Console:

```javascript
// Check if all hidden inputs have signatures
SIGNATURE_CONFIG.forEach((config) => {
  const input = document.getElementById(config.inputId);
  const hasData = input?.value?.length > 0;
  console.log(
    `${config.label}: ${hasData ? "✓ " + input.value.length + " bytes" : "✗ Empty"}`,
  );
});

// Check if signature pads are initialized
console.log(
  "Pads initialized:",
  Object.keys(pads).length,
  "of",
  SIGNATURE_CONFIG.length,
);

// Check localStorage has signatures
SIGNATURE_CONFIG.forEach((config) => {
  const saved = localStorage.getItem(config.storageKey);
  console.log(
    `${config.storageKey}: ${saved ? "✓ " + saved.length + " bytes" : "✗ Not found"}`,
  );
});

// Manually capture a signature (in case button doesn't work)
// Replace 'tsp' with valid label: 'tsp', 'customer', 'biomed', 'tsp-workwith'
useSignature("tsp");
```

---

## Success Indicators

✅ **All working if you see:**

1. Browser Console shows all [PAGE LOAD] initialization messages
2. Drawing on canvas works (crosshair cursor)
3. "✓ Saved" status appears when clicking button
4. Fleet terminal shows `[SIGNATURE] Upload response status: 200`
5. Monday.com board shows signature thumbnail in column

✗ **Issues if you see:**

- Red error messages in console
- "Please draw a signature first" alert (when you did draw)
- `b64_data=NO` in server logs
- `Upload response status: 400` or `401`
- Blank image in Monday.com even after successful upload
