# Kapda Bill (कपड़ा बिल) — mobile billing app for a clothing shop

A working Progressive Web App (PWA). The shop owner makes a bill on an Android phone, saves it, and sends it to the customer on WhatsApp as a text message or a PDF. No computer, printer, login, subscription or WhatsApp Business API is needed for daily use.

## What is in this folder

| Path | What it is |
|---|---|
| `dist/` | **The app, ready to upload.** `index.html`, `manifest.json`, `sw.js` (offline support) and icons. |
| `src/app.html` | Source of the whole app (HTML + CSS + JavaScript, no frameworks, no outside libraries). |
| `build.py` | Rebuilds `dist/` from `src/app.html` (needs Python 3 + Pillow). |
| `tests/e2e_test.py` | 75 automated checks run in a headless Android-sized Chrome (Playwright). |
| `test-results/` | Screenshots, sample PDFs and `results.json` from the last test run. |

## 1. Put the app online once (free) — done from any computer, one time only

A PWA must be served over **https** to install on a phone and work offline. Any free static host works. Two simple choices:

**Option A — Netlify (easiest)**
1. Create a free account at netlify.com.
2. Open *Sites → Add new site → Deploy manually*.
3. Drag the **`dist`** folder onto the page. You get an address like `https://kapda-bill-xyz.netlify.app`.
4. (Optional) Rename the site to something like `ganesh-vastra-bill`.

**Option B — GitHub Pages**
1. Create a free GitHub account and a new public repository.
2. Upload the files from `dist/` (not the folder itself) to the repository.
3. *Settings → Pages → Branch: main / root → Save*. Address: `https://<username>.github.io/<repo>/`.

**Important:** keep using the same address forever. The bills are stored by the browser *per website address*; if the address changes, the phone shows an empty app (restore from a backup file to bring the data across).

Cost: ₹0. A custom domain (optional) costs about the price of a domain name per year.

## 2. Install on the Android phone

1. Open the address in **Google Chrome** on the shop owner's phone.
2. Tap the **⋮** menu → **Add to Home screen / Install app** → **Install**.
3. A "कपड़ा बिल" icon appears on the home screen. It opens full-screen like a normal app and works **without internet** after the first open.

## 3. First-time setup (5 minutes)

1. Open **दुकान सेटिंग (Shop Settings)**:
   - Shop name, address, mobile number, logo (optional), thank-you message, footer line.
   - **Bill numbering:** prefix (default `B/`), add financial year (gives `B/26-27/0001`), restart from 1 every 1 April, next bill number, number of digits. A live preview shows the next number and warns if it is longer than the 16 characters GST allows.
   - **GST:** choose *Not GST registered* (default; bill is titled "बिल / BILL"), *GST registered (regular)* (titled "TAX INVOICE", shows GSTIN, taxable value, CGST/SGST or IGST), or *Composition scheme* (titled "BILL OF SUPPLY" with the composition declaration, no tax charged). For regular GST you can choose whether rates include GST.
   - **PIN (optional):** 4 digits needed to edit or cancel a saved bill.
   - **Language:** हिंदी (default) or English.
   - Tap **सेटिंग सेव करें**.
2. Open **सामान सूची (Item List)**: the 10 sample items are already there. Add, rename, search or delete items. No fixed price is stored — the rate is typed on every bill. When GST is on, each item can carry an HSN code and a default GST rate.

## 4. Daily use

**New bill (about 30 seconds):** tap **नया बिल** → type customer's WhatsApp number (name optional) → tap item chips (or type a new item name and tap *जोड़ें*) → set quantity with − / + and type the rate → optional discount in ₹ or % → choose नकद / UPI / कार्ड / उधार (paid amount fills itself; change it for part payment and the balance is shown) → **बिल सेव करें**.

**Send:**
- **WhatsApp पर बिल भेजें** opens WhatsApp straight into the customer's chat with the full item-wise bill typed in. The owner taps send in WhatsApp.
- **PDF शेयर करें** opens Android's share menu with the PDF; choose WhatsApp and the customer.
- **PDF डाउनलोड** saves the PDF to the phone.
- When the owner comes back from WhatsApp, the app asks "क्या ग्राहक को बिल भेज दिया?" and records only what the owner answers. The app never claims a message was delivered or read — it cannot know that.

**पुराने बिल (Bill History):** search by bill number, customer name, mobile or date (`29-10-2026`); open any bill to view, re-send on WhatsApp, or download the PDF again. **Edit** and **Cancel** need a written reason (and the PIN, if set). The bill number stays the same, the old version is kept, and every change, cancellation and share is listed under *बदलाव का रिकॉर्ड*. Cancelled bills stay in history with a "रद्द / CANCELLED" stamp and are left out of sales totals.

**आज की बिक्री (Today's Sales):** pick any date; shows total sales, number of bills, cash / UPI / card / credit totals, amount received, credit outstanding, discount given, total GST (when on), the day's bills and a 7-day table. "सारांश WhatsApp करें" sends the day's summary to anyone (e.g. the owner's accountant).

## 5. Where the data lives — and backup (please read)

- Bills, items and settings are saved **only on this phone**, inside Chrome's storage for the app address. They survive closing the app and restarting the phone (tested).
- They are **lost** if the phone is lost or reset, the app/Chrome data is cleared, or the site address changes.
- There is **no automatic cloud backup**. Instead: *Shop Settings → बैकअप फ़ाइल बनाएँ* creates a backup file and opens the share menu — send it to Google Drive or to your own WhatsApp. The home screen reminds the owner if no backup was made in 7 days.
- To move to a new phone: install the app, *Shop Settings → बैकअप से वापस लाएँ*, choose the backup file.
- **One phone only.** Two phones using the app keep separate bill books and separate bill numbers. Sharing one live bill book across phones needs a cloud database with login (for example Firebase or Supabase, both have free tiers for a shop this size) — that is a separate piece of work.

## 6. GST notes (for the shop's CA)

- Calculations are done in paise (whole numbers) so totals are exact to two decimals. Discount is spread over the lines in proportion to their value before tax.
- *Rates include GST* (default, as most shops quote): taxable value = line amount × 100 / (100 + rate); tax = line amount − taxable value. Otherwise tax is added on top.
- CGST and SGST are each half the tax (odd paise go to SGST). Tick *दूसरे राज्य का ग्राहक* on the bill for IGST.
- **Auto** GST rate on clothing lines: 5% when the per-piece value is up to ₹2,500, otherwise 18% (the rates in force since 22 September 2025). Saree and Dress Material default to 5% (fabric). Every line's rate can be changed by hand. HSN codes are left blank on purpose — fill them in Item List after confirming with the CA.
- The PDF is an image-based single page (keeps Hindi text correct on every phone); its text cannot be selected or searched.
- E-invoicing (IRN/QR) is not implemented; small retail shops selling to consumers are normally below that requirement.

## 7. Optional: fully automatic WhatsApp sending (not built, not needed)

Sending bills automatically without the owner tapping *Send* needs the **WhatsApp Business Platform (Cloud API)** from Meta: a verified Facebook Business account, a phone number dedicated to the API, pre-approved message templates, a small server to call the API, and **per-message charges from Meta** (see Meta's current pricing page for India). This app deliberately uses the free "click to chat" link and the phone's share menu instead.

## 8. Tested — and what still needs testing on a real phone

Automated (headless Chrome emulating a Pixel 7, 75/75 checks pass): the sample bill (Shirt 2×500, Jeans 1×900, T-Shirt 3×250, discount ₹150 → subtotal ₹2,650, total ₹2,500) in the screen, saved bill, WhatsApp text, PDF and sales summary; empty bill, zero/negative/non-numeric quantity and rate, wrong mobile, overpayment; triple-tap Save creating exactly one bill; draft surviving reload; data surviving browser close; history search; edit/cancel with reason, PIN and audit trail; item add/edit/delete/duplicate; GST inclusive split; English mode; backup and restore; offline use; no sideways scrolling; no script errors.

Not testable here and to be checked once on the owner's phone: that Chrome offers *Install*, that WhatsApp opens from the green button, and that the share menu passes the PDF to WhatsApp. These use standard Android features (wa.me links and the Web Share API in Chrome) and are mocked in the tests.

## Rebuild / run tests

```bash
pip install pillow playwright && playwright install chromium
python3 build.py                                   # regenerate dist/
python3 -m http.server 8765 --directory dist &     # serve locally
python3 tests/e2e_test.py test-results             # run the 75 checks
```
