"""Rebuild compact analysis database from the original supplied ZIP.
Usage: python build_data.py path/to/original.zip
All CSV sources contribute either canonical measures, auxiliary daily summaries,
or reconciliation evidence. Alternate exports are never added to totals.
"""
from pathlib import Path
from zipfile import ZipFile
import sys, sqlite3, hashlib, json, re
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'data'; OUT.mkdir(exist_ok=True)

def build(archive):
    tables={}; inventory=[]; checks=[]; summaries=[]
    with ZipFile(archive) as z:
        for name in z.namelist():
            base=Path(name).name
            if not base.endswith('.csv'): continue
            with z.open(name) as f: d=pd.read_csv(f,dtype={'Id':str})
            rows=len(d); dup=int(d.duplicated().sum()); d=d.drop_duplicates()
            timecol=next(c for c in ['ActivityDate','ActivityDay','SleepDay','ActivityHour','ActivityMinute','Time','date','Date'] if c in d)
            dt=pd.to_datetime(d[timecol],format='%m/%d/%Y' if timecol in ['ActivityDate','ActivityDay'] else '%m/%d/%Y %I:%M:%S %p'); d['date']=dt.dt.strftime('%Y-%m-%d') if timecol!='date' else dt.dt.strftime('%Y-%m-%d')
            inventory.append(dict(file=base,rows=rows,exact_duplicates=dup,users=d.Id.nunique(),start=dt.min().isoformat(),end=dt.max().isoformat(),missing_cells=int(d.isna().sum().sum())))
            key=base.replace('_merged.csv','')
            if key.startswith('daily') or key in ['sleepDay','weightLogInfo']:
                tables[key]=d
            elif key.startswith('hourly'):
                d['timestamp']=dt.dt.strftime('%Y-%m-%d %H:%M:%S'); tables[key]=d
            else:
                valuecols=[c for c in d.select_dtypes('number').columns if c not in ['Id','logId']]
                # Detailed records stay at their own grain until aggregation.
                if 'Wide' in key:
                    d['measure']=d[valuecols].sum(axis=1,min_count=1)
                    s=d.groupby(['Id','date']).agg(**{key+'_total':('measure','sum'),key+'_hours':('measure','count')}).reset_index()
                elif key=='heartrate_seconds':
                    s=d.groupby(['Id','date']).agg(hr_mean_bpm=('Value','mean'),hr_min_bpm=('Value','min'),hr_max_bpm=('Value','max'),hr_samples=('Value','count')).reset_index()
                elif key=='minuteSleep':
                    s=d.groupby(['Id','date']).agg(sleep_minute_records=('value','count'),sleep_logs=('logId','nunique')).reset_index()
                else:
                    v=valuecols[0]
                    s=d.groupby(['Id','date']).agg(**{key+'_total':(v,'sum'),key+'_mean':(v,'mean'),key+'_minutes':(v,'count')}).reset_index()
                summaries.append(s)
            print(base,rows,'rows',flush=True)
        # Inspect spreadsheet copies without loading millions of spreadsheet cells.
        for name in z.namelist():
            if name.endswith('.xlsx'):
                blob=z.read(name)
                import io
                with ZipFile(io.BytesIO(blob)) as x:
                    with x.open('xl/worksheets/sheet1.xml') as f: head=f.read(4000).decode()
                    dimension=re.search(r'<dimension ref="([^"]+)"',head)
                inventory.append(dict(file=Path(name).name,rows=None,sha256=hashlib.sha256(blob).hexdigest(),sheet_dimension=dimension.group(1) if dimension else 'unknown',role='Alternate heart-rate spreadsheet export; CSV is canonical to avoid overlap and Excel row limits.'))
    daily=tables['dailyActivity'].drop(columns='ActivityDate')
    assert not daily.duplicated(['Id','date']).any()
    for key, mapping in [('dailySteps',{'StepTotal':'TotalSteps'}),('dailyCalories',{'Calories':'Calories'}),('dailyIntensities',{c:c for c in tables['dailyIntensities'].columns if c not in ['Id','date','ActivityDay']})]:
        src=tables[key]; joined=daily.merge(src,on=['Id','date'],how='outer',suffixes=('','_other'),indicator=True,validate='one_to_one')
        mismatch=0
        for a,b in mapping.items():
            aa=a+'_other' if a in daily.columns else a
            mismatch+=int((~np.isclose(joined[b],joined[aa],equal_nan=True)).sum())
        checks.append(dict(check=key+' vs dailyActivity',mismatched_values=mismatch,unmatched_rows=int((joined['_merge']!='both').sum())))
    # Canonical small raw tables allow cleaning and joins to be demonstrated in SQL.
    db=OUT/'fitness.db'
    if db.exists():db.unlink()
    con=sqlite3.connect(db)
    daily.to_sql('raw_daily',con,index=False)
    tables['sleepDay'].drop(columns='SleepDay').to_sql('raw_sleep',con,index=False)
    w=tables['weightLogInfo'].drop(columns='Date').copy();w.to_sql('raw_weight',con,index=False)
    h=None
    for key in ['hourlySteps','hourlyCalories','hourlyIntensities']:
        t=tables[key].drop(columns=['ActivityHour','date'])
        assert not t.duplicated(['Id','timestamp']).any()
        h=t if h is None else h.merge(t,on=['Id','timestamp'],how='outer',validate='one_to_one')
    h['date']=h.timestamp.str[:10];h['hour']=h.timestamp.str[11:13].astype(int)
    h.to_sql('hourly',con,index=False)
    aux=None
    for s in summaries:aux=s if aux is None else aux.merge(s,on=['Id','date'],how='outer',validate='one_to_one')
    aux.to_sql('detail_daily',con,index=False)
    con.executescript((ROOT/'prepare.sql').read_text())
    merged=pd.read_sql('SELECT * FROM daily ORDER BY Id,date',con)
    assert not merged.duplicated(['Id','date']).any()
    assert len(merged)==len(daily)
    assert merged.TotalSteps.sum()==daily.TotalSteps.sum()
    merged.to_csv(OUT/'merged_daily.csv',index=False)
    # Retain all detailed-only dates separately instead of silently discarding them.
    full=daily[['Id','date']].merge(aux,on=['Id','date'],how='outer',validate='one_to_one')
    full.to_csv(OUT/'all_detail_daily.csv',index=False)
    h.to_csv(OUT/'merged_hourly.csv',index=False)
    pd.DataFrame(inventory).to_csv(OUT/'source_inventory.csv',index=False)
    pd.DataFrame(inventory).to_sql('source_inventory',con,index=False)
    checks += [dict(check='Daily merge row count',result=len(merged)),dict(check='Daily step sum preserved',result=int(merged.TotalSteps.sum())),dict(check='Detail dates outside activity base',result=len(full.merge(daily[['Id','date']],on=['Id','date'],how='left',indicator=True).query('_merge == "left_only"')))]
    (OUT/'validation.json').write_text(json.dumps(checks,indent=2))
    # Union-of-dates export integrates all non-overlapping source measures.
    all_sources=daily.copy()
    for table in ['sleep_daily','weight_daily','detail_daily']:
        all_sources=all_sources.merge(pd.read_sql('SELECT * FROM '+table,con),on=['Id','date'],how='outer',validate='one_to_one')
    hd=h.groupby(['Id','date']).agg(hourly_steps_total=('StepTotal','sum'),hourly_calories_total=('Calories','sum'),observed_hours=('timestamp','count')).reset_index()
    all_sources=all_sources.merge(hd,on=['Id','date'],how='outer',validate='one_to_one')
    all_sources.to_csv(OUT/'all_sources_daily.csv',index=False)
    all_sources.to_sql('all_sources_daily',con,index=False,if_exists='replace')
    con.close()
    print(json.dumps(checks,indent=2))
if __name__=='__main__':build(sys.argv[1])
