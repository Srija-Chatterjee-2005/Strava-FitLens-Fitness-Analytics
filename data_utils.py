from pathlib import Path
import sqlite3,time,re
import pandas as pd
ROOT=Path(__file__).resolve().parent
WEEKDAYS=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
METRICS={'Daily steps':'TotalSteps','Daily calories':'Calories','Active minutes':'active_minutes','Sedentary minutes':'SedentaryMinutes','Sleep hours':'sleep_hours','Distance (source units)':'TotalDistance'}
def connect():return sqlite3.connect(f'file:{(ROOT/"data/fitness.db").as_posix()}?mode=ro',uri=True)
def read_table(name):
    if name not in ['daily','hourly','source_inventory','all_sources_daily']:raise ValueError('Unknown table')
    with connect() as c:return pd.read_sql_query('SELECT * FROM '+name,c)
def enrich(d):
    d=d.copy();d.Id=d.Id.astype(str);d['date']=pd.to_datetime(d.date)
    d['weekday']=d.date.dt.day_name();d['sleep_hours']=d.sleep_minutes/60
    d['participant'] = 'P' + d.Id.astype(str)
    return d

def longest_streak(d,goal):
    best=run=0;previous=None
    for row in d.sort_values('date').itertuples():
        if row.TotalSteps>=goal:
            run=run+1 if previous is not None and (row.date-previous).days==1 else 1
            best=max(best,run)
        else:run=0
        previous=row.date
    return best

def execute_sql(sql,d,h,scope='Filtered selection'):
    # Dedicated in-memory database: original file never receives writes.
    with sqlite3.connect(':memory:') as c:
        with connect() as source:source.backup(c)
        dd=d.copy();dd['date']=dd.date.dt.strftime('%Y-%m-%d')
        hh=h.copy();hh['date']=hh.date.dt.strftime('%Y-%m-%d')
        dd.to_sql('filtered_daily',c,index=False);hh.to_sql('filtered_hourly',c,index=False)
        if scope == 'Filtered selection':
            c.execute('CREATE TEMP VIEW daily AS SELECT * FROM filtered_daily')
            c.execute('CREATE TEMP VIEW hourly AS SELECT * FROM filtered_hourly')
        else:
            full = enrich(read_table('daily'))
            full['date'] = full.date.dt.strftime('%Y-%m-%d')
            full.to_sql('full_daily_enriched', c, index=False)
            c.execute('CREATE TEMP VIEW daily AS SELECT * FROM full_daily_enriched')
        allowed={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_RECURSIVE}
        c.set_authorizer(lambda action,*args:sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY)
        start=time.monotonic();c.set_progress_handler(lambda:int(time.monotonic()-start>5),10000)
        cur=c.execute(sql);rows=cur.fetchmany(10001)
        result=pd.DataFrame(rows[:10000],columns=[x[0] for x in cur.description])
        return result,len(rows)>10000,round((time.monotonic()-start)*1000)

def templates():
    parts=(ROOT/'analysis.sql').read_text().split(';');out={}
    for p in parts:
        if 'SELECT ' not in p:continue
        lines=p.strip().splitlines();label=next((x[3:] for x in lines if x.startswith('-- Q')),f'Query {len(out)+1}')
        out[label]=p.strip()+';'
    return out
