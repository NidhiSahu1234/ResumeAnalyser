# Contributing to CareerFit AI

Thank you for considering a contribution to CareerFit AI. The app is built with Python and Streamlit, and the explainable job matcher lives in `matching/`.

## Local development

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest
streamlit run app.py
```

Keep API keys in ignored environment files or a secret manager. Do not commit resumes, SQLite databases, exports, credentials, or other personal data. For matching changes, add tests for the pure functions in `matching/` and keep the heuristic transparent.

Open a pull request against [NidhiSahu1234/ResumeAnalyser](https://github.com/NidhiSahu1234/ResumeAnalyser) with a concise description and the checks you ran. Preserve the upstream attribution and terms in `LICENSE`.
