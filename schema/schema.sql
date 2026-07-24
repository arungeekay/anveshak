-- ============================================================================
-- ANVESHAK · KSP Datathon 2026 · Challenge 1
-- Schema derived 1:1 from the official "Police FIR System — ER Diagram" doc.
-- Dialect: DuckDB / standard SQL (the in-process analytical mirror).
-- Zoho Catalyst Data Store holds the same tables as system of record;
-- this mirror is rebuilt from Data Store on AppSail startup (see CLAUDE.md ADR-1).
-- ============================================================================

-- ---------- Geography & org masters ----------

CREATE TABLE State (
  StateID        INTEGER PRIMARY KEY,
  StateName      VARCHAR NOT NULL,
  NationalityID  INTEGER,
  Active         BOOLEAN DEFAULT TRUE
);

CREATE TABLE District (
  DistrictID   INTEGER PRIMARY KEY,
  DistrictName VARCHAR NOT NULL,
  StateID      INTEGER REFERENCES State(StateID),
  Active       BOOLEAN DEFAULT TRUE
);

CREATE TABLE UnitType (
  UnitTypeID    INTEGER PRIMARY KEY,
  UnitTypeName  VARCHAR NOT NULL,         -- e.g. Police Station, Circle Office
  CityDistState VARCHAR,                  -- operational level: City / District / State
  Hierarchy     INTEGER,                  -- lower = higher authority
  Active        BOOLEAN DEFAULT TRUE
);

CREATE TABLE Unit (
  UnitID        INTEGER PRIMARY KEY,      -- police station / unit
  UnitName      VARCHAR NOT NULL,
  TypeID        INTEGER REFERENCES UnitType(UnitTypeID),
  ParentUnit    INTEGER,                  -- self-reference to Unit.UnitID (hierarchy)
  NationalityID INTEGER,
  StateID       INTEGER REFERENCES State(StateID),
  DistrictID    INTEGER REFERENCES District(DistrictID),
  Active        BOOLEAN DEFAULT TRUE
);

CREATE TABLE Rank (
  RankID    INTEGER PRIMARY KEY,
  RankName  VARCHAR NOT NULL,             -- Constable, Inspector, DSP...
  Hierarchy INTEGER,                      -- lower = higher rank
  Active    BOOLEAN DEFAULT TRUE
);

CREATE TABLE Designation (
  DesignationID   INTEGER PRIMARY KEY,
  DesignationName VARCHAR NOT NULL,       -- Investigating Officer, SHO...
  Active          BOOLEAN DEFAULT TRUE,
  SortOrder       INTEGER
);

CREATE TABLE Employee (
  EmployeeID           INTEGER PRIMARY KEY,
  DistrictID           INTEGER REFERENCES District(DistrictID),
  UnitID               INTEGER REFERENCES Unit(UnitID),
  RankID               INTEGER REFERENCES Rank(RankID),
  DesignationID        INTEGER REFERENCES Designation(DesignationID),
  KGID                 VARCHAR,           -- Karnataka Government ID
  FirstName            VARCHAR NOT NULL,
  EmployeeDOB          DATE,
  GenderID             INTEGER,           -- lookup value
  BloodGroupID         INTEGER,
  PhysicallyChallenged BOOLEAN DEFAULT FALSE,
  AppointmentDate      DATE
);

CREATE TABLE Court (
  CourtID    INTEGER PRIMARY KEY,
  CourtName  VARCHAR NOT NULL,
  DistrictID INTEGER REFERENCES District(DistrictID),
  StateID    INTEGER REFERENCES State(StateID),
  Active     BOOLEAN DEFAULT TRUE
);

-- ---------- Legal masters ----------

CREATE TABLE Act (
  ActCode        VARCHAR PRIMARY KEY,     -- e.g. 'BNS', 'IPC', 'NDPS'
  ActDescription VARCHAR,
  ShortName      VARCHAR,
  Active         BOOLEAN DEFAULT TRUE
);

CREATE TABLE Section (
  ActCode            VARCHAR REFERENCES Act(ActCode),
  SectionCode        VARCHAR NOT NULL,    -- e.g. '303(2)', '302'
  SectionDescription VARCHAR,
  Active             BOOLEAN DEFAULT TRUE,
  PRIMARY KEY (ActCode, SectionCode)
);

CREATE TABLE CrimeHead (
  CrimeHeadID    INTEGER PRIMARY KEY,
  CrimeGroupName VARCHAR NOT NULL,        -- e.g. 'Crimes Against Body', 'Property Crimes'
  Active         BOOLEAN DEFAULT TRUE
);

CREATE TABLE CrimeSubHead (
  CrimeSubHeadID INTEGER PRIMARY KEY,
  CrimeHeadID    INTEGER REFERENCES CrimeHead(CrimeHeadID),
  CrimeHeadName  VARCHAR NOT NULL,        -- e.g. 'Murder', 'Chain Snatching'
  SeqID          INTEGER
);

CREATE TABLE CrimeHeadActSection (
  CrimeHeadID INTEGER REFERENCES CrimeHead(CrimeHeadID),
  ActCode     VARCHAR REFERENCES Act(ActCode),
  SectionCode VARCHAR                     -- section applicable to this crime head
);

-- ---------- Case lookups ----------

CREATE TABLE CaseCategory (
  CaseCategoryID INTEGER PRIMARY KEY,
  LookupValue    VARCHAR NOT NULL         -- FIR / UDR / PAR / Zero FIR
);

CREATE TABLE GravityOffence (
  GravityOffenceID INTEGER PRIMARY KEY,
  LookupValue      VARCHAR NOT NULL       -- Heinous / Non-Heinous
);

CREATE TABLE CaseStatusMaster (
  CaseStatusID   INTEGER PRIMARY KEY,
  CaseStatusName VARCHAR NOT NULL         -- Under Investigation / Charge Sheeted / Closed ...
);

CREATE TABLE OccupationMaster (
  OccupationID   INTEGER PRIMARY KEY,
  OccupationName VARCHAR NOT NULL
);

CREATE TABLE ReligionMaster (
  ReligionID   INTEGER PRIMARY KEY,
  ReligionName VARCHAR NOT NULL
);

CREATE TABLE CasteMaster (
  caste_master_id   INTEGER PRIMARY KEY,
  caste_master_name VARCHAR NOT NULL
);

-- ---------- Core case tables ----------

CREATE TABLE CaseMaster (
  CaseMasterID        INTEGER PRIMARY KEY,
  -- CrimeNo composite format (per ER doc):
  --   1-digit CaseCategory code (FIR=1, UDR=3, PAR=4, ZeroFIR=8)
  -- + 4-digit District ID + 4-digit PS/Unit ID + 4-digit Year + 5-digit serial
  -- e.g. FIR '104430006202600001'
  CrimeNo             VARCHAR NOT NULL UNIQUE,
  CaseNo              VARCHAR NOT NULL,   -- YYYY + 5-digit serial (last 9 of CrimeNo)
  CrimeRegisteredDate DATE NOT NULL,
  PolicePersonID      INTEGER REFERENCES Employee(EmployeeID),
  PoliceStationID     INTEGER REFERENCES Unit(UnitID),
  CaseCategoryID      INTEGER REFERENCES CaseCategory(CaseCategoryID),
  GravityOffenceID    INTEGER REFERENCES GravityOffence(GravityOffenceID),
  CrimeMajorHeadID    INTEGER REFERENCES CrimeHead(CrimeHeadID),
  CrimeMinorHeadID    INTEGER REFERENCES CrimeSubHead(CrimeSubHeadID),
  CaseStatusID        INTEGER REFERENCES CaseStatusMaster(CaseStatusID),
  CourtID             INTEGER REFERENCES Court(CourtID),
  IncidentFromDate    TIMESTAMP,
  IncidentToDate      TIMESTAMP,
  InfoReceivedPSDate  TIMESTAMP,
  latitude            DOUBLE,
  longitude           DOUBLE,
  BriefFacts          VARCHAR             -- narrative; EN or KN; the linkage-engine fuel
);

CREATE TABLE ComplainantDetails (
  ComplainantID   INTEGER PRIMARY KEY,
  CaseMasterID    INTEGER REFERENCES CaseMaster(CaseMasterID),
  ComplainantName VARCHAR,
  AgeYear         INTEGER,
  OccupationID    INTEGER REFERENCES OccupationMaster(OccupationID),
  ReligionID      INTEGER REFERENCES ReligionMaster(ReligionID),
  CasteID         INTEGER REFERENCES CasteMaster(caste_master_id),
  GenderID        INTEGER
);

CREATE TABLE Victim (
  VictimMasterID INTEGER PRIMARY KEY,
  CaseMasterID   INTEGER REFERENCES CaseMaster(CaseMasterID),
  VictimName     VARCHAR,
  AgeYear        INTEGER,
  GenderID       INTEGER,                 -- m / f / t lookup
  VictimPolice   VARCHAR                  -- '1' if victim is police else '0'
);

CREATE TABLE Accused (
  AccusedMasterID INTEGER PRIMARY KEY,
  CaseMasterID    INTEGER REFERENCES CaseMaster(CaseMasterID),
  AccusedName     VARCHAR,
  AgeYear         INTEGER,
  GenderID        INTEGER,                -- M / F / T
  PersonID        VARCHAR                 -- sort key within case: A1, A2, A3...
  -- NOTE (ADR-3): the same real-world individual keeps the same AccusedName and a
  -- stable person_key (via AccusedPersonMap below) so cross-case identity resolution
  -- is possible — mirroring how CCTNS matches on name/parentage/DOB.
);

CREATE TABLE ActSectionAssociation (
  CaseMasterID   INTEGER REFERENCES CaseMaster(CaseMasterID),
  ActID          VARCHAR REFERENCES Act(ActCode),
  SectionID      VARCHAR,                 -- SectionCode of the act invoked
  ActOrderID     INTEGER,
  SectionOrderID INTEGER
);

CREATE TABLE ArrestSurrender (
  ArrestSurrenderID         INTEGER PRIMARY KEY,
  CaseMasterID              INTEGER REFERENCES CaseMaster(CaseMasterID),
  ArrestSurrenderTypeID     INTEGER,      -- arrest / voluntary surrender (lookup)
  ArrestSurrenderDate       DATE,
  ArrestSurrenderStateId    INTEGER REFERENCES State(StateID),
  ArrestSurrenderDistrictId INTEGER REFERENCES District(DistrictID),
  PoliceStationID           INTEGER REFERENCES Unit(UnitID),
  IOID                      INTEGER REFERENCES Employee(EmployeeID),
  CourtID                   INTEGER REFERENCES Court(CourtID),
  AccusedMasterID           INTEGER REFERENCES Accused(AccusedMasterID),
  IsAccused                 BOOLEAN,
  IsComplainantAccused      BOOLEAN
);

-- Junction (named in the ER relationship matrix; columns inferred)
CREATE TABLE inv_arrestsurrenderaccused (
  ArrestSurrenderID INTEGER REFERENCES ArrestSurrender(ArrestSurrenderID),
  AccusedMasterID   INTEGER REFERENCES Accused(AccusedMasterID)
);

-- One-to-one with CaseMaster (named in the ER matrix; columns inferred)
CREATE TABLE Inv_OccuranceTime (
  CaseMasterID      INTEGER PRIMARY KEY REFERENCES CaseMaster(CaseMasterID),
  OccurrenceFrom    TIMESTAMP,
  OccurrenceTo      TIMESTAMP,
  PlaceOfOccurrence VARCHAR
);

CREATE TABLE ChargesheetDetails (
  CSID           INTEGER PRIMARY KEY,
  CaseMasterID   INTEGER REFERENCES CaseMaster(CaseMasterID),
  csdate         TIMESTAMP,
  cstype         CHAR(1),                 -- A=Chargesheet, B=False Case, C=Undetected
  PolicePersonID INTEGER REFERENCES Employee(EmployeeID)
);

-- ---------- ANVESHAK auxiliary tables (ours, not in the ER doc) ----------

-- Stable cross-case identity for synthetic people (see ADR-3)
CREATE TABLE PersonRegistry (
  person_key VARCHAR PRIMARY KEY,         -- e.g. 'P-004412'
  full_name  VARCHAR,
  dob        DATE,
  home_h3    VARCHAR,                     -- home locality H3 cell (linkage feature)
  notes      VARCHAR
);

CREATE TABLE AccusedPersonMap (
  AccusedMasterID INTEGER REFERENCES Accused(AccusedMasterID),
  person_key      VARCHAR REFERENCES PersonRegistry(person_key)
);

-- Precomputed MO vectors (data_engine writes; linkage engine reads)
CREATE TABLE CaseMOVector (
  CaseMasterID INTEGER PRIMARY KEY REFERENCES CaseMaster(CaseMasterID),
  embedding    DOUBLE[],                  -- narrative sentence-embedding
  mo_features  VARCHAR,                   -- JSON: {tod_bucket, dow, h3, weapon, vehicle, entry, target}
  model        VARCHAR
);

-- District socio-economic overlay (census-style indicators, coarse)
CREATE TABLE DistrictIndicators (
  DistrictID      INTEGER PRIMARY KEY REFERENCES District(DistrictID),
  population      INTEGER,
  urban_pct       DOUBLE,
  literacy_pct    DOUBLE,
  density_per_km2 DOUBLE
);

-- Audit log (append-only; also persisted to Catalyst NoSQL)
CREATE TABLE AuditLog (
  audit_id INTEGER PRIMARY KEY,
  ts       TIMESTAMP,
  user_id  VARCHAR,
  role     VARCHAR,
  action   VARCHAR,                       -- chat / investigate / export / role_switch ...
  detail   VARCHAR                        -- JSON: question, sql, case_ids touched
);

-- ---------- Analyst views (the NL->SQL engine targets THESE first) ----------

CREATE VIEW vw_case_360 AS
SELECT
  cm.CaseMasterID, cm.CrimeNo, cm.CaseNo, cm.CrimeRegisteredDate,
  cm.IncidentFromDate, cm.IncidentToDate, cm.latitude, cm.longitude, cm.BriefFacts,
  cc.LookupValue          AS case_category,
  go_.LookupValue         AS gravity,
  ch.CrimeGroupName       AS crime_head,
  csh.CrimeHeadName       AS crime_sub_head,
  cs.CaseStatusName       AS case_status,
  u.UnitName              AS police_station,
  d.DistrictName          AS district,
  e.FirstName             AS registering_officer,
  ct.CourtName            AS court,
  (SELECT COUNT(*) FROM Accused a WHERE a.CaseMasterID = cm.CaseMasterID)  AS accused_count,
  (SELECT COUNT(*) FROM Victim v WHERE v.CaseMasterID = cm.CaseMasterID)   AS victim_count,
  (SELECT MIN(cd.csdate) FROM ChargesheetDetails cd WHERE cd.CaseMasterID = cm.CaseMasterID) AS chargesheet_date,
  (SELECT cd.cstype FROM ChargesheetDetails cd WHERE cd.CaseMasterID = cm.CaseMasterID LIMIT 1) AS final_report_type
FROM CaseMaster cm
LEFT JOIN CaseCategory cc    ON cc.CaseCategoryID = cm.CaseCategoryID
LEFT JOIN GravityOffence go_ ON go_.GravityOffenceID = cm.GravityOffenceID
LEFT JOIN CrimeHead ch       ON ch.CrimeHeadID = cm.CrimeMajorHeadID
LEFT JOIN CrimeSubHead csh   ON csh.CrimeSubHeadID = cm.CrimeMinorHeadID
LEFT JOIN CaseStatusMaster cs ON cs.CaseStatusID = cm.CaseStatusID
LEFT JOIN Unit u             ON u.UnitID = cm.PoliceStationID
LEFT JOIN District d         ON d.DistrictID = u.DistrictID
LEFT JOIN Employee e         ON e.EmployeeID = cm.PolicePersonID
LEFT JOIN Court ct           ON ct.CourtID = cm.CourtID;

CREATE VIEW vw_accused_history AS
SELECT
  pm.person_key,
  pr.full_name,
  a.AccusedMasterID, a.CaseMasterID, a.AccusedName, a.AgeYear,
  c.CrimeRegisteredDate, c.crime_sub_head, c.district, c.police_station,
  c.case_status, c.gravity
FROM Accused a
JOIN AccusedPersonMap pm ON pm.AccusedMasterID = a.AccusedMasterID
JOIN PersonRegistry pr   ON pr.person_key = pm.person_key
JOIN vw_case_360 c       ON c.CaseMasterID = a.CaseMasterID;

CREATE VIEW vw_station_monthly AS
SELECT
  district, police_station, crime_head, crime_sub_head,
  DATE_TRUNC('month', CrimeRegisteredDate) AS month,
  COUNT(*) AS case_count
FROM vw_case_360
GROUP BY district, police_station, crime_head, crime_sub_head,
         DATE_TRUNC('month', CrimeRegisteredDate);

-- Co-accusal edges (CrimeGraph raw input)
CREATE VIEW vw_coaccusal_edges AS
SELECT DISTINCT
  m1.person_key AS person_a,
  m2.person_key AS person_b,
  a1.CaseMasterID
FROM Accused a1
JOIN Accused a2 ON a1.CaseMasterID = a2.CaseMasterID AND a1.AccusedMasterID < a2.AccusedMasterID
JOIN AccusedPersonMap m1 ON m1.AccusedMasterID = a1.AccusedMasterID
JOIN AccusedPersonMap m2 ON m2.AccusedMasterID = a2.AccusedMasterID;
