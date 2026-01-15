from flask import Flask, request, send_file, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
import time
import os

app = Flask(__name__)

# Directory to save PDFs
DOWNLOAD_DIR = "/home/yourusername/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/track', methods=['GET'])
def track():
    tracking_number = request.args.get("number", "").strip()
    if not tracking_number:
        return jsonify({"error": "Tracking number is required"}), 400

    try:
        # ================= DRIVER SETUP =================
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # On PythonAnywhere, Chromedriver path is usually /usr/bin/chromedriver
        driver = webdriver.Chrome(executable_path="/usr/bin/chromedriver", options=options)
        wait = WebDriverWait(driver, 40)

        # ================= OPEN PAGE =================
        driver.get("https://buffaloex.co.za/track.html")

        # ================= SELECT DROPDOWN =================
        dropdown = wait.until(EC.presence_of_element_located((By.TAG_NAME, "select")))
        Select(dropdown).select_by_visible_text("Tracking No.")

        # ================= INPUT TRACKING NUMBER =================
        tracking_input = wait.until(EC.presence_of_element_located((By.ID, "order-no")))
        tracking_input.clear()
        for ch in tracking_number:
            tracking_input.send_keys(ch)
            time.sleep(0.15)

        driver.execute_script("""
        arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
        arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
        arguments[0].dispatchEvent(new Event('keyup', {bubbles:true}));
        arguments[0].blur();
        """, tracking_input)
        time.sleep(0.5)

        # ================= SEARCH =================
        driver.execute_script("""
        document.querySelector('.order-search').dispatchEvent(
            new MouseEvent('click', {bubbles:true})
        );
        """)
        wait.until(EC.visibility_of_element_located((By.ID, "search-result")))

        # ================= SCRAPE DATA =================
        basic_info = []
        info_blocks = driver.find_elements(By.CSS_SELECTOR, "#result-content p.record-ul")
        for block in info_blocks:
            text = block.text.strip()
            if text:
                basic_info.append(text)

        sign_status = driver.find_element(By.CSS_SELECTOR, "#result-content div.record-data").text.strip()

        logistics = []
        records = driver.find_elements(By.XPATH, "//div[@id='result-content']//div[contains(@class,'record-data')]")
        for rec in records[1:]:
            text = rec.text.strip()
            if text:
                logistics.append(text)

        driver.quit()

        # ================= SAVE TO PDF =================
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_name = f"Tracking_{tracking_number}_{timestamp}.pdf"
        pdf_path = os.path.join(DOWNLOAD_DIR, pdf_name)

        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4
        y = height - 40

        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, "BuffaloEx Tracking Report")
        y -= 30

        c.setFont("Helvetica", 11)
        c.drawString(40, y, f"Tracking Number: {tracking_number}")
        y -= 25

        for line in basic_info:
            c.drawString(40, y, line)
            y -= 18

        y -= 15
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, f"Sign Status: {sign_status}")
        y -= 25

        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, "Logistics Records:")
        y -= 25

        c.setFont("Helvetica", 10)
        for record in logistics:
            record = record.replace("\n", " ").strip()
            parts = record.split("GMT+2)")
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                line = part + "GMT+2)"
                if y < 50:
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y = height - 40
                c.drawString(40, y, line)
                y -= 16

        c.save()

        return send_file(pdf_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
