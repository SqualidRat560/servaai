# ServaAI findings (all 4,500 customers)

Shock: README twist 1, job loss with EI at 55% of usual income. Judge = the track's formula (EI forever, no cap). Realistic = EI stops after 6 months and is capped at $729/week.

## Headline

- **The judge formula overstates runway by more than 6 months for 32.8% (95% CI 31.4% to 34.2%) of customers.**
- Under 6 months of runway: judge formula 35.1% (95% CI 33.6% to 36.4%); realistic 51.2% (95% CI 49.7% to 52.6%).
- Intervals: 1,000 bootstrap resamples of the 4,500 accounts.

## Segments

| Segment | Rule | Customers | Share |
|---|---|---:|---:|
| Stable | realistic runway 6+ months or no shortfall | 2,196 | 48.8% |
| Hidden fragile | judge says 6+ months, realistic says under 6 | 726 | 16.1% |
| Fragile | judge already under 6 months | 1,555 | 34.6% |
| Already short | buffer B <= 0 | 23 | 0.5% |

## Shock comparison (share under 6 months)

| Shock | Judge | Realistic | Median judge | Median realistic |
|---|---:|---:|---:|---:|
| Job loss, EI 55% (README 1) | 35.1% | 51.2% | 8.6 | 5.7 |
| Repair = 1 month of spending (README 2) | 8.7% | 8.7% | 120.0 | 120.0 |
| Job loss EI 55% + bills +15% (README 3) | 38.7% | 53.1% | 7.8 | 5.3 |
| Household bills +15% | 3.1% | 3.1% | 120.0 | 120.0 |
| Rent +$200/month | 2.8% | 2.8% | 120.0 | 120.0 |
| Scam of $1,000 | 2.8% | 2.8% | 120.0 | 120.0 |

## Hidden fragile share by region

| Region | Customers | Hidden fragile |
|---|---:|---:|
| west Bohemia | 430 | 18.1% |
| south Moravia | 778 | 17.2% |
| north Bohemia | 457 | 17.1% |
| east Bohemia | 544 | 16.0% |
| north Moravia | 793 | 15.6% |
| central Bohemia | 574 | 15.3% |
| Prague | 554 | 15.0% |
| south Bohemia | 370 | 14.6% |

## Hidden fragile share by owner age

| Owner age | Customers | Hidden fragile |
|---|---:|---:|
| 45-59 | 1,281 | 20.8% |
| 30-44 | 1,201 | 20.0% |
| <30 | 1,131 | 15.7% |
| 60+ | 887 | 4.6% |

## Caveats

- money_in includes transfers and pensions, not only wages, so EI computed from it is an upper bound: real runways may be shorter still.
- Medians of 120 mean 'no shortfall or 120+ months' (the track's cap).
- Gender is shown as context only; it is not used in any score.
