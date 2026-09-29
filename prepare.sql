-- SQLite dialect. Run after build_data.py imports source tables.
-- Dates are parsed by Python before import. Exact source duplicates are removed.
DROP VIEW IF EXISTS daily;
DROP VIEW IF EXISTS sleep_daily;
DROP VIEW IF EXISTS weight_daily;
CREATE VIEW sleep_daily AS
SELECT Id,date,SUM(TotalMinutesAsleep) AS sleep_minutes,
 SUM(TotalTimeInBed) AS time_in_bed_minutes,SUM(TotalSleepRecords) AS sleep_records
FROM (SELECT DISTINCT * FROM raw_sleep) GROUP BY Id,date;
CREATE VIEW weight_daily AS
SELECT Id,date,AVG(WeightKg) AS weight_kg,AVG(BMI) AS bmi,COUNT(*) AS weight_logs
FROM (SELECT DISTINCT * FROM raw_weight) GROUP BY Id,date;
CREATE VIEW daily AS
SELECT d.*,s.sleep_minutes,s.time_in_bed_minutes,s.sleep_records,
 w.weight_kg,w.bmi,w.weight_logs,
 (d.VeryActiveMinutes+d.FairlyActiveMinutes+d.LightlyActiveMinutes) AS active_minutes,
 (d.VeryActiveMinutes+d.FairlyActiveMinutes+d.LightlyActiveMinutes+d.SedentaryMinutes) AS recorded_minutes,
 100.0*s.sleep_minutes/NULLIF(s.time_in_bed_minutes,0) AS sleep_efficiency_pct,
 a.hr_mean_bpm,a.hr_samples,a.minuteMETsNarrow_mean AS mets_raw_mean,
 a.minuteStepsNarrow_total,a.minuteStepsNarrow_minutes,
 a.minuteCaloriesNarrow_total,a.minuteCaloriesNarrow_minutes,
 a.minuteIntensitiesNarrow_mean,a.minuteIntensitiesNarrow_minutes,
 a.minuteStepsWide_total,a.minuteStepsWide_hours,
 a.minuteCaloriesWide_total,a.minuteCaloriesWide_hours,
 a.minuteIntensitiesWide_total,a.minuteIntensitiesWide_hours,
 a.sleep_minute_records,a.sleep_logs
FROM raw_daily d
LEFT JOIN sleep_daily s ON d.Id=s.Id AND d.date=s.date
LEFT JOIN weight_daily w ON d.Id=w.Id AND d.date=w.date
LEFT JOIN detail_daily a ON d.Id=a.Id AND d.date=a.date;
