# Deployment guide

CareerFit AI is a Streamlit application. Streamlit Community Cloud is the simplest host to evaluate first; no hosting project has been created and there is no verified public URL yet.

## Before deployment

1. Review the repository's existing database and spreadsheet files and Git history. The target repository has previously contained these data artifacts; `.gitignore` cannot remove tracked files or erase old versions.
2. Do not deploy with real resume data in a public or shared SQLite database. The legacy analyzer and builder can save resume details only after a user opts in, but SQLite files are not encrypted and the app has no end-user accounts.
3. Decide whether to disable database-backed features or replace local SQLite with private, access-controlled storage before inviting real users. Do not use paid services without approval.
4. Add `GOOGLE_API_KEY` only if you intend to enable Gemini analysis. The job-match feature works without it. Store the key in the host's secret manager, never in source control.
5. Review all dependencies and the required Chromium system packages in `packages.txt` for the selected host.

## Streamlit Community Cloud

1. Sign in to Streamlit Community Cloud and connect the intended GitHub repository.
2. Select the repository's deployment branch and set the application entry point to `app.py`.
3. Add Python dependencies from `requirements.txt`. If using job-search browser automation, also confirm the host supports the Chromium packages listed in `packages.txt`.
4. If Gemini analysis is enabled, add `GOOGLE_API_KEY` in the app's Secrets settings as a TOML string, for example:

   ```toml
   GOOGLE_API_KEY = "your_key_here"
   ```

5. Deploy and inspect the application logs without sharing resume text or secret values.
6. Verify the landing page, PDF/DOCX upload, job comparison, skill gaps, bullet feedback, report download, and missing-key behavior with a fictional sample resume.
7. Add the actual public URL to `README.md` only after those checks pass.

The job-match history exists only for a visitor's current app session. Files written to a hosted instance's local filesystem may be lost when the instance restarts or redeploys; do not treat local SQLite as durable storage.

Official setup references: [deploy an app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [configure secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management), and [declare dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).

## Local run

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

For Gemini locally, copy `utils/.env.example` to `.env` and set the key there. The `.env` file is ignored by Git.
