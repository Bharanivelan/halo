# Ground-Truth Evaluation Dataset

This folder holds the **manually verified** dataset we use to measure whether Inhabitr's discovery, research and scoring actually work (PRD §8.1, AGENT_ARCHITECTURE §13).

> **Rule:** every row is researched and checked by a human. Never fill it with AI-generated content: the whole point is to have an independent reference to compare the AI against.

## Files

| File | Purpose |
|---|---|
| `ground_truth_template.csv` | Column headers + one clearly fictional EXAMPLE row (delete it when you start) |
| `ground_truth_omr_v1.csv` | Your working dataset (create by copying the template) |

## Reference property

Use the same hypothetical property as the demo workspace: an upscale hotel on OMR (Rajiv Gandhi Salai) near Sholinganallur, Chennai, **15 km radius**. Record the exact pin you use here so distances are reproducible:

```
reference_lat = ________   reference_lng = ________   (fill in once and don't change)
radius_km     = 15
```

**Fixed scope (DECISION_LOG D-20):** the pin and radius above never change for `ground_truth_omr_v1`. If either must change, create `ground_truth_omr_v2.csv` and keep v1 untouched, so eval runs stay comparable.

**Git:** only this README and the template are committed. Your working dataset (`ground_truth_omr_v1.csv`) is git-ignored by default. It contains researched public information, not customer data, so you may choose to version it later; decide deliberately.

## What to include (target 30–50 rows)

| Group | Count | Why |
|---|---|---|
| Clearly relevant targets (IT/ITES, consulting, engineering R&D, manufacturing) inside 15 km | 20–30 | Measures recall and research accuracy |
| Borderline (just outside radius, very small, or very large RFP-driven firms) | 5–10 | Tests ranking nuance |
| **Negatives** (not a business office: shops, residential, closed companies, wrong industry) | ~10 | Measures discovery **precision**; without negatives we can't tell if the system filters junk |

Mix sizes (small, mid, large), localities along the corridor (e.g. Perungudi, Thoraipakkam, Karapakkam, Sholinganallur, Navalur, Siruseri, Kelambakkam) and industries.

## How to verify (per row, ~10–15 min)

1. Find the company's official website and the address of its **local** office (not just the registered office).
2. Record a **primary source URL** for each fact you fill in. If you can't find a source, write `U` (unknown) rather than guessing — "unknown" is a valid ground truth.
3. Employee range: only fill it in if a source states it (company site, credible news, or a filing); note the source URL.
4. Signals: only events with a **publication date**; prefer the last 12 months.
5. Hotel potential: your own judgement, with a one-line rationale. Pretend you are the hotel's sales manager.
6. Do not record personal contact details of individuals in this dataset. Roles only.

## Column definitions

| Column | Values | Notes |
|---|---|---|
| `record_id` | `GT-001`… | stable id |
| `company_name` | text | common name |
| `legal_name` | text / blank | if known |
| `website_domain` | e.g. `example.com` | registrable domain, no `https://` |
| `industry_code` | taxonomy code below | |
| `local_address` | text | operating office near OMR |
| `locality` | text | e.g. Perungudi |
| `latitude`, `longitude` | decimal | from a map pin on the office |
| `location_type` | `hq` / `branch` / `delivery_center` / `plant` / `registered` / `unknown` | |
| `within_radius` | `Y` / `N` | relative to reference pin |
| `hq_city` | text / `U` | |
| `employee_range` | `1-10`, `11-50`, `51-200`, `201-500`, `501-1000`, `1001-5000`, `5000+`, `U` | |
| `employee_range_source_url` | url / blank | |
| `client_facing_services` | `Y` / `N` / `U` | do clients/partners likely visit? |
| `has_training_or_onboarding` | `Y` / `N` / `U` | |
| `hosts_events` | `Y` / `N` / `U` | |
| `recent_signal_type` | signal type code (AGENT_ARCHITECTURE §6) / blank | |
| `recent_signal_summary` | text | one line |
| `recent_signal_url` | url | |
| `recent_signal_published_date` | `YYYY-MM-DD` | |
| `is_relevant_target` | `Y` / `N` | `N` for negatives |
| `hotel_potential` | `high` / `medium` / `low` / `none` | your judgement |
| `potential_offerings` | `;`-separated: `corporate_rate;mice;long_stay;fnb` | |
| `potential_rationale` | text | one line: why |
| `primary_source_url` | url | main source used |
| `verified_by` | initials | |
| `verified_on` | `YYYY-MM-DD` | |
| `notes` | text | anything odd |

## Initial industry taxonomy (seed for `industries` table)

`it_services` · `it_product_saas` · `ites_bpo` · `engineering_rnd` · `manufacturing_automotive` · `manufacturing_electronics` · `manufacturing_other` · `consulting_professional` · `bfsi_operations` · `healthcare_hospital` · `education` · `logistics` · `real_estate_coworking` · `events_agency` · `travel_management` · `other`

(Changes to this list must be mirrored in DATABASE_SCHEMA `industries` seed and recorded in DECISION_LOG.)

## How it's used

The `eval` module (Phase 4) loads this CSV, runs discovery + research for the reference property, matches results to rows (domain first, then name + location), and reports discovery precision/recall, FACT accuracy, signal date accuracy, ranking agreement (system top-20 vs rows with `hotel_potential = high`), and cost per company.
