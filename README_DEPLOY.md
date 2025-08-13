# AU PDF Extractor (Streamlit)

Deploy this app online with **Streamlit Community Cloud** or **Hugging Face Spaces**.

## Files
- `app.py` — Streamlit app (single file)
- `requirements.txt` — Python deps

## Deploy on Streamlit Community Cloud (free)
1. Create a new GitHub repo and add `app.py` and `requirements.txt`.
2. Go to https://share.streamlit.io, connect your repo, and choose `app.py` as the entry file.
3. Click **Deploy**.

## Deploy on Hugging Face Spaces
1. Create a new **Space** → **Streamlit**.
2. Upload `app.py` and `requirements.txt`.
3. The Space will build and run automatically.

## Usage
- Upload one or more USGS-style AU PDFs.
- The app extracts:
  - `AU_Name`, `AU_Number` (from first page)
  - For each section page (Oil/Gas/NGL in Oil Fields; Gas/Liquids in Gas Fields):
    - `MN` from *Statistics* (line under **Trials = 50 000**)
    - `F95`, `F50`, `F5` from *Percentiles → Forecast Values* (monotone 19-number window)
- Download the consolidated CSV.

### Notes
- This app uses **vector text parsing** only (no OCR) — ideal for native PDFs with selectable text.
- If you need OCR fallback, deploy locally with the CLI version (requires Tesseract + Poppler) or ask me to adapt the Space to include OCR (a bit heavier).
