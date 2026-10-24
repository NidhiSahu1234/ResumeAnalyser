# CareerFit AI

CareerFit AI is a Streamlit workspace for reviewing resumes, comparing them with a job posting, and preparing a tailored resume. Its job-match estimate is explainable and heuristic; it is not an official ATS score.

**Repository:** [NidhiSahu1234/ResumeAnalyser](https://github.com/NidhiSahu1234/ResumeAnalyser)  
**Live application:** Not deployed yet.

## Screenshots

Screenshots of the current application will be added after a verified deployment.

## Features

- Resume analysis for a selected role, with structure, formatting, skill, and recommendation feedback.
- Optional Google Gemini analysis. It requires a configured API key and explicit consent before resume text is sent to Google.
- Resume builder with Modern, Professional, Minimal, and Creative templates.
- Explainable resume-to-job comparison with required and preferred skills, evidence excerpts, date-based experience estimates, and actionable gaps.
- Bullet feedback that preserves the candidate's facts. Automatic rewrites only rephrase eligible opening phrases.
- Up to 20 session-only job-match snapshots with score and skill-gap comparison. History stores comparison metadata, never resume or job-description text.
- Role-based learning resources, a dashboard, job search, and feedback pages.
- PDF and DOCX input for job matching (maximum 5 MB) and downloadable Markdown reports.

The job-match page uses deterministic, offline rules and works without an AI key. Skills outside its built-in vocabulary and soft skills are not scored. Related skills are suggestions, not matches.

## Technology

- Python and Streamlit
- SQLite for optional resume-builder/dashboard data
- pandas and Plotly for analysis views
- pypdf/pdfplumber and python-docx for document handling
- Google Gemini through `google-generativeai` for the optional AI analyzer
- Selenium and Chromium for job-search features that need browser automation

## Local setup

Python 3.10 or newer is recommended.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item utils/.env.example .env
streamlit run app.py
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`. The job-match feature needs no external services. To use AI analysis locally, set `GOOGLE_API_KEY` in `.env`; never commit that file. A key is optional for all other features.

## Configuration and data handling

- AI analysis sends the extracted resume text and any job description to Google Gemini after the user checks the consent box. Review Google's terms and data practices before enabling it.
- The two legacy analyzer and builder pages offer an unchecked-by-default option to save resume details in the app's local SQLite database. The database is not encrypted and this app does not provide separate end-user accounts.
- Job-match history lasts for the current Streamlit session only. The downloadable history includes role labels, scores, and skill gaps, not resume text.
- The repository has previously contained database and spreadsheet files. Review repository contents and history before publishing or deploying any copy; `.gitignore` does not remove files already tracked by Git.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for Streamlit Community Cloud setup. A public URL will be added here only after the deployed application and its main flow have been verified.

## License and attribution

This project builds on the open-source Smart AI Resume Analyzer originally authored by Het Patel. The original [MIT license](LICENSE) and its attribution are retained.
