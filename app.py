
import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import sqlite3
import re
import datetime

# IEEE Thresholds
IEEE_THRESHOLDS = {
    "Power Factor": 2.0,  # %
    "Insulation Resistance": 1000,  # MΩ
    "Turns Ratio Deviation": 0.5,  # %
    "Acetylene": 35,
    "Hydrogen": 100,
    "Methane": 120,
    "Ethylene": 65,
    "Ethane": 65,
    "Carbon Monoxide": 3500,
    "Carbon Dioxide": 10000,
    "Moisture": 35,
    "Acidity": 0.3,
    "Interfacial Tension": 25,
    "Dielectric Breakdown": 30
}

# Safe float conversion
def safe_float(value):
    try:
        return float(value)
    except:
        return None

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

# Extract test data
def extract_test_data(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    results = []

    for page in doc:
        text = page.get_text()

        # Power Factor
        pf_matches = re.findall(r"Power Factor.*?([\d.]+)\s*%", text, re.IGNORECASE)
        for pf in pf_matches:
            value = safe_float(pf)
            if value is not None:
                status = "Pass" if value < IEEE_THRESHOLDS["Power Factor"] else "Fail"
                results.append(("Power Factor", value, status))

        # Insulation Resistance
