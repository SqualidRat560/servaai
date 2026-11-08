# Forecast backtest (month-end balance, next 3 months)

Origins: train 2020-07..2023-09 (70,077 rows), validate 2024-01..09 (35,735), test 2025-01..09 (40,309). No feature uses any month after the origin.

Test set (2025). MAE in dollars; MdAPE = median of |error| / max(|actual balance|, $100).

| Model | MAE h=1 | MAE h=2 | MAE h=3 | MdAPE h=1 | MdAPE h=2 | MdAPE h=3 |
|---|---:|---:|---:|---:|---:|---:|
| Flat (balance unchanged) | 4,224 | 5,289 | 6,042 | 10.1% | 14.5% | 17.4% |
| Statistical baseline | 4,395 | 6,157 | 7,952 | 10.1% | 16.4% | 22.1% |
| Ridge (alpha=10000) | 4,490 | 5,562 | 6,243 | 13.5% | 18.2% | 20.8% |
| XGBoost (absolute error, volatility-scaled) | 3,770 | 4,605 | 5,225 | 8.9% | 12.4% | 14.9% |

**XGBoost (absolute error, volatility-scaled)** wins and powers the app: average MAE 4,533 vs 5,185 for the flat baseline (+12.6% better).

Uncertainty band: P10-P90 of the winner's 2024 validation errors, scaled per account by its 12-month net-flow volatility. Share of 2025 test balances inside the band: 78.9% (target 80%).
