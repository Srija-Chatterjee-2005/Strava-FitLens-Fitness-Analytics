-- Fitness app analysis | SQLite | open data/fitness.db first.
-- These queries use the cleaned daily view created by prepare.sql.
-- Q1: Study coverage and core metrics
SELECT COUNT(DISTINCT Id) users, COUNT(*) user_days,MIN(date) start_date,MAX(date) end_date,
 ROUND(AVG(TotalSteps),1) avg_steps,ROUND(AVG(Calories),1) avg_daily_calories,
 ROUND(AVG(sleep_minutes)/60,2) avg_sleep_hours,COUNT(sleep_minutes) sleep_user_days FROM daily;
-- Q2: Daily trend, with changing observed sample size
SELECT date,COUNT(*) observed_users,AVG(TotalSteps) avg_steps,AVG(Calories) avg_calories FROM daily GROUP BY date;
-- Q3: Weekday comparison, Monday first
SELECT (CAST(strftime('%w',date) AS INTEGER)+6)%7 weekday_number,
 COUNT(*) user_days,AVG(TotalSteps) avg_steps,AVG(active_minutes) avg_active_minutes FROM daily GROUP BY weekday_number ORDER BY weekday_number;
-- Q4: Hourly activity
SELECT hour,COUNT(StepTotal) observed_user_hours,AVG(StepTotal) avg_steps,
 AVG(Calories) avg_calories FROM hourly GROUP BY hour ORDER BY hour;
-- Q5: Activity composition, this is recorded time, not verified wear time
SELECT AVG(SedentaryMinutes) sedentary,AVG(LightlyActiveMinutes) light,
 AVG(FairlyActiveMinutes) fairly,AVG(VeryActiveMinutes) very FROM daily;
-- Q6: User-level step comparison (avoids giving frequent reporters more weight)
SELECT Id,COUNT(*) observed_days,AVG(TotalSteps) avg_steps,AVG(Calories) avg_calories FROM daily GROUP BY Id ORDER BY avg_steps DESC;
-- Q7: Step goal attainment, 10,000 is an illustrative configurable goal
SELECT SUM(CASE WHEN TotalSteps>=10000 THEN 1 ELSE 0 END) goal_days,
 COUNT(TotalSteps) observed_days,100.0*SUM(CASE WHEN TotalSteps>=10000 THEN 1 ELSE 0 END)/COUNT(TotalSteps) goal_pct FROM daily;
-- Q8: Matched same-date sleep and activity observations
SELECT Id,date,TotalSteps,active_minutes,SedentaryMinutes,sleep_minutes/60.0 sleep_hours,
 sleep_efficiency_pct FROM daily WHERE sleep_minutes IS NOT NULL;
-- Q9: Data-quality flags, do not automatically delete flagged observations
SELECT SUM(CASE WHEN TotalSteps=0 THEN 1 ELSE 0 END) zero_step_days,
 SUM(CASE WHEN Calories=0 THEN 1 ELSE 0 END) zero_calorie_days,
 SUM(CASE WHEN recorded_minutes>1440 THEN 1 ELSE 0 END) over_24h_days,
 SUM(CASE WHEN SedentaryMinutes>=1440 THEN 1 ELSE 0 END) fully_sedentary_days FROM daily;
-- Q10: Sparse measurement coverage
SELECT COUNT(*) activity_days,COUNT(sleep_minutes) sleep_days,COUNT(weight_kg) weight_days,
 COUNT(hr_mean_bpm) heart_rate_days FROM daily;
-- Q11: User-weekday heatmap
SELECT Id,(CAST(strftime('%w',date) AS INTEGER)+6)%7 weekday_number,
 AVG(TotalSteps) avg_steps FROM daily GROUP BY Id,weekday_number;
-- Q12: Sample-averaged heart rate (not resting heart rate)
SELECT date,COUNT(hr_mean_bpm) observed_users,AVG(hr_mean_bpm) avg_user_daily_bpm FROM daily GROUP BY date;
