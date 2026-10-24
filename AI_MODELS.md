# Optional AI analysis

CareerFit AI has one implemented external AI provider: Google Gemini, accessed through the `google-generativeai` package. AI analysis is optional. Resume-versus-job matching uses deterministic local rules and does not need a provider key.

## Configuration

For local development, copy `utils/.env.example` to `.env` and set `GOOGLE_API_KEY`. For Streamlit hosting, put the key in the application's secret manager. The app reads the key from the process environment first and then from Streamlit secrets. Do not commit a real key or include it in logs.

If the key is missing or the provider is unavailable, AI analysis should report the configuration or request failure; it must not substitute a fabricated analysis. The job-match page remains available.

## Data sent to Google

When a user explicitly agrees and runs AI analysis, the extracted resume text and an optional job description are sent to Google Gemini. Review the provider's current terms and data practices before enabling the feature for real candidate data.

## Upstream attribution

This project is derived from Smart AI Resume Analyzer by Het Patel. The original license and attribution are retained in [LICENSE](LICENSE).
