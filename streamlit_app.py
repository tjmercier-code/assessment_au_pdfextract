import io
import re
from typing import Optional, List, Dict
import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader

st.set_page_config(page_title="AU PDF Extractor", layout="wide")
st.title("AU PDF Extractor (USGS-style)")

st.markdown("""
Upload one or more PDFs and get a CSV with:
- AU_Name, AU_Number (from first page)
- For each section page — Oil/Gas/NGL in Oil Fields; Gas/Liquids in Gas Fields:
  - Mean (from *Statistics*, line under **Trials = 50 000**)
  - F95, F50, F5 (from *Percentiles → Forecast Values*, 19-number monotone window)
""")

SECTIONS = {
    "Oil in Oil Fields": "OIL",
    "Gas in Oil Fields": "AG",
    "NGL in Oil Fields": "AGL",
    "Gas in Gas Fields": "NAGAS",
    "Liquids in Gas Fields": "NAGL",
}

def norm_num_token(s: str) -> Optional[float]:
    if s is None:
        return None
    s2 = s.replace("×10", "e").replace(" ", "").replace(",", "")
    s2 = re.sub(r"(?<!e|E)[^0-9.\-+]+$", "", s2)
    try:
        return float(s2)
    except Exception:
        return None

def page_text(reader: PdfReader, i: int) -> str:
    txt = reader.pages[i].extract_text()
    return txt or ""

def find_page_soft(reader: PdfReader, title: str) -> Optional[int]:
    patt = re.compile(r"\b" + re.escape(title).replace(r"\ ", r"\s+") + r"\b", re.IGNORECASE)
    for i in range(len(reader.pages)):
        if patt.search(page_text(reader, i)):
            return i
    return None

def stats_mean(text: str) -> Optional[float]:
    m = re.search(r"Statistics\s*:(.*?)(?:Percentiles\s*:|Figure|Table|$)", text, re.IGNORECASE | re.DOTALL)
    block = m.group(1) if m else text
    mt = re.search(r"Trials", block, re.IGNORECASE)
    if not mt:
        return None
    lines = block[mt.end():].splitlines()
    trials_idx = None
    for i, ln in enumerate(lines[:150]):
        if re.sub(r"[^\d]", "", ln) == "50000" or re.search(r"\b5\s*0\s*0\s*0\s*0\s*0\b", ln):
            trials_idx = i
            break
    if trials_idx is None:
        return None
    for j in range(trials_idx+1, min(trials_idx+20, len(lines))):
        mnum = re.search(r"[-+]?\d[\d\s,]*\.?\d*(?:e[-+]?\d+)?", lines[j])
        if mnum:
            val = norm_num_token(mnum.group(0))
            if val is not None:
                return val
    return None

def percentiles_seq(text: str) -> List[float]:
    m = re.search(r"Percentiles\s*:(.*?)(?:Figure|Table|$)", text, re.IGNORECASE | re.DOTALL)
    if not m:
        return []
    block = m.group(1)
    mfv = re.search(r"Forecast\s*Values", block, re.IGNORECASE)
    if not mfv:
        return []
    after = block[mfv.end():][:2000]
    nums = re.findall(r"[-+]?\d[\d\s,]*\.?\d*(?:e[-+]?\d+)?", after)
    vals = []
    for n in nums:
        v = norm_num_token(n)
        if v is not None:
            vals.append(v)
    best = None
    for i in range(0, max(0, len(vals)-18)):
        window = vals[i:i+19]
        if all(window[k] <= window[k+1] for k in range(18)):
            if best is None or window[0] < best[0]:
                best = window
    return best or []

def first_page_fields(text: str):
    m_num = re.search(r"AU\s*Number\s*:\s*([\d\s,]+)", text, re.IGNORECASE)
    au_number = re.sub(r"\D", "", m_num.group(1)) if m_num else None
    m_name = re.search(r"AU\s*Name\s*:\s*(.+)", text, re.IGNORECASE)
    au_name = m_name.group(1).strip() if m_name else None
    return au_name, au_number

def parse_one(file_bytes: bytes, filename: str) -> Dict[str, Optional[float] or str]:
    reader = PdfReader(io.BytesIO(file_bytes))
    row = {"AU_Name": None, "AU_Number": None,
           "OIL_F95_MMB": None, "OIL_F50_MMB": None, "OIL_F5_MMB": None, "OIL_MN_MMB": None,
           "AG_F95_MMB": None, "AG_F50_MMB": None, "AG_F5_MMB": None, "AG_MN_MMB": None,
           "AGL_F95_MMB": None, "AGL_F50_MMB": None, "AGL_F5_MMB": None, "AGL_MN_MMB": None,
           "NAGAS_F95_MMB": None, "NAGAS_F50_MMB": None, "NAGAS_F5_MMB": None, "NAGAS_MN_MMB": None,
           "NAGL_F95_MMB": None, "NAGL_F50_MMB": None, "NAGL_F5_MMB": None, "NAGL_MN_MMB": None,
           "_file": filename}

    first = page_text(reader, 0)
    au_name, au_number = first_page_fields(first)
    row["AU_Name"], row["AU_Number"] = au_name, au_number

    for title, prefix in SECTIONS.items():
        idx = find_page_soft(reader, title)
        if idx is None:
            continue
        txt = page_text(reader, idx)
        mean = stats_mean(txt)
        seq  = percentiles_seq(txt)
        row[f"{prefix}_MN_MMB"]  = mean
        if seq and len(seq) == 19:
            row[f"{prefix}_F95_MMB"] = seq[0]
            row[f"{prefix}_F50_MMB"] = seq[9]
            row[f"{prefix}_F5_MMB"]  = seq[18]
    return row

uploads = st.file_uploader("Drop one or more PDFs", type=["pdf"], accept_multiple_files=True)
if uploads:
    rows = []
    for f in uploads:
        try:
            rows.append(parse_one(f.read(), f.name))
            st.success(f"Parsed {f.name}")
        except Exception as e:
            st.error(f"Failed {f.name}: {e}")
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"),
                           file_name="au_extraction.csv", mime="text/csv")
else:
    st.info("Upload PDFs to extract AU fields and section fractiles/mean.")
