# WattWise — Smart Energy Digital Twin

Academic software prototype for **Cloud-Enabled IoT Smart Energy Monitoring Using Digital Twin Technology**.

## Included
- Responsive dashboard and virtual energy-system illustration
- Flask backend and SQLite persistence
- Simulated readings: normal, high-load, and energy-imbalance scenarios
- Chart comparing source energy and downstream load
- Rule-based alerts for aggregate difference, configured power limit, and elevated simulated temperature
- Estimated carbon emissions using a configurable factor
- CSV export, editable demo thresholds, and reset function

## Important limitations
This is a **local software simulation**, not a deployed cloud service and not connected to physical IoT hardware. Every reading is simulated. Energy differences are signals to investigate and do not prove theft. The default carbon factor `0.70 kg CO₂e/kWh` is an illustrative placeholder, not an official current Indian grid factor; replace it with an appropriate cited source and record source/year before submitting the report. Demo thresholds are not validated engineering limits. Do not connect a prototype directly to mains electricity; future hardware work requires appropriate isolated sensors, protection, and qualified supervision.

## Run in Antigravity IDE (Windows / Python 3.12)
1. Extract this ZIP to a normal folder, such as `D:\\Smart_Energy_Digital_Twin`.
2. Open the extracted folder in Antigravity IDE.
3. Open the integrated PowerShell terminal and run:

   ```powershell
   py -3.12 -m venv .venv
   .\\.venv\\Scripts\\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   python app.py
   ```

   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again.

4. Visit `http://127.0.0.1:5000`. Health check: `http://127.0.0.1:5000/api/health`.
5. Stop the server with `Ctrl+C`.

Chart.js and Google Fonts load from CDNs, so those visual extras need internet access. Flask and the local SQLite database run on your computer.

## Project structure
```text
Smart_Energy_Digital_Twin/
├── app.py
├── requirements.txt
├── .env.example
├── README.md
├── templates/index.html
├── static/style.css
├── static/app.js
└── data/                 # energy.db is generated on first run
```

## API
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Basic health status |
| GET | `/api/dashboard?limit=48` | Readings and computed summary |
| POST | `/api/simulate` | Add `normal`, `high_load`, or `imbalance` reading |
| POST | `/api/reset` | Reset to 24 normal demo points |
| GET | `/api/settings` | Read settings |
| POST | `/api/settings` | Update settings |
| GET | `/api/export.csv` | Download readings as CSV |

Example simulation JSON: `{"scenario":"imbalance"}`.

## Suggested report sections
Abstract; introduction/problem statement; objectives/scope; existing/proposed system; architecture and modules; technologies; database design; formulas and simulation scenarios; screenshots/test cases; results/limitations/future work; conclusion and references.

## Future work
Add authenticated multi-user access, deploy backend and managed database to a cloud platform, use cited grid emission factors, and integrate ESP32/isolated sensors only after guide/lab approval.
