# Hosting and sharing

Environmental data from a mine is confidential. Keep it on your own machine by default.

## A. Your own GitHub repository (code only)
```bash
git init && git add . && git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<you>/underground-mine-environment-monitor.git
git push -u origin main
```
Make the repository **private** if it will ever hold more than the synthetic demo. `.gitignore` excludes `outputs/`, `data/demo/`, `data/real/` and `*.sqlite`; never commit real measurements, the database, or generated reports. On push, GitHub Actions (`.github/workflows/tests.yml`) runs the tests on Ubuntu and Windows (Python 3.10–3.13) plus an end-to-end demo run.

## B. Local only (recommended)
Run `python dashboard_dash.py` with `HOST` left at `127.0.0.1`.

## C. Site network
Set `HOST` to `0.0.0.0` only on a trusted internal network behind your IT access controls. The dashboard has **no login**.

## D. Docker
```bash
docker build -t underground-mine-environment-monitor .
docker run --rm -p 127.0.0.1:8050:8050 -v "$PWD/outputs:/app/outputs" underground-mine-environment-monitor
```
Run `python run_pipeline.py` first so `outputs/environment.sqlite` exists.

## E. Sharing a result
Send `outputs/dashboard_offline.html` and `outputs/environment_report.html` to the authorised team only; both embed your data and are confidential.

## F. Do not
Do not host real data publicly, and do not wire this tool to live control or alarm equipment. It is a reporting aid.
