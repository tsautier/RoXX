# RoXX v1.0.0-beta7 Release Notes

## 🛡️ The "Competitor Killer" Update (Protection & Migration)

**Release Date:** March 22, 2026

This release transforms RoXX into a legally and technologically shielded powerhouse, specifically designed to outperform and outprotect competitors like RadX.

---

## 🎯 Highlights

### ✅ NPS Migration Assistant
- **Zero-Effort Transition**: Import Microsoft NPS XML configurations directly.
- **Automatic Mapping**: Maps NPS policies and clients to RoXX's modern RADIUS backend.
- **Preview Mode**: Review imported rules before committing to production.

### ✅ Combat Dashboard & Visual Analytics
- **Live Metrics**: Real-time Authentication Success/Failure donut charts.
- **Health Monitoring**: Instant visibility into LDAP, EntraID, and Radius backend status.
- **Advanced Logging**: Color-coded live log viewer (`SUCCESS` in green, `FAILURE` in red) for immediate troubleshooting.

### ✅ Supreme Protection Framework
- **AGPLv3 Licensing**: Strongest copyleft protection for network-accessible software.
- **Integrity Manifests**: All core files are SHA-256 hashed and verified on startup.
- **Digital Watermarking**: Hidden technical proof of ownership throughout the codebase.
- **X-RoXX Headers**: Custom security headers identifying the origin and build integrity.

---

## 📦 New Features

### 1. NPS Migration Assistant (`/nps-migration`)
- Upload `netsh nps export` XML files.
- Visual breakdown of imported clients and policies.
- One-click integration into the RoXX configuration database.

### 2. Enhanced Web Admin UI
- Dark-mode optimized dashboard with high-contrast analytics.
- Improved live log streaming with auto-scroll and status filtering.
- Backend health-check pings (Visual status indicators).

### 3. Licensing Strategy
- Transitioned from MIT to **GNU AGPLv3** to block "dishonest" cloud clones.
- Updated `LICENSE` and `README` to reflect the strongest legal protections.

---

## 🔧 Technical Improvements & Fixes

### CI/CD & Stability
- **Branch Optimization**: Converged all development to a clean `master` branch.
- **Python 3.12 Focus**: CI jobs now run exclusively on Python 3.12 for maximum performance.
- **Dependency Fixes**: Resolved missing `psutil` issues in the core system manager.
- **Linting Cleanup**: 43 `ruff` errors resolved (missing imports, orphan files).

### Bug Fixes
- **Auth Loop Resolved**: Fixed a critical redirection deadlock in the "Force Change Password" flow.
- **Admin Password Recovery**: Implemented a secure manual recovery path for the primary admin account.

---

## 🚀 Getting Started

### Upgrade from Beta6 (or squashed Master)
```bash
git pull origin master
git checkout v1.0.0-beta7
pip install -r requirements.txt
python -m roxx.web.app
```

### New Installation
```bash
git clone https://github.com/tsautier/RoXX.git
cd RoXX
git checkout v1.0.0-beta7
pip install -r requirements.txt
python -m roxx.web.app
```

**Enjoy the ultimate protection! 🔐**

---

**Full Changelog:** [v1.0.0-beta6...v1.0.0-beta7](https://github.com/tsautier/RoXX/compare/master...v1.0.0-beta7)
