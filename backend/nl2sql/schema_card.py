"""Compressed schema card + domain glossary for the NL->SQL prompt (views first)."""
from __future__ import annotations

SCHEMA_CARD = """\
You write DuckDB SQL for the Karnataka State Police crime database. Prefer the
ANALYST VIEWS below; they already join the lookups. Return ONE read-only SELECT.

VIEW vw_case_360 (one row per case — USE THIS FIRST):
  CaseMasterID, CrimeNo, CaseNo, CrimeRegisteredDate (DATE),
  IncidentFromDate, IncidentToDate, latitude, longitude, BriefFacts,
  case_category ('FIR'|'UDR'|'PAR'|'Zero FIR'),
  gravity ('Heinous'|'Non-Heinous'),
  crime_head (group, e.g. 'Property Crimes'),
  crime_sub_head (e.g. 'Chain Snatching','Murder','Theft','Robbery',
                  'House Burglary (Night)','Cheating / Online Fraud','NDPS'),
  case_status ('Under Investigation'|'Charge Sheeted'|'Closed'),
  police_station (e.g. 'Jayanagar PS'), district (e.g. 'Bengaluru City'),
  registering_officer, court,
  accused_count, victim_count, chargesheet_date, final_report_type ('A'|'B'|'C')

VIEW vw_accused_history: person_key, full_name, AccusedMasterID, CaseMasterID,
  AccusedName, AgeYear, CrimeRegisteredDate, crime_sub_head, district,
  police_station, case_status, gravity

VIEW vw_station_monthly: district, police_station, crime_head, crime_sub_head,
  month (DATE, month start), case_count

VIEW vw_coaccusal_edges: person_a, person_b, CaseMasterID

Useful base tables: ActSectionAssociation(CaseMasterID, ActID, SectionID),
  Victim(CaseMasterID, VictimName, AgeYear, GenderID), ArrestSurrender(CaseMasterID, ...).

CrimeNo composite = 1-digit category (FIR=1,UDR=3,PAR=4,Zero FIR=8) + 4-digit
DistrictID + 4-digit UnitID + 4-digit year + 5-digit serial.

GLOSSARY:
- heinous  -> gravity = 'Heinous'
- UDR = Unnatural Death Report; PAR = Preliminary Action Report; Zero FIR = filed
  at any station regardless of jurisdiction -> case_category values above.
- chargesheet final report types: A = charge-sheeted, B = false case, C = undetected
  -> final_report_type.
- "this year" = 2026; the data spans 2023-01-01 to 2026-07-20 (IST).
- Use year(CrimeRegisteredDate), month(CrimeRegisteredDate), date_trunc('month', ...).

RULES: output ONLY the SQL, no explanation, no markdown fences. Single SELECT.
Match string filters exactly to the values above (case-sensitive)."""


def build_prompt(question: str, few_shots: list[dict]) -> str:
    examples = "\n\n".join(
        f"Q: {ex['question']}\nSQL: {ex['sql']}" for ex in few_shots
    )
    return (
        f"{SCHEMA_CARD}\n\n"
        f"Examples:\n{examples}\n\n"
        f"Q: {question}\nSQL:"
    )
