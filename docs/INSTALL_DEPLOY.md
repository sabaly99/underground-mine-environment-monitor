# Install and deploy

Python 3.10–3.13 on Linux, macOS or Windows. No internet is needed after installation, nor at run time.

## 1. Install
```bash
git clone <your-repository-url> underground-mine-environment-monitor
cd underground-mine-environment-monitor
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Air-gapped machine: on a connected computer run `pip download -r requirements.txt -d wheels`, copy `wheels` over, then `pip install --no-index --find-links wheels -r requirements.txt` (same OS and Python version).

## 2. Configure
Each script has a `CONFIG` block at the top; edit it, then run. No command-line arguments.
- `run_pipeline.py`: input folder/files, `AS_OF` (`"now"`, `"auto"` or a timestamp), outputs, `ENV` method settings (timezone, stale/gap factors, plausibility bounds).
- `dashboard_dash.py`, `dashboard_streamlit.py`: database path and `DEFAULT_THEME` (midnight, daylight, ocean, forest, sand, contrast); (host/port for Dash). Users can switch theme live; the single-file dashboard and Dash remember the choice in the browser.
- `make_demo_data.py`, `make_manual_entry_form.py`.

For live use set `AS_OF` to `"now"`; the demo uses a fixed time so its scenarios stay reproducible. Nothing in `ENV` is a safety limit.

## 3. Run
```bash
python run_pipeline.py                  # analyse + history + report + offline dashboard + manual form
python dashboard_dash.py                # offline Dash dashboard, http://127.0.0.1:8050
streamlit run dashboard_streamlit.py    # optional
```
Or just open `outputs/dashboard_offline.html` and `outputs/environment_report.html` in a browser.

## 4. Windows desktop
After install, double-click `run_dashboard.bat`.

## 5. Updating
Re-run `run_pipeline.py` as new files arrive. Raw measurements accumulate in `outputs/environment.sqlite` (identical duplicate rows are ignored, so re-running is safe); all derived results are rebuilt from the full history. Back the database up like any record.

## 6. Tests
```bash
pip install -r requirements-dev.txt
python -m pytest -q
```
