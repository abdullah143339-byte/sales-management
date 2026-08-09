# Sales Management System

Sales, inventory aur product management system — PC aur mobile dono ke liye.

## Web App (Live)

- URL: https://sales-management-tawny.vercel.app
- Mobile: browser mein kholo -> menu -> **Add to Home Screen** (app jaisa install ho jata hai)

## Auto-update workflow

Code edit karo -> `git push` -> Vercel automatically deploy kar deta hai.
Sab users ko wahi URL pe naya version mil jata hai.

## Desktop App

- Windows: `dist/SalesManagement.exe` (PyInstaller build)
- Build script: `scripts/build_windows.ps1`

## Dev

```
pip install -r requirements.txt
python -m pytest
python -m web.app          # local web app (SQLite)
python -m web.migrate data/sales.db   # SQLite -> Postgres migrate
```

## Stack

- Web: Flask + PWA + Vercel (Neon Postgres)
- Desktop: PySide6 + PyInstaller
