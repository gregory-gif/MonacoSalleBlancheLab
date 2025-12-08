# Monaco Salle Blanche Lab ♠️

**Architect:** Gregory  
**Tech Stack:** Python 3.11, NiceGUI, Render  

## Mission
A private Baccarat Cockpit & Monte-Carlo Simulator designed to optimize "SBM Gold" status acquisition while strictly managing bankroll risk via the "Iron Gate" and "Unified Ladder" protocols.

## Modules
1. **Live Cockpit:** Real-time decision assistant for physical play.
2. **Simulator:** Monte-Carlo engine to test strategies against 10-year timelines.
3. **Dashboard:** Live financial tracking (GA, YTD PnL, Luxury Tax).
4. **Session Log:** Ledger of all played sessions.

## Deployment
* **Local:** `python3 -m utils.main`
* **Render:** `gunicorn -w 4 -k uvicorn.workers.UvicornWorker utils.main:app`
