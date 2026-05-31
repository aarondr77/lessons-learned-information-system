# LLIS Corpus Analysis

Generated: 2026-05-31 21:47 UTC
Total lessons: **2126**

## Field coverage

| Field | % populated |
| --- | --- |
| `title` | 99.1% |
| `lesson_date` | 99.6% |
| `organization` | 99.6% |
| `program_phase` | 22.9% |
| `abstract_text` | 48.4% |
| `driving_event_text` | 98.2% |
| `lesson_text` | 98.8% |
| `recommendation_text` | 98.5% |
| `nasa_topics_nonempty` | 99.4% |

## Text theme frequency

Keyword/regex hits across title + abstract + driving event + lesson + recommendation.

| Theme | Lessons | % |
| --- | --- | --- |
| testing | 1002 | 47.1% |
| hardware_design | 910 | 42.8% |
| safety_critical | 886 | 41.7% |
| operations | 702 | 33.0% |
| program_process | 577 | 27.1% |
| integration | 554 | 26.1% |
| cost_schedule | 514 | 24.2% |
| facilities | 510 | 24.0% |
| configuration | 461 | 21.7% |
| software | 445 | 20.9% |
| requirements | 359 | 16.9% |
| human_factors | 271 | 12.7% |
| safety_pha | 213 | 10.0% |

## Top NASA topics

| Topic | Count |
| --- | --- |
| None | 1616 |
| Spacecraft | 119 |
| Engineering design and project processes and standards | 116 |
| Hardware | 110 |
| Spacecraft and Spacecraft Instruments | 101 |
| Flight Equipment | 89 |
| Safety and Mission Assurance | 85 |
| Payloads | 80 |
| Integration and Testing | 80 |
| Ground Operations | 77 |
| Ground support systems | 75 |
| Program Management | 72 |
| Ground Equipment | 69 |
| Systems Engineering and Analysis | 66 |
| Ground processing and manifesting | 63 |
| Product Assurance | 62 |
| Planning of requirements verification processes | 62 |
| Engineering Design | 61 |
| Early requirements and standards definition | 61 |
| Risk Management / Assessment | 60 |
| Facilities | 60 |
| Flight Operations | 58 |
| Maintenance | 58 |
| Acquisition / procurement strategy and planning | 57 |
| Level II/III requirements definition | 57 |

## Organization distribution (top 15)

| Center | Count |
| --- | --- |
| ksc | 481 |
| jpl | 419 |
| jsc | 236 |
| hq | 206 |
| msfc | 200 |
| gsfc | 145 |
| arc | 119 |
| grc | 116 |
| larc | 101 |
| nesc | 31 |
| afrc | 30 |
| ssc | 18 |
| wstf | 13 |
| unknown | 9 |
| wff | 1 |

## Program phase

| Phase | Count |
| --- | --- |
| unknown | 1639 |
| Implementation | 115 |
| Not Applicable | 67 |
| Approval | 53 |
| Implementation &raquo; Pre-Phase A | 48 |
| Not Specified | 33 |
| Implementation &raquo; Phase E | 33 |
| Not Applicable &raquo; Pre-Phase A | 32 |
| Implementation &raquo; Phase D | 32 |
| Implementation &raquo; Phase C | 26 |
| Evaluation | 12 |
| Formulation &raquo; Phase B | 9 |
| Formulation | 9 |
| Formulation &raquo; Phase A | 8 |
| Formulation &raquo; Pre-Phase A | 5 |
| Implementation &raquo; Phase B | 3 |
| Implementation &raquo; Phase F | 2 |

## Lessons by year (sample)

| Year | Count |
| --- | --- |
| 1972 | 1 |
| 1981 | 1 |
| 1983 | 1 |
| 1985 | 1 |
| 1989 | 5 |
| 1990 | 7 |
| 1991 | 40 |
| 1992 | 191 |
| 1993 | 110 |
| 1994 | 113 |
| 1995 | 72 |
| 1996 | 73 |
| 1997 | 81 |
| 1998 | 75 |
| 1999 | 267 |
| 2000 | 103 |
| 2001 | 86 |
| 2002 | 118 |
| 2003 | 120 |
| 2004 | 66 |
| 2005 | 85 |
| 2006 | 22 |
| 2007 | 22 |
| 2008 | 42 |
| 2009 | 31 |
| 2010 | 125 |
| 2011 | 90 |
| 2012 | 30 |
| 2013 | 27 |
| 2014 | 19 |
| 2015 | 12 |
| 2016 | 19 |
| 2017 | 17 |
| 2018 | 13 |
| 2019 | 10 |
| 2020 | 6 |
| 2021 | 7 |
| 2022 | 5 |
| 2023 | 3 |
| 2025 | 1 |

## Taxonomy recommendations

Based on theme frequency and field coverage:

### Layer 1 — lifecycle agents (9)

Data supports distinct clusters for:
- `design_safety_review` — safety_pha theme + PHA/hazard language
- `code_review` — software theme (~445 lessons)
- `test_verification_review` — testing theme (~1002 lessons)
- `ops_monitoring_bot` — operations theme (~702 lessons)
- `config_change_review` — configuration theme (~461 lessons)
- `hardware_spec_review` — hardware_design theme (~910 lessons)
- `integration_systems_review` — integration theme (~554 lessons)
- `program_process_bot` — program_process theme (~577 lessons)
- `facilities_ground_review` — facilities theme (~510 lessons)

No merge recommended — each theme cluster has >100 hits.

### Layer 2 — failure patterns (18)

Patterns map to recurring mechanisms in text:
- Review/monitoring gaps (insufficient_review_flagging, insufficient_monitoring_alerting)
- Requirements and test gaps (requirements_gap, inadequate_test_verification)
- Config/change issues (configuration_drift, late_change_bypass)
- Ops/human factors (operator_procedure_gap, complacency_assumed_robustness, human_factors_ops)
- System mismatch (commodity_service_mismatch, interface_integration_gap)
- Quality/process (parts_materials_quality, software_assurance_gap, documentation_process_debt, procurement_supply_chain)
- Infrastructure (facility_installation_defect, redundancy_analysis_incomplete, schedule_pressure_shortcut)

### Impact extraction

- Lessons mentioning cost/schedule language: ~514
- Lessons mentioning safety-critical language: ~886
- No structured cost field in source; classify `impact_severity` from narrative during LLM pass.

- `driving_event_text` populated: 98.2% — mark `data_quality: partial` when missing.

## Sample lesson numbers for qualitative review

- [1188](https://llis.nasa.gov/lesson/1188) — jsc — Fire Hazard Associated With Battery Backup For Phone System
- [1146](https://llis.nasa.gov/lesson/1146) — ksc — Managing Risk Assessment In New Program Plans
- [473](https://llis.nasa.gov/lesson/473) — grc — Storage Battery Explosion
- [780](https://llis.nasa.gov/lesson/780) — jpl — Pyrotechnic Shock Testing
- [967](https://llis.nasa.gov/lesson/967) — msfc — Space Shuttle Main Engine (SSME): Instrumented Safety Checks During Engine Start
