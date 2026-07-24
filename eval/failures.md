# NL->SQL eval failures (for few-shot tuning)

## q04 (en)
- Q: Show the monthly trend of chain snatching in Bengaluru City for 2026.
- gold: SELECT date_trunc('month', CrimeRegisteredDate) AS ym, COUNT(*) FROM vw_case_360 WHERE crime_sub_head='Chain Snatching' AND district='Bengaluru City' AND year(CrimeRegisteredDate)=2026 GROUP BY ym ORDER BY ym
- gen:  SELECT DATE_TRUNC('MONTH', CrimeRegisteredDate) AS ym, COUNT(*) FROM vw_case_360 WHERE crime_sub_head = 'Chain Snatching' AND district = 'Bengalu City' AND YEAR(CrimeRegisteredDate) = 2026 GROUP BY ym ORDER BY ym LIMIT 500
- err:  None

## q19 (en)
- Q: How many cases invoke IT Act section 66D?
- gold: SELECT COUNT(DISTINCT CaseMasterID) FROM ActSectionAssociation WHERE ActID='ITAct' AND SectionID='66D'
- gen:  SELECT COUNT(DISTINCT CaseMasterID) FROM ActSectionAssociation WHERE ActID = 'IT' AND SectionID = '66D' LIMIT 500
- err:  None

## q23 (en)
- Q: In which districts did chain snatching occur in 2026?
- gold: SELECT DISTINCT district FROM vw_case_360 WHERE crime_sub_head='Chain Snatching' AND year(CrimeRegisteredDate)=2026 ORDER BY district
- gen:  SELECT district FROM vw_case_360 WHERE crime_sub_head = 'Chain Snatching' AND YEAR(CrimeRegisteredDate) = 2026 LIMIT 500
- err:  None

## q27 (en)
- Q: How many female victims were recorded in 2026?
- gold: SELECT COUNT(*) FROM Victim v JOIN CaseMaster c ON c.CaseMasterID=v.CaseMasterID WHERE v.GenderID=2 AND year(c.CrimeRegisteredDate)=2026
- gen:  SELECT 1
- err:  None

## q31 (en)
- Q: How many cases were closed as undetected (final report C)?
- gold: SELECT COUNT(*) FROM vw_case_360 WHERE final_report_type='C'
- gen:  SELECT COUNT(*) FROM vw_case_360 WHERE final_report_type = 'C' AND YEAR(CrimeRegisteredDate) = 2026 LIMIT 500
- err:  None

## q32 (en)
- Q: How many cases were closed as false (final report B)?
- gold: SELECT COUNT(*) FROM vw_case_360 WHERE final_report_type='B'
- gen:  SELECT COUNT(*) FROM vw_case_360 WHERE final_report_type = 'B' AND YEAR(CrimeRegisteredDate) = 2026 LIMIT 500
- err:  None

## q33 (en)
- Q: Heinous vs non-heinous breakdown for 2026.
- gold: SELECT gravity, COUNT(*) c FROM vw_case_360 WHERE year(CrimeRegisteredDate)=2026 GROUP BY gravity ORDER BY gravity
- gen:  SELECT COUNT(*) OVER () AS heinous_count, gravity, COUNT(*) AS count FROM vw_case_360 WHERE YEAR(CrimeRegisteredDate) = 2026 GROUP BY gravity ORDER BY CASE WHEN gravity = 'Heinous' THEN 1 ELSE 2 END, count DESC, gravity LIMIT 500
- err:  None

## q39 (en)
- Q: Who is the single most frequently accused person (by case count)?
- gold: SELECT person_key, COUNT(*) c FROM vw_accused_history GROUP BY person_key ORDER BY c DESC, person_key LIMIT 1
- gen:  SELECT full_name, COUNT(DISTINCT CaseMasterID) AS c FROM vw_accused_history WHERE YEAR(CrimeRegisteredDate) = 2026 GROUP BY full_name ORDER BY c DESC LIMIT 1
- err:  None

## q46 (kn)
- Q: ಈ ವರ್ಷ ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಎಷ್ಟು ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು ದಾಖಲಾಗಿವೆ?
- gold: SELECT COUNT(*) FROM vw_case_360 WHERE crime_sub_head='Chain Snatching' AND district='Bengaluru City' AND year(CrimeRegisteredDate)=2026
- gen:  SELECT COUNT(*) FROM vw_case_360 WHERE crime_sub_head = 'Saragallatana' AND district = 'Bengaluru City' AND YEAR(CrimeRegisteredDate) = 2026 LIMIT 500
- err:  None

## q47 (kn)
- Q: 2024 ರಲ್ಲಿ ಮೈಸೂರಿನಲ್ಲಿ ಎಷ್ಟು ಕೊಲೆ ಪ್ರಕರಣಗಳು ದಾಖಲಾದವು?
- gold: SELECT COUNT(*) FROM vw_case_360 WHERE crime_sub_head='Murder' AND district='Mysuru' AND year(CrimeRegisteredDate)=2024
- gen:  SELECT COUNT(*) FROM vw_case_360 WHERE crime_sub_head = 'Theft' AND district = 'Mysuru' AND YEAR(CrimeRegisteredDate) = 2024 LIMIT 500
- err:  None

## q54 (kn)
- Q: 2026 ರಲ್ಲಿ ಯಾವ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಸರಗಳ್ಳತನ ನಡೆದಿದೆ?
- gold: SELECT DISTINCT district FROM vw_case_360 WHERE crime_sub_head='Chain Snatching' AND year(CrimeRegisteredDate)=2026 ORDER BY district
- gen:  SELECT district FROM vw_case_360 WHERE crime_sub_head = 'Saragadda' AND YEAR(CrimeRegisteredDate) = 2026 GROUP BY district LIMIT 500
- err:  None

## q55 (kn)
- Q: 2026 ರಲ್ಲಿ ಬೆಂಗಳೂರು ನಗರದ ಅತಿ ಹೆಚ್ಚು ಪ್ರಕರಣಗಳಿರುವ 5 ಠಾಣೆಗಳು ಯಾವುವು?
- gold: SELECT police_station, COUNT(*) c FROM vw_case_360 WHERE district='Bengaluru City' AND year(CrimeRegisteredDate)=2026 GROUP BY police_station ORDER BY c DESC, police_station LIMIT 5
- gen:  SELECT police_station, COUNT(*) AS c FROM vw_case_360 WHERE district = 'Bengaluru City' AND gravity = 'Heinous' AND YEAR(CrimeRegisteredDate) = 2026 GROUP BY police_station ORDER BY c DESC, police_station LIMIT 5
- err:  None

## q59 (kn)
- Q: ಸುರೇಶ್ ಬಿ ಎಷ್ಟು ಪ್ರಕರಣಗಳಲ್ಲಿ ಆರೋಪಿಯಾಗಿದ್ದಾರೆ?
- gold: SELECT COUNT(DISTINCT CaseMasterID) FROM vw_accused_history WHERE full_name='Suresh B'
- gen:  SELECT COUNT(DISTINCT CaseMasterID) FROM vw_accused_history WHERE full_name = 'SURESH B I' AND crime_sub_head IN ('Murder', 'Theft', 'Robbery', 'House Burglary (Night)', 'Cheating / Online Fraud', 'NDPS') LIMIT 500
- err:  None

## q60 (kn)
- Q: 2026 ರಲ್ಲಿ ಬೆಂಗಳೂರು ನಗರದ ಸರಗಳ್ಳತನದ ಮಾಸಿಕ ಪ್ರವೃತ್ತಿಯನ್ನು ತೋರಿಸಿ.
- gold: SELECT date_trunc('month', CrimeRegisteredDate) AS ym, COUNT(*) FROM vw_case_360 WHERE crime_sub_head='Chain Snatching' AND district='Bengaluru City' AND year(CrimeRegisteredDate)=2026 GROUP BY ym ORDER BY ym
- gen:  SELECT DATE_TRUNC('MONTH', CrimeRegisteredDate) AS ym, COUNT(*) FROM vw_case_360 WHERE district = 'Bengaluru City' AND YEAR(CrimeRegisteredDate) = 2026 GROUP BY ym ORDER BY ym LIMIT 500
- err:  None
