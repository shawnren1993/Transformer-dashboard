import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import sqlite3
import re

# IEEE Thresholds
IEEE_THRESHOLDS = {
    "Power Factor": 2.0,  # %
    "Insulation Resistance": 1000,  # MΩ
    "Turns Ratio Deviation": 0.5  # %
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
conn.commit()

# Function to safely convert to float
def safe_float(value):
    try:
        return float(value)
    except:
        return None

# Function to extract test data from PDF
def extract_test_data(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    results = []
    skipped = []

    for page in doc:
        text = page.get_text()

        # Extract Power Factor
        pf_matches = re.findall(r"Power Factor.*?([\d.]+)\s*%", text, re.IGNORECASE)
        for pf in pf_matches:
            value = safe_float(pf)
            if value is not None:
                status = "Pass" if value < IEEE_THRESHOLDS["Power Factor"] else "Fail"
                results.append(("Power Factor", value, status))
            else:
                skipped.append(("Power Factor", pf))

        # Extract Insulation Resistance
        ir_matches = re.findall(r"Insulation Resistance.*?([\d,]+)\s*M?egohms?", text, re.IGNORECASE)
        for ir in ir_matches:
            value = safe_float(ir.replace(",", ""))
            if value is not None:
                status = "Pass" if value > IEEE_THRESHOLDS["Insulation Resistance"] else "Fail"
                results.append(("Insulation Resistance", value, status))
            else:
                skipped.append(("Insulation Resistance", ir))

        # Extract Turns Ratio Deviation
        tr_matches = re.findall(r"Ratio.*?([\d.]+)\s*%?", text, re.IGNORECASE)
        for tr in tr_matches:
            value = safe_float(tr)
            if value is not None:
                status = "Pass" if abs(value) < IEEE_THRESHOLDS["Turns Ratio Deviation"] else "Fail"
                results.append(("Turns Ratio Deviation", value, status))
            else:
                skipped.append(("Turns Ratio Deviation", tr))

    return results, skipped

# Streamlit UI
st.title("Transformer Testing Dashboard")
st.write("Upload transformer test reports (PDF) to assess and compare against IEEE standards.")

uploaded_file = st.file_uploader("Upload PDF Report", type=["pdf"])

if uploaded_file:
    transformer_name = st.text_input("Transformer Identifier", value="Unit 3 GSU")
    test_date = st.date_input("Test Date")

    pdf_bytes = uploaded_file.read()
    test_data, skipped_data = extract_test_data(pdf_bytes)

    st.subheader("Assessment Results")
    df = pd.DataFrame(test_data, columns=["Test Type", "Value", "Status"])
    st.dataframe(df)

    # Notify user of skipped values
    if skipped_data:
        st.warning("Some values were skipped due to formatting issues:")
        skipped_df = pd.DataFrame(skipped_data, columns=["Test Type", "Raw Value"])
        st.dataframe(skipped_df)

    # Save to database
    for test_type, value, status in test_data:
        cursor.execute("INSERT INTO test_results (transformer, test_type, value, status, date) VALUES (?, ?, ?, ?, ?)",
                       (transformer_name, test_type, value, status, str(test_date)))
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
