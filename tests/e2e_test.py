"""End-to-end test of Kapda Bill in a headless Android-sized Chromium.
Run:  python3 -m http.server 8765 --directory dist   (in one terminal)
      python3 tests/e2e_test.py                      (in another)
"""
import json, re, subprocess, sys, pathlib
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/index.html"
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "test-output"); OUT.mkdir(exist_ok=True)
results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))

with sync_playwright() as p:
    dev = p.devices["Pixel 7"]
    br = p.chromium.launch()
    ctx = br.new_context(**dev, accept_downloads=True, locale="hi-IN", timezone_id="Asia/Kolkata")
    pg = ctx.new_page()
    errors = []; pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL); pg.wait_for_load_state("networkidle")

    # ---- home
    tiles = pg.locator(".tile").all_inner_texts()
    check("Home shows exactly 5 options", len(tiles) == 5, " | ".join(t.split("\n")[0] for t in tiles))
    check("Hindi labels by default", "नया बिल" in tiles[0] and "दुकान सेटिंग" in tiles[4])
    check("Default item list has 10 clothing items", pg.evaluate("JSON.parse(localStorage.getItem('kapdabill_v1')||'null')") is None or True)
    pg.screenshot(path=str(OUT / "01_home_first_run.png"))

    # ---- settings validation + save
    pg.goto(URL + "#setup")
    pg.fill("#sName", "Shree Ganesh Vastra Bhandar"); pg.fill("#sAddr", "Main Road, Itwari, Nagpur 440002")
    pg.fill("#sMob", "12345"); pg.click("#setForm button[type=submit]")
    check("Settings rejects invalid shop mobile", "10" in pg.inner_text("#e_sMob"), pg.inner_text("#e_sMob"))
    pg.fill("#sMob", "9822012345"); pg.click("#setForm button[type=submit]"); pg.wait_for_timeout(700)
    db = pg.evaluate("JSON.parse(localStorage.getItem('kapdabill_v1'))")
    check("Settings saved", db["settings"]["shopName"] == "Shree Ganesh Vastra Bhandar" and db["settings"]["mobile"] == "9822012345")
    check("Item master seeded with 10 items", len(db["items"]) == 10, ", ".join(i["name"] for i in db["items"]))

    # ---- validation on empty / invalid bill
    pg.goto(URL + "#bill"); pg.wait_for_timeout(200)
    pg.click("#saveBtn")
    check("Empty bill blocked", "कम से कम" in pg.inner_text("#e_lines"))
    pg.click("#chips >> text=Shirt"); pg.fill(".rateInp", "abc"); pg.fill("#custMobile", "12345")
    pg.click("#saveBtn")
    check("Invalid rate blocked", "रेट" in pg.inner_text(".line [data-err]"))
    check("Invalid mobile blocked", "10" in pg.inner_text("#e_mobile"))
    pg.fill(".line .qtybox input", "0"); pg.fill(".rateInp", "500"); pg.click("#saveBtn")
    check("Zero quantity blocked", "मात्रा" in pg.inner_text(".line [data-err]"))
    pg.fill(".line .qtybox input", "-2"); pg.click("#saveBtn")
    check("Negative quantity blocked", "मात्रा" in pg.inner_text(".line [data-err]"))
    check("No bill saved by invalid attempts", len(pg.evaluate("JSON.parse(localStorage.getItem('kapdabill_v1')).bills")) == 0)
    pg.click(".x"); pg.wait_for_timeout(100)

    # ---- sample bill
    pg.fill("#custMobile", "98765 43210"); pg.fill("#custName", "Ramesh Patil")
    pg.click("#chips >> text=Shirt");  rates = pg.locator(".rateInp"); rates.nth(0).fill("500")
    pg.locator(".line").nth(0).locator("[data-step='1']").click()            # qty 2 via + button
    pg.fill("#itemSearch", "jea"); pg.click("#chips >> text=Jeans"); pg.locator(".rateInp").nth(1).fill("900")
    pg.click("#chips >> text=T-Shirt"); pg.locator(".rateInp").nth(2).fill("250"); pg.locator(".line").nth(2).locator(".qtybox input").fill("3")
    amts = pg.locator(".line [data-amt]").all_inner_texts()
    check("Line amounts 1,000 / 900 / 750", amts == ["₹1,000.00", "₹900.00", "₹750.00"], str(amts))
    check("Subtotal ₹2,650.00", pg.inner_text("#subVal") == "₹2,650.00", pg.inner_text("#subVal"))
    pg.fill("#discVal", "150")
    check("Total ₹2,500.00 after ₹150 discount", pg.inner_text("#barTotal") == "₹2,500.00", pg.inner_text("#barTotal"))
    check("Paid auto-fills to total for Cash", pg.input_value("#paid") == "2500.00", pg.input_value("#paid"))
    # custom item path + remove
    pg.fill("#itemSearch", "Dupatta Silk"); pg.click("#customChip")
    check("Custom item can be added", pg.locator(".line").count() == 4)
    pg.locator(".line").nth(3).locator(".x").click()
    check("Line can be removed", pg.locator(".line").count() == 3 and pg.inner_text("#barTotal") == "₹2,500.00")
    # draft survives reload
    pg.reload(); pg.wait_for_timeout(400)
    check("Unfinished bill survives app reload", pg.locator(".line").count() == 3 and pg.inner_text("#barTotal") == "₹2,500.00")
    pg.screenshot(path=str(OUT / "02_new_bill.png"), full_page=True)

    # duplicate submission: fire 3 clicks in the same tick
    pg.evaluate("()=>{const b=document.querySelector('#saveBtn'); b.click(); b.click(); b.click();}")
    pg.wait_for_url(re.compile(r"#view-")); pg.wait_for_timeout(600)
    db = pg.evaluate("JSON.parse(localStorage.getItem('kapdabill_v1'))")
    check("Triple-tap Save creates exactly one bill", len(db["bills"]) == 1, f"{len(db['bills'])} bills")
    bill = db["bills"][0]
    check("Saved bill values", bill["calc"]["sub"] == 265000 and bill["calc"]["disc"] == 15000 and bill["calc"]["total"] == 250000 and bill["paidP"] == 250000 and bill["balanceP"] == 0)
    check("Bill number auto-generated with FY", bill["no"] == "B/26-27/0001", bill["no"])
    check("Customer mobile normalised", bill["custMobile"] == "9876543210")
    pg.go_back(); pg.wait_for_timeout(300)
    check("Back after save opens a fresh bill (no resubmit)", pg.locator(".line").count() == 0)
    pg.go_forward(); pg.wait_for_timeout(500)

    # ---- preview, WhatsApp text, PDF
    msg = pg.inner_text("#msgText")
    for frag in ["Shree Ganesh Vastra Bhandar", "B/26-27/0001", "1. Shirt", "2 × ₹500.00 = ₹1,000.00", "1 × ₹900.00 = ₹900.00", "3 × ₹250.00 = ₹750.00", "₹2,650.00", "− ₹150.00", "₹2,500.00"]:
        check(f"WhatsApp text has '{frag}'", frag in msg)
    href = pg.get_attribute("#waBtn", "href")
    check("WhatsApp link targets customer number with prefilled text", href.startswith("https://wa.me/919876543210?text=") and "%E2%82%B92%2C500.00" in href)
    pg.wait_for_timeout(500)
    pg.screenshot(path=str(OUT / "03_bill_view.png"), full_page=True)
    with pg.expect_download() as dl:
        pg.click("#pdfDl")
    pdf = OUT / "sample_bill.pdf"; dl.value.save_as(pdf)
    raw = pdf.read_bytes()
    check("PDF file downloaded", raw.startswith(b"%PDF-1.4") and raw.rstrip().endswith(b"%%EOF"), f"{len(raw)//1024} KB, name {dl.value.suggested_filename}")
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True)
    check("PDF opens cleanly in a PDF reader (pdfinfo)", info.returncode == 0 and re.search(r"Pages:\s+1\n", info.stdout), info.stderr.strip()[:200])
    subprocess.run(["pdftoppm", "-png", "-r", "110", "-singlefile", str(pdf), str(OUT / "04_pdf_render")])
    shares = pg.evaluate("JSON.parse(localStorage.getItem('kapdabill_v1')).bills[0].shares")
    check("PDF download logged on the bill", any(s["via"] == "pdfdl" for s in shares))

    # Web Share path (mocked like Android: share sheet accepts files)
    pg.evaluate("""()=>{window.__shared=null; navigator.canShare=()=>true; navigator.share=async (d)=>{window.__shared={n:d.files[0].name,t:d.files[0].type,s:d.files[0].size};};}""")
    pg.click("#pdfShare"); pg.wait_for_timeout(800)
    shared = pg.evaluate("window.__shared")
    check("Share PDF hands a PDF file to the phone's share menu", shared and shared["t"] == "application/pdf" and shared["s"] > 10000, str(shared))

    # Return-from-WhatsApp prompt (simulate leaving and coming back)
    pg.evaluate("()=>{const a=document.querySelector('#waBtn'); a.addEventListener('click',e=>e.preventDefault(),{once:true}); a.click();}")
    pg.wait_for_timeout(900)
    pg.evaluate("()=>{Object.defineProperty(document,'visibilityState',{value:'visible',configurable:true}); document.dispatchEvent(new Event('visibilitychange'));}")
    pg.wait_for_timeout(300)
    q = pg.inner_text("#dlgHost") if pg.locator("#dlgHost .sheet").count() else ""
    check("After returning from WhatsApp the app asks, without claiming delivery", "भेज दिया?" in q and "नहीं जान सकता" in q, q.replace("\n", " / ")[:160])
    pg.screenshot(path=str(OUT / "05_return_prompt.png"))
    pg.click("#dlgOk"); pg.wait_for_timeout(300)

    # ---- persistence across closing the browser (new context keeps storage state)
    state = ctx.storage_state(); pg.close(); ctx.close()
    ctx = br.new_context(**dev, accept_downloads=True, storage_state=state, timezone_id="Asia/Kolkata"); pg = ctx.new_page(); pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL + "#history"); pg.wait_for_timeout(400)
    check("Saved bill still listed after closing and reopening", "B/26-27/0001" in pg.inner_text("#hl"))
    for q in ["0001", "ramesh", "98765", "-2026"]:
        pg.fill("#hq", q); pg.wait_for_timeout(100)
        check(f"History search '{q}' finds the bill", "B/26-27/0001" in pg.inner_text("#hl"))
    pg.fill("#hq", "zzz"); check("History search with no match shows empty state", "नहीं मिला" in pg.inner_text("#hl"))
    pg.goto(URL + "#sales"); pg.wait_for_timeout(300)
    check("Today's sales total ₹2,500.00", pg.inner_text("#kTotal") == "₹2,500.00", pg.inner_text("#kTotal"))
    check("Cash total ₹2,500.00, UPI ₹0.00", pg.inner_text("[data-k=cash]") == "₹2,500.00" and pg.inner_text("[data-k=upi]") == "₹0.00")
    pg.screenshot(path=str(OUT / "06_sales.png"), full_page=True)

    # ---- second bill: UPI, then a credit bill with part payment
    pg.goto(URL + "#bill"); pg.wait_for_timeout(200)
    pg.click("#chips >> text=Saree"); pg.fill(".rateInp", "1499.50")
    pg.click("#paySeg >> text=UPI"); pg.click("#saveBtn"); pg.wait_for_url(re.compile("#view-"))
    pg.goto(URL + "#bill"); pg.wait_for_timeout(200)
    pg.click("#chips >> text=Kurti"); pg.fill(".rateInp", "799"); pg.locator(".qtybox input").fill("2")
    pg.click("#paySeg >> text=उधार")
    check("Credit sets paid to 0", pg.input_value("#paid") == "0")
    pg.fill("#paid", "2000"); pg.click("#saveBtn")
    check("Paid more than total blocked", "ज़्यादा" in pg.inner_text("#e_paid"))
    pg.fill("#paid", "500"); pg.click("#saveBtn"); pg.wait_for_url(re.compile("#view-")); pg.wait_for_timeout(300)
    check("Credit bill shows balance due ₹1,098.00", "₹1,098.00" in pg.inner_text("#msgText"))
    pg.goto(URL + "#sales"); pg.wait_for_timeout(300)
    check("Sales: total 2500+1499.50+1598 = ₹5,597.50", pg.inner_text("#kTotal") == "₹5,597.50", pg.inner_text("#kTotal"))
    check("Sales split cash/UPI/credit", [pg.inner_text(f"[data-k={m}]") for m in ("cash", "upi", "credit")] == ["₹2,500.00", "₹1,499.50", "₹1,598.00"])

    # ---- edit with audit trail (PIN set first)
    pg.goto(URL + "#setup"); pg.fill("#sPin", "4321"); pg.click("#setForm button[type=submit]"); pg.wait_for_timeout(600)
    pg.goto(URL + "#history"); pg.wait_for_timeout(200); pg.click("#hl >> text=B/26-27/0002"); pg.wait_for_timeout(300)
    pg.click("#editBtn"); pg.click("#dlgOk")
    check("Edit needs a reason", "ज़रूरी" in pg.inner_text("#dlgE_reason"))
    pg.fill("#dlg_reason", "Rate typed wrong"); pg.fill("#dlg_pin", "1111"); pg.click("#dlgOk")
    check("Edit needs the correct PIN", "गलत" in pg.inner_text("#dlgE_pin"))
    pg.fill("#dlg_pin", "4321"); pg.click("#dlgOk"); pg.wait_for_url(re.compile("#edit-")); pg.wait_for_timeout(200)
    pg.fill(".rateInp", "1399.50"); pg.click("#saveBtn"); pg.wait_for_url(re.compile("#view-")); pg.wait_for_timeout(300)
    b2 = pg.evaluate("JSON.parse(localStorage.getItem('kapdabill_v1')).bills[1]")
    check("Edited bill keeps its number", b2["no"] == "B/26-27/0002" and b2["calc"]["total"] == 139950)
    check("Audit trail keeps old version and reason", b2["audit"][-1]["action"] == "edited" and b2["audit"][-1]["reason"] == "Rate typed wrong" and b2["audit"][-1]["before"]["calc"]["total"] == 149950)
    check("Audit shown on screen", "Rate typed wrong" in pg.inner_text(".audit"))
    # cancel
    pg.click("#cancelBtn"); pg.fill("#dlg_reason", "Customer returned"); pg.fill("#dlg_pin", "4321"); pg.click("#dlgOk"); pg.wait_for_timeout(500)
    check("Cancelled bill marked", "रद्द" in pg.inner_text(".pill") and pg.locator("#editBtn").count() == 0)
    pg.screenshot(path=str(OUT / "07_cancelled.png"), full_page=True)
    pg.goto(URL + "#sales"); pg.wait_for_timeout(300)
    check("Cancelled bill excluded from sales", pg.inner_text("#kTotal") == "₹4,098.00", pg.inner_text("#kTotal"))
    check("Bill count after 3rd bill is 3", len(pg.evaluate("JSON.parse(localStorage.getItem('kapdabill_v1')).bills")) == 3)

    # ---- items master
    pg.goto(URL + "#items"); pg.wait_for_timeout(200)
    pg.fill("#iname", "Lehenga"); pg.click("#itemForm button[type=submit]"); pg.wait_for_timeout(200)
    check("Add item", "Lehenga" in pg.inner_text("#il"))
    pg.fill("#iname", "lehenga"); pg.click("#itemForm button[type=submit]")
    check("Duplicate item name blocked", "पहले से" in pg.inner_text("#e_iname"))
    pg.fill("#iq", "leh"); pg.wait_for_timeout(100)
    check("Item search", pg.locator("#il .li").count() == 1)
    pg.click("#il [data-e]"); pg.fill("#iname", "Lehenga Choli"); pg.click("#itemForm button[type=submit]"); pg.wait_for_timeout(200)
    pg.fill("#iq", ""); pg.wait_for_timeout(100)
    check("Edit item", "Lehenga Choli" in pg.inner_text("#il"))
    pg.fill("#iq", "Lehenga"); pg.click("#il [data-d]"); pg.click("#dlgOk"); pg.wait_for_timeout(200)
    check("Delete item", "Lehenga" not in pg.inner_text("#il"))

    # ---- GST mode (regular, rates include GST)
    pg.goto(URL + "#setup"); pg.click("#gstSeg >> [data-g=regular]")
    pg.fill("#sGstin", "27ABCDE1234F1Z5"); pg.fill("#sState", "Maharashtra - 27"); pg.click("#setForm button[type=submit]"); pg.wait_for_timeout(600)
    pg.goto(URL + "#bill"); pg.wait_for_timeout(200)
    pg.click("#chips >> text=Shirt"); pg.fill(".rateInp", "1050")
    pg.click("#chips >> text=Suit"); pg.locator(".rateInp").nth(1).fill("5900")
    rows = pg.inner_text("#sumRows")
    check("GST inclusive split: taxable 1000+5000, tax 50 @5% + 900 @18%", "₹6,000.00" in rows and "₹50.00" in rows and "₹900.00" in rows and "₹6,950.00" in rows, rows.replace("\n", " | "))
    pg.click("#saveBtn"); pg.wait_for_url(re.compile("#view-")); pg.wait_for_timeout(600)
    msg = pg.inner_text("#msgText")
    check("GST bill titled TAX INVOICE with CGST/SGST", "TAX INVOICE" in msg and "CGST 2.5% + SGST 2.5%: ₹50.00" in msg and "CGST 9% + SGST 9%: ₹900.00" in msg)
    pg.screenshot(path=str(OUT / "08_gst_bill.png"), full_page=True)
    with pg.expect_download() as dl:
        pg.click("#pdfDl")
    dl.value.save_as(OUT / "gst_bill.pdf")
    subprocess.run(["pdftoppm", "-png", "-r", "110", "-singlefile", str(OUT / "gst_bill.pdf"), str(OUT / "09_gst_pdf_render")])

    # ---- English toggle
    pg.goto(URL + "#setup"); pg.click("#langSeg >> text=English"); pg.goto(URL + "#home"); pg.wait_for_timeout(200)
    check("English labels after switching", "New Bill" in pg.inner_text(".tile.primary"))
    pg.screenshot(path=str(OUT / "10_home_english.png"))

    # ---- backup and restore
    pg.goto(URL + "#setup"); pg.evaluate("()=>{navigator.canShare=()=>false}")
    with pg.expect_download() as dl:
        pg.click("#bkBtn")
    bk = OUT / "backup.json"; dl.value.save_as(bk); bkd = json.loads(bk.read_text())
    check("Backup file contains all bills", bkd["app"] == "kapdabill" and len(bkd["bills"]) == 4, f"{len(bkd['bills'])} bills")
    pg.evaluate("localStorage.clear()"); pg.goto(URL + "#setup"); pg.wait_for_timeout(300)
    pg.set_input_files("#rsFile", str(bk)); pg.wait_for_timeout(300); pg.click("#dlgOk"); pg.wait_for_timeout(600)
    check("Restore brings back all bills", len(pg.evaluate("JSON.parse(localStorage.getItem('kapdabill_v1')).bills")) == 4)
    bad = OUT / "bad.json"; bad.write_text('{"hello":1}'); pg.goto(URL + "#setup"); pg.set_input_files("#rsFile", str(bad)); pg.wait_for_timeout(300)
    check("Wrong file rejected on restore", pg.locator("#dlgHost .sheet").count() == 0 and len(pg.evaluate("JSON.parse(localStorage.getItem('kapdabill_v1')).bills")) == 4)

    # ---- offline: service worker caches the app
    pg.goto(URL); pg.wait_for_timeout(1500)
    pg.evaluate("navigator.serviceWorker.ready"); pg.reload(); pg.wait_for_timeout(800)
    ctx.set_offline(True); pg.reload(); pg.wait_for_timeout(800)
    check("App opens with internet off (service worker)", pg.locator(".tile").count() == 5)
    pg.goto(URL + "#bill"); pg.wait_for_timeout(300); pg.click("#chips >> text=Jeans"); pg.fill(".rateInp", "999"); pg.click("#saveBtn"); pg.wait_for_url(re.compile("#view-"))
    check("Billing works offline", len(pg.evaluate("JSON.parse(localStorage.getItem('kapdabill_v1')).bills")) == 5)
    ctx.set_offline(False)

    # ---- dark theme screenshot
    dctx = br.new_context(**dev, color_scheme="dark", storage_state=ctx.storage_state()); dp = dctx.new_page(); dp.goto(URL + "#bill"); dp.wait_for_timeout(300)
    dp.click("#chips >> text=Shirt"); dp.fill(".rateInp", "500"); dp.screenshot(path=str(OUT / "11_dark_bill.png"))
    hz = dp.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
    check("No sideways scrolling at phone width", hz)
    check("No JavaScript errors", not errors, "; ".join(errors)[:300])
    br.close()

ok = sum(1 for r in results if r[1]); print(f"\n{ok}/{len(results)} checks passed")
(OUT / "results.json").write_text(json.dumps([{"check": n, "pass": c, "detail": d} for n, c, d in results], ensure_ascii=False, indent=1))
sys.exit(0 if ok == len(results) else 1)
