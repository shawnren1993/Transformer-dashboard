
import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import sqlite3
import re
import io

# IEEE Thresholds
IEEE_THRESHOLDS = {
    "Power Factor": 2.0,  # %
    "Insulation Resistance": 1000,  # MΩ
    "Turns Ratio Deviation": 0.5,  # %
    "Acetylene": 35,  # ppm
    "Hydrogen": 100,  # ppm
    "Methane": 120,  # ppm
    "Ethylene": 65,  # ppm
    "Ethane": 65,  # ppm
    "Carbon Monoxide": 3500,  # ppm
    "Carbon Dioxide": 10000,  # ppm,
    "Moisture": 35,  # ppm
    "Acidity": 0.3,  # mg KOH/g
    "Interfacial Tension": 25,  # dynes/cm
    "Dielectric Breakdown": 30  # kV
}

# Initialize SQLite database
conn = sqlite3.connect("transformer_tests.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transformer TEXT,
    test_type TEXT,
    value REAL,
    status TEXT,
    date TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS dga_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transformer TEXT,
    gas TEXT,
    value REAL,
    status TEXT,
    date TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS oil_quality (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transformer TEXT,
    parameter TEXT,
    value REAL,
    status TEXT,
    date TEXT
)
""")
conn.commit()

# Function to extract test data from PDF
def extract_test_data(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    results = []

    for page in doc:
        text = page.get_text()

        # Extract Power Factor
        pf_matches = re.findall(r"Power Factor.*?([\d.]+)\s*%", text, re.IGNORECASE)
        for pf in pf_matches:
            value = float(pf)
            status = "Pass" if value < IEEE_THRESHOLDS["Power Factor"] else "Fail"
            results.append(("Power Factor", value, status))

        # Extract Insulation Resistance
        ir_matches = re.findall(r"Insulation Resistance.*?([\d,]+)\s*M?egohms?", text, re.IGNORECASE)
        for ir in ir_matches:
            value = float(ir.replace(",", ""))
            status = "Pass" if value > IEEE_THRESHOLDS["Insulation Resistance"] else "Fail"
            results.append(("Insulation Resistance", value, status))

        # Extract Turns Ratio Deviation
        tr_matches = re.findall(r"Ratio.*?([\d.]+)\s*%?", text, re.IGNORECASE)
        for tr in tr_matches:
            value = float(tr)
            status = "Pass" if abs(value) < IEEE_THRESHOLDS["Turns Ratio Deviation"] else "Fail"
            results.append(("Turns Ratio Deviation", value, status))

    return results

# Function to extract DGA and oil analysis
def extract_dga_oil_data(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    dga_results = []
    oil_results = []

    for page in doc:
        text = page.get_text()

        # DGA gases
        for gas in ["Acetylene", "Hydrogen", "Methane", "Ethylene", "Ethane", "Carbon Monoxide", "Carbon Dioxide"]:
            match = re.search(rf"{gas}.*?([\d.]+)\s*ppm", text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                status = "Pass" if value < IEEE_THRESHOLDS[gas] else "Fail"
                dga_results.append((gas, value, status))

        # Oil quality parameters
        oil_params = {
            "Moisture": r"Moisture.*?([\d.]+)\s*ppm",
            "Acidity": r"Acidity.*?([\d.]+)\s*mg",
            "Interfacial Tension": r"Interfacial Tension.*?([\d.]+)\s*dynes",
            "Dielectric Breakdown": r"Dielectric Breakdown.*?([\d.]+)\s*kV"
        }
        for param, pattern in oil_params.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                status = "Pass" if value >= IEEE_THRESHOLDS[param] else "Fail"
                oil_results.append((param, value, status))

    return dga_results, oil_results

# Streamlit UI
st.title("Transformer Testing Dashboard")
st.write("Upload transformer test reports (PDF) to assess and compare against IEEE standards.")

uploaded_file = st.file_uploader("Upload PDF Report", type=["pdf"])

if uploaded_file:
    transformer_name = st.text_input("Transformer Identifier", value="Unit 3 GSU")
    test_date = st.date_input("Test Date")

    pdf_bytes = uploaded_file.read()
    test_data = extract_test_data(pdf_bytes)
    dga_data, oil_data = extract_dga_oil_data(pdf_bytes)

    st.subheader("Assessment Results")
    df = pd.DataFrame(test_data, columns=["Test Type", "Value", "Status"])
    st.dataframe(df)

    # Save to database
    for test_type, value, status in test_data:
        cursor.execute("INSERT INTO test_results (transformer, test_type, value, status, date) VALUES (?, ?, ?, ?, ?)",
                       (transformer_name, test_type, value, status, str(test_date)))
    for gas, value, status in dga_data:
        cursor.execute("INSERT INTO dga_results (transformer, gas, value, status, date) VALUES (?, ?, ?, ?, ?)",
                       (transformer_name, gas, value, status, str(test_date)))
    for param, value, status in oil_data:
        cursor.execute("INSERT INTO oil_quality (transformer, parameter, value, status, date) VALUES (?, ?, ?, ?, ?)",
                       (transformer_name, param, value, status, str(test_date)))
    conn.commit()
    st.success("Results saved to database.")

    # Historical Data
    st.subheader("Historical Data")
    cursor.execute("SELECT transformer, test_type, value, status, date FROM test_results WHERE transformer = ?", (transformer_name,))
    rows = cursor.fetchall()
    hist_df = pd.DataFrame(rows, columns=["Transformer", "Test Type", "Value", "Status", "Date"])
    st.dataframe(hist_df)

    # Trending Chart
    st.subheader("Trending Chart")
    selected_test = st.selectbox("Select Test Type", df["Test Type"].unique())
    trend_df = hist_df[hist_df["Test Type"] == selected_test]
    trend_df["Date"] = pd.to_datetime(trend_df["Date"])
    trend_df = trend_df.sort_values("Date")
    st.line_chart(trend_df.set_index("Date")["Value"])

conn.close()
