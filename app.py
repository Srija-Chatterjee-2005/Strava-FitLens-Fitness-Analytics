"""FitLens v2 — run with START_WINDOWS.bat or python -m streamlit run app.py."""
from pathlib import Path
import io,json,sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from data_utils import ROOT,WEEKDAYS,METRICS,read_table,enrich,longest_streak,execute_sql,templates
from ui import style,title,cards,kpi,heading,insight,chart,empty,fmt,esc,RED,BLUE,TEAL,PALETTE

st.set_page_config(page_title='FitLens • Fitness analytics',page_icon='🏃',layout='wide',initial_sidebar_state='expanded')
style()
@st.cache_data
def load():
    a = enrich(read_table('daily'))
    b = read_table('hourly')
    b.Id = b.Id.astype(str)
    b['date'] = pd.to_datetime(b.date)
    return a,b,read_table('source_inventory')
try:base,hourly,inventory=load()
except Exception:
    st.error('The project database could not be opened. Extract the entire ZIP first and keep the data folder beside app.py.');st.stop()
PAGES=['Overview','Activity explorer','Sleep & recovery','Participant studio','Goal tracker','Chart builder','SQL workspace','Data explorer']
def reset():
    st.session_state['dates'] = (base.date.min().date(), base.date.max().date())
    st.session_state['participants'] = []
    st.session_state['exclude'] = False
    st.session_state['goal'] = 10000
    st.session_state.pop('query_result', None)
with st.sidebar:
    st.markdown('<div class="brand"><div class="brand-icon">f.</div><div><div class="brand-name">FitLens</div><div class="brand-sub">MOVE. MEASURE. EXPLORE.</div></div></div>',unsafe_allow_html=True)
    page=st.radio('Workspace',PAGES,label_visibility='collapsed',key='page')
    st.divider()
    st.markdown('**Your selection**')
    dates=st.date_input('Date range',(base.date.min().date(),base.date.max().date()),min_value=base.date.min().date(),max_value=base.date.max().date(),key='dates')
    chosen=st.multiselect('Participants',sorted(base.Id.unique()),format_func=lambda x:'P'+x+' · '+x,key='participants',placeholder='All participants')
    goal=st.slider('Daily step goal',1000,20000,10000,500,key='goal')
    exclude=st.checkbox('Exclude zero-step days',key='exclude')
    st.button('Reset filters',on_click=reset,width='stretch')
    st.caption('Illustrative goal. Missing records stay missing; zero-step days may include non-wear.')
    st.divider();st.caption('ACADEMIC CASE STUDY\n\nFitbit / Fitabase · April–May 2016\n\nBuilt for Srija Chatterjee')
if len(dates)!=2:empty('Choose an end date to complete your selection.');st.stop()
d=base[base.date.between(pd.Timestamp(dates[0]),pd.Timestamp(dates[1]))].copy()
if chosen:d=d[d.Id.isin(chosen)]
if exclude:d=d[d.TotalSteps.gt(0)]
if d.empty:empty('No records match this selection. Use Reset filters to return to the full sample.');st.stop()
h=hourly.merge(d[['Id','date']],on=['Id','date'],how='inner',validate='many_to_one')
scope=f'{dates[0]:%d %b} – {dates[1]:%d %b %Y}  ·  {d.Id.nunique()} participants  ·  {len(d):,} recorded user-days'

def line(df,x,y):return px.line(df,x=x,y=y,color_discrete_sequence=[RED],markers=True)
def bar(df,x,y,color=RED):return px.bar(df,x=x,y=y,color_discrete_sequence=[color])
def csv(df):return df.to_csv(index=False).encode()
def user_stats(frame):
    g=frame.groupby(['Id','participant'],as_index=False).agg(observed_days=('date','nunique'),avg_steps=('TotalSteps','mean'),avg_calories=('Calories','mean'),active_minutes=('active_minutes','mean'),sleep_hours=('sleep_hours','mean'))
    rates=frame.assign(hit=frame.TotalSteps.ge(goal)).groupby('Id').hit.mean()*100
    g['goal_pct']=g.Id.map(rates);return g

def explain_scope():     
    st.caption(scope + ' • Sidebar filters apply to dashboard selections. SQL follows its selected scope. Full-sample datasets and project downloads ignore sidebar filters.')

if page=='Overview':
    title('Your fitness data, in focus.','A clear view of movement, daily habits, and the people behind the numbers.')
    rate=d.TotalSteps.ge(goal).mean()*100
    st.markdown(f'<div class="hero"><div><div class="eyebrow">ACTIVITY SNAPSHOT</div><h2>Small steps. A bigger picture.</h2><p>{esc(scope)}<br>Explore the sample, compare patterns, and turn observations into questions worth testing.</p></div><div class="hero-stat"><strong>{rate:.1f}%</strong><span>of observed days reached {goal:,} steps</span></div></div>',unsafe_allow_html=True)
    cards([('AVERAGE DAILY STEPS',fmt(d.TotalSteps.mean()),f'{d.TotalSteps.sum():,} total recorded steps'),('DAILY CALORIE ESTIMATE',fmt(d.Calories.mean()),'Includes total device-estimated calories'),('ACTIVE MINUTES / DAY',fmt(d.active_minutes.mean()),'Light + fairly + very active minutes'),('RECORDED SLEEP',fmt(d.sleep_hours.mean(),' h',1),f'{d.sleep_hours.count()} matched sleep user-days')])
    left,right=st.columns([2.1,1])
    with left,st.container(border=True):
        heading('Movement over time','Daily mean and a 7-day moving average of those means')
        trend=d.groupby('date',as_index=False).agg(steps=('TotalSteps','mean'),n=('Id','nunique'))
        full=pd.date_range(d.date.min(),d.date.max());trend=trend.set_index('date').reindex(full).rename_axis('date').reset_index()
        fig=go.Figure();fig.add_trace(go.Scatter(x=trend.date,y=trend.steps,name='Daily average',mode='lines+markers',line=dict(color=RED,width=2.5),marker=dict(size=5),fill='tozeroy',fillcolor='rgba(229,72,77,.06)',customdata=trend.n,hovertemplate='%{x|%d %b}<br>%{y:,.0f} steps<br>%{customdata} participants<extra></extra>'))
        fig.add_trace(go.Scatter(x=trend.date,y=trend.steps.rolling(7,min_periods=7).mean(),name='7-day mean',line=dict(color=BLUE,width=2,dash='dot')))
        fig.update_yaxes(title='Steps',rangemode='tozero');chart(fig,330)
    with right,st.container(border=True):
        heading('Recorded activity mix','Share of recorded category minutes')
        cols=['SedentaryMinutes','LightlyActiveMinutes','FairlyActiveMinutes','VeryActiveMinutes'];labels=['Sedentary','Lightly active','Fairly active','Very active']
        totals=d[cols].sum();fig=go.Figure(go.Pie(labels=labels,values=totals,hole=.73,marker=dict(colors=['#dce1ec',RED,BLUE,TEAL]),textinfo='none',hovertemplate='%{label}<br>%{percent}<extra></extra>'))
        fig.update_layout(annotations=[dict(text=f'<b>{d.active_minutes.mean():.0f}</b><br>active min/day',x=.5,y=.5,font_size=16,showarrow=False)],showlegend=True);chart(fig,330)
    l,r=st.columns(2)
    with l,st.container(border=True):
        heading('The rhythm of your week','Average steps per observed user-day')
        w=d.groupby('weekday').TotalSteps.mean().reindex(WEEKDAYS).reset_index();f=bar(w,'weekday','TotalSteps');f.update_xaxes(title=None,ticktext=[x[:3] for x in WEEKDAYS],tickvals=WEEKDAYS);f.update_yaxes(title='Steps');chart(f,275)
    with r,st.container(border=True):
        heading('Activity and energy','Each point is a participant on one date')
        f=px.scatter(d,x='TotalSteps',y='Calories',opacity=.5,color_discrete_sequence=[RED],hover_data={'participant':True,'date':True},labels={'TotalSteps':'Daily steps','Calories':'Daily calories'});chart(f,275)
    valid=w.dropna();insight(f'<b>In this selection:</b> {valid.loc[valid.TotalSteps.idxmax(),"weekday"]} has the highest average steps. The number of observed participants can vary by day; associations do not establish causation.')
    st.download_button('↓ Download this selection',csv(d),'fitlens_daily_selection.csv','text/csv')

elif page=='Activity explorer':
    title('Find your activity rhythm.','Look beyond averages to explore timing, variation, and recorded movement.')
    explain_scope()
    tab1,tab2=st.tabs(['Daily & hourly patterns','Distribution & intensity'])
    with tab1:
        l,r=st.columns([1.35,1])
        with l,st.container(border=True):
            heading('When does movement happen?','Mean steps per observed user-hour')
            if h.empty:empty('No hourly measurements in this selection.')
            else:
                hh=h.groupby('hour',as_index=False).agg(steps=('StepTotal','mean'),observations=('StepTotal','count'))
                chart(px.bar(hh,x='hour',y='steps',hover_data=['observations'],color_discrete_sequence=[RED],labels={'hour':'Hour of day','steps':'Steps'}),330)
        with r,st.container(border=True):
            heading('Weekday or weekend?','User-day averages, not matched-participant effects')
            v=d.assign(day_type=np.where(d.date.dt.dayofweek>=5,'Weekend','Weekday')).groupby('day_type',as_index=False).agg(steps=('TotalSteps','mean'),records=('Id','size'))
            chart(px.bar(v,x='day_type',y='steps',text_auto='.0f',hover_data=['records'],color_discrete_sequence=[BLUE],labels={'steps':'Steps','day_type':''}),330)
        with st.container(border=True):
            heading('Hourly activity heatmap','Missing combinations remain blank')
            if h.empty:empty('No hourly measurements available.')
            else:
                pivot=h.assign(weekday=h.date.dt.day_name()).pivot_table(index='weekday',columns='hour',values='StepTotal',aggfunc='mean').reindex(index=WEEKDAYS,columns=range(24))
                chart(px.imshow(pivot,aspect='auto',color_continuous_scale=['#fff4f3','#f8afb0',RED,'#a62134'],labels={'color':'Steps','x':'Hour','y':''}),325)
    with tab2:
        l,r=st.columns(2)
        with l,st.container(border=True):
            heading('Daily step distribution')
            bins=st.slider('Histogram bins',10,60,25)
            chart(px.histogram(d,x='TotalSteps',nbins=bins,color_discrete_sequence=[RED],labels={'TotalSteps':'Daily steps'}))
        with r,st.container(border=True):
            heading('Activity minutes by weekday')
            cats=['LightlyActiveMinutes','FairlyActiveMinutes','VeryActiveMinutes']
            v=d.groupby('weekday')[cats].mean().reindex(WEEKDAYS).reset_index().melt('weekday',var_name='Intensity',value_name='Minutes')
            v.Intensity=v.Intensity.map(dict(zip(cats,['Light','Fairly active','Very active'])))
            chart(px.bar(v,x='weekday',y='Minutes',color='Intensity',color_discrete_sequence=PALETTE,barmode='stack',labels={'weekday':''}))
        st.caption('Recorded category minutes are not verified wear time. Zero-step and partial-record days can influence the results.')

elif page=='Sleep & recovery':
    title('Make room for recovery.','Explore recorded sleep and heart-rate patterns, with measurement coverage always visible.')
    explain_scope();s=d.dropna(subset=['sleep_hours']).copy()
    cards([('AVERAGE SLEEP',fmt(s.sleep_hours.mean(),' h',2),f'{len(s)} recorded user-days'),('TIME IN BED',fmt(s.time_in_bed_minutes.mean()/60,' h',2),'On days with sleep measurements'),('ASLEEP / TIME IN BED',fmt(100*s.sleep_minutes.sum()/s.time_in_bed_minutes.sum() if s.time_in_bed_minutes.sum()>0 else np.nan,'%',1),'Ratio of recorded totals'),('SLEEP COVERAGE',f'{100*len(s)/len(d):.1f}%',f'{s.Id.nunique()} participants with records')])
    tab1,tab2=st.tabs(['Sleep patterns','Heart rate & weight'])
    with tab1:
        if s.empty:empty('No sleep records match this selection. Try another participant.')
        else:
            l,r=st.columns(2)
            with l,st.container(border=True):
                heading('How much sleep is recorded?')
                chart(px.histogram(s,x='sleep_hours',nbins=20,color_discrete_sequence=[BLUE],labels={'sleep_hours':'Sleep hours'}))
            with r,st.container(border=True):
                heading('Steps and recorded sleep','Matched by source date')
                chart(px.scatter(s,x='TotalSteps',y='sleep_hours',hover_data=['participant','date'],color_discrete_sequence=[RED],opacity=.6,labels={'TotalSteps':'Daily steps','sleep_hours':'Sleep hours'}))
            with st.container(border=True):
                heading('Sleep duration across the week')
                chart(px.box(s,x='weekday',y='sleep_hours',category_orders={'weekday':WEEKDAYS},color_discrete_sequence=[BLUE],labels={'weekday':'','sleep_hours':'Hours'}),285)
        insight('Sleep is matched by the source date. This does not establish whether activity occurred before or after a particular night’s sleep. Missing sleep is never counted as zero.')
    with tab2:
        hr=d.dropna(subset=['hr_mean_bpm']);wt=d.dropna(subset=['weight_kg'])
        l,r=st.columns(2)
        with l,st.container(border=True):
            heading('Recorded heart rate',f'{len(hr)} user-days · {hr.Id.nunique()} participants')
            if hr.empty:empty('No heart-rate data in this selection.')
            else:
                g=hr.groupby('date',as_index=False).agg(bpm=('hr_mean_bpm','mean'),participants=('Id','nunique'))
                chart(px.line(g,x='date',y='bpm',markers=True,hover_data=['participants'],color_discrete_sequence=[RED],labels={'bpm':'BPM','date':''}))
            st.caption('Average of sample-based daily participant means. Not resting heart rate or a time-weighted mean.')
        with r,st.container(border=True):
            heading('Weight observations',f'{len(wt)} user-days · {wt.Id.nunique()} participants')
            if wt.empty:empty('No weight records in this selection.')
            else:
                who=st.selectbox('Participant with weight records',sorted(wt.Id.unique()),format_func=lambda x:'P'+x)
                chart(px.scatter(wt[wt.Id.eq(who)],x='date',y='weight_kg',color_discrete_sequence=[BLUE],labels={'weight_kg':'Weight (kg)','date':''}))
            st.caption('Sparse measurements. Points show observed dates only; no weight-loss claims are inferred.')

elif page=='Participant studio':
    title('Every participant has a pattern.','Explore one profile or compare participants using the same selected period.')
    explain_scope();tab1,tab2=st.tabs(['Individual profile','Compare participants'])
    with tab1:
        who=st.selectbox('Choose a participant',sorted(d.Id.unique()),format_func=lambda x:'Participant P'+x+' · '+x)
        u=d[d.Id.eq(who)].sort_values('date');hit=u.TotalSteps.ge(goal)
        cards([('AVERAGE STEPS',fmt(u.TotalSteps.mean()),f'Participant P{who}'),('OBSERVED DAYS',str(len(u)),f'{u.date.min():%d %b} to {u.date.max():%d %b}'),('GOAL SUCCESS',f'{hit.mean()*100:.1f}%',f'{hit.sum()} of {len(u)} observed days'),('LONGEST GOAL STREAK',f'{longest_streak(u,goal)} days','Consecutive calendar days; gaps break a streak')])
        l,r=st.columns([2,1])
        with l,st.container(border=True):
            heading('Daily progress')
            f=bar(u,'date','TotalSteps');f.add_hline(y=goal,line_dash='dot',line_color=BLUE,annotation_text=f'{goal:,} step goal');f.update_xaxes(title=None);f.update_yaxes(title='Steps');chart(f,325)
        with r,st.container(border=True):
            heading('Profile snapshot')
            summary=pd.DataFrame({'Measure':['Average active minutes','Average sedentary minutes','Average sleep hours','Sleep records','Heart-rate records'],'Value':[fmt(u.active_minutes.mean()),fmt(u.SedentaryMinutes.mean()),fmt(u.sleep_hours.mean(),digits=2),str(u.sleep_hours.count()),str(u.hr_mean_bpm.count())]})
            st.dataframe(summary,hide_index=True,width='stretch')
            st.download_button('↓ Export participant records',csv(u),f'participant_{who}.csv','text/csv')
        with st.expander('Inspect daily records'):
            st.dataframe(u[['date','TotalSteps','Calories','active_minutes','sleep_hours','hr_mean_bpm']],hide_index=True,width='stretch')
    with tab2:
        ids=sorted(d.Id.unique());picked=st.multiselect('Compare up to 4 participants',ids,default=ids[:min(3,len(ids))],max_selections=4,format_func=lambda x:'P'+x)
        if not picked:empty('Select at least one participant to compare.')
        else:
            metric=st.selectbox('Comparison measure',list(METRICS),key='compare_metric');column=METRICS[metric]
            sub=d[d.Id.isin(picked)];summary=user_stats(sub)
            with st.container(border=True):
                heading(metric+' by participant','Mean over each participant’s available records')
                g=sub.groupby(['Id','participant'],as_index=False).agg(value=(column,'mean'),records=(column,'count'))
                chart(px.bar(g,x='participant',y='value',hover_data=['records'],color_discrete_sequence=[RED],labels={'participant':'','value':metric}),285)
            with st.container(border=True):
                heading('Compare daily patterns','Gaps remain visible')
                grid=pd.MultiIndex.from_product([picked,pd.date_range(d.date.min(),d.date.max())],names=['Id','date']).to_frame(index=False)
                t=grid.merge(sub[['Id','date',column]],how='left',on=['Id','date']);t['participant']='P'+t.Id.astype(str)
                chart(px.line(t,x='date',y=column,color='participant',markers=True,color_discrete_sequence=PALETTE,labels={column:metric,'date':''}),310)
            st.dataframe(summary.drop(columns='Id').round(2),hide_index=True,width='stretch')
            st.download_button('↓ Export comparison',csv(summary),'participant_comparison.csv','text/csv')

elif page=='Goal tracker':
    title('Goals you can explore.','Adjust the step goal and see how recorded achievement changes across the sample.')
    explain_scope();hit=d.TotalSteps.ge(goal);stats=user_stats(d)
    cards([('SELECTED DAILY GOAL',f'{goal:,}','Change it in the sidebar'),('GOAL DAYS',f'{hit.sum():,}',f'Out of {len(d):,} observed user-days'),('ACHIEVEMENT RATE',f'{100*hit.mean():.1f}%','Observed days at or above the goal'),('MEDIAN DAILY STEPS',fmt(d.TotalSteps.median()),'Middle value of observed user-days')])
    l,r=st.columns(2)
    with l,st.container(border=True):
        heading('Daily goal achievement','Denominator: observed participants that day')
        v=d.assign(hit=hit).groupby('date',as_index=False).agg(rate=('hit','mean'),n=('Id','nunique'));v['rate']*=100
        f=bar(v,'date','rate');f.update_yaxes(title='Goal achievement (%)',range=[0,100]);f.update_xaxes(title=None);chart(f)
    with r,st.container(border=True):
        heading('What if the goal changed?','A threshold comparison, not a prediction')
        thresholds=range(2000,20001,1000);sim=pd.DataFrame({'Step goal':thresholds,'Observed success (%)':[100*d.TotalSteps.ge(g).mean() for g in thresholds]})
        f=px.line(sim,x='Step goal',y='Observed success (%)',markers=True,color_discrete_sequence=[RED]);f.update_yaxes(range=[0,100]);f.add_vline(x=goal,line_dash='dot',line_color=BLUE);chart(f)
    with st.container(border=True):
        heading('Participant consistency','Ranks use the selected goal and period')
        max_days=int(stats.observed_days.max())
        minimum=st.slider('Minimum observed days',1,max_days,min(7,max_days)) if max_days>1 else 1
        ranked=stats[stats.observed_days.ge(minimum)].sort_values(['goal_pct','avg_steps'],ascending=False)
        ranked['longest_streak']=[longest_streak(d[d.Id.eq(i)],goal) for i in ranked.Id]
        st.dataframe(ranked[['participant','observed_days','avg_steps','goal_pct','longest_streak']].round(1),hide_index=True,width='stretch',column_config={'goal_pct':st.column_config.ProgressColumn('Goal days (%)',min_value=0,max_value=100,format='%.1f%%')})
        st.download_button('↓ Export goal summary',csv(ranked),'goal_summary.csv','text/csv')
    insight('Goals are illustrative exploration settings, not medical recommendations. A missing day breaks a recorded streak; it does not prove that a person missed their real-world goal.')

elif page=='Chart builder':
    title('Build your own view.','Choose a chart and measures. Every view uses your current data selection.')
    explain_scope();controls,canvas=st.columns([1,2.6])
    with controls,st.container(border=True):
        heading('Chart settings')
        kind=st.selectbox('Chart type',['Trend line','Weekday bars','Scatter plot','Histogram','Weekday box plot'])
        metric=st.selectbox('Measure',list(METRICS),key='builder_measure');col=METRICS[metric]
        if kind=='Scatter plot':
            xm=st.selectbox('X-axis measure',list(METRICS),index=1);xcol=METRICS[xm]
            group=st.checkbox('Color by participant',False)
        if kind in ['Trend line','Weekday bars']:agg=st.selectbox('Aggregation',['Mean','Median','Sum'])
        if kind=='Histogram':bins=st.slider('Number of bins',10,60,25,key='builder_bins')
        st.caption('Use the camera icon on the chart to save a PNG. Download the plotted data below.')
    with canvas,st.container(border=True):
        heading(metric+' · '+kind)
        if kind in ['Trend line','Weekday bars']:
            x='date' if kind=='Trend line' else 'weekday';g=d.groupby(x)[col]
            vals=g.sum(min_count=1) if agg=='Sum' else (g.mean() if agg=='Mean' else g.median())
            if x=='weekday':vals=vals.reindex(WEEKDAYS)
            else:vals=vals.reindex(pd.date_range(d.date.min(),d.date.max())).rename_axis('date')
            v=vals.reset_index(name=metric)
            f=px.line(v,x=x,y=metric,markers=True,color_discrete_sequence=[RED]) if x=='date' else bar(v,x,metric)
        elif kind=='Scatter plot':
            v=d[['participant','date',xcol]+([col] if col!=xcol else [])].dropna(subset=list(set([xcol,col])))
            f=px.scatter(v,x=xcol,y=col,color='participant' if group else None,color_discrete_sequence=PALETTE,opacity=.65,hover_data=['date','participant'],labels={xcol:xm,col:metric})
        elif kind=='Histogram':v=d[['participant','date',col]].dropna(subset=[col]);f=px.histogram(v,x=col,nbins=bins,color_discrete_sequence=[RED],labels={col:metric})
        else:v=d[['participant','date','weekday',col]].dropna(subset=[col]);f=px.box(v,x='weekday',y=col,category_orders={'weekday':WEEKDAYS},color_discrete_sequence=[BLUE],labels={col:metric,'weekday':''})
        if v.empty or not v.select_dtypes('number').notna().any().any():empty('No measurements are available for these chart settings.')
        else:chart(f,465)
        st.download_button('↓ Download chart data',csv(v),'chart_data.csv','text/csv')
    with st.expander('Inspect plotted data'):st.dataframe(v,hide_index=True,width='stretch')

elif page=='SQL workspace':
    title('Ask the data with SQL.','Explore the prepared queries, write your own analysis, and visualize the result.')
    explain_scope();library=templates();names=list(library)
    left,right=st.columns([1,2.8])
    with left,st.container(border=True):
        heading('Query library')
        selected=st.selectbox('Choose an analysis',names)
        sql_scope=st.radio('Query scope',['Filtered selection','Full sample'])
        st.caption('daily and hourly use this scope. filtered_daily and filtered_hourly always use the sidebar selection. Other source tables retain the full sample. Q7 uses a fixed 10,000-step goal; edit its SQL to use a different goal.')
        with st.expander('Available fields'):
            st.code('daily\n'+', '.join(base.columns)+'\n\nhourly\n'+', '.join(hourly.columns),language=None)
        st.download_button('↓ Download SQL examples',(ROOT/'analysis.sql').read_bytes(),'analysis.sql')
    with right,st.container(border=True):
        heading('SQL editor','Read-only SQLite · one statement · 10,000-row limit · 5-second timeout')
        q=st.text_area('Query',value=library[selected],height=225,key='editor_'+selected,label_visibility='collapsed')
        a,b=st.columns([1,2])
        with a:run=st.button('Run query',type='primary',width='stretch')
        with b:st.download_button('↓ Save this query',q,'my_analysis.sql',width='stretch')
        token=(str(dates),tuple(chosen),exclude,sql_scope)
        if run:
            try:
                result,truncated,ms=execute_sql(q,d,h,sql_scope);st.session_state['query_result']=(result,truncated,ms,token,q)
            except Exception as e:st.error('The query could not run: '+str(e));st.session_state.pop('query_result',None)
        saved=st.session_state.get('query_result')
        if saved:
            result,truncated,ms,old_token,old_q=saved
            if old_token!=token or old_q!=q:st.info('The query or filters changed. Run the query again to refresh the result.')
            else:
                st.caption(f'{len(result):,} rows returned · {ms} ms')
                if truncated:st.warning('Only the first 10,000 rows are shown and exported.')
                st.dataframe(result,hide_index=True,width='stretch')
                st.download_button('↓ Download result',csv(result),'sql_result.csv','text/csv')
                numeric=list(result.select_dtypes('number').columns)
                if len(result)>1 and numeric:
                    with st.expander('Visualize this result'):
                        x=st.selectbox('X axis',list(result.columns));y=st.selectbox('Y axis',numeric);typ=st.radio('Visual', ['Bar','Line','Scatter'],horizontal=True)
                        if typ=='Bar':f=bar(result,x,y)
                        elif typ=='Line':f=px.line(result,x=x,y=y,markers=True,color_discrete_sequence=[RED])
                        else:f=px.scatter(result,x=x,y=y,color_discrete_sequence=[RED])
                        chart(f,320)
        else:st.info('Select an analysis and run it to see the result here.')

else:
    title('Explore the data behind the view.','Inspect records, understand coverage, and export exactly what you need.')
    explain_scope();tab1,tab2,tab3=st.tabs(['Records & exports','Quality & coverage','About the project'])
    with tab1:
        table=st.selectbox('Dataset',['Daily selection','Hourly selection','All-source daily export (full sample)'])
        source=d if table=='Daily selection' else h if table=='Hourly selection' else read_table('all_sources_daily')
        search=st.text_input('Search participant ID',placeholder='Type an ID or its last digits')
        shown=source[source.Id.astype(str).str.contains(search,regex=False)] if search else source
        default=[x for x in ['Id','date','TotalSteps','Calories','active_minutes','sleep_hours','hr_mean_bpm','hour','StepTotal'] if x in source]
        cols=st.multiselect('Columns',list(source.columns),default=default)
        if not cols:empty('Select at least one column.')
        else:
            export=shown[cols];st.caption(f'{len(export):,} records · {len(cols)} columns');st.dataframe(export,hide_index=True,width='stretch',height=420)
            st.download_button('↓ Download displayed records',csv(export),'fitlens_records.csv','text/csv',type='primary')
        with st.expander('Project downloads (full sample; ignores sidebar filters)'):
            for name in ['merged_daily.csv','merged_hourly.csv','all_sources_daily.csv']:
                st.download_button('↓ '+name,(ROOT/'data'/name).read_bytes(),name,'text/csv')
    with tab2:
        cards([('ZERO-STEP DAYS',str(d.TotalSteps.eq(0).sum()),'Retained unless excluded in filters'),('SLEEP RECORDS',str(d.sleep_hours.count()),f'Of {len(d)} activity user-days'),('HEART-RATE RECORDS',str(d.hr_mean_bpm.count()),f'Of {len(d)} activity user-days'),('WEIGHT RECORDS',str(d.weight_kg.count()),'Sparse auxiliary measurements')])
        coverage=pd.DataFrame({'Measurement':['Activity','Sleep','Heart rate','Weight'],'Recorded user-days':[len(d),d.sleep_hours.count(),d.hr_mean_bpm.count(),d.weight_kg.count()]})
        with st.container(border=True):heading('Measurement availability');chart(bar(coverage,'Recorded user-days','Measurement',BLUE),250)
        with st.expander('Source inventory · full archive'):st.dataframe(inventory,hide_index=True,width='stretch')
        with st.expander('Reconciliation checks · full dataset'):st.json(json.loads((ROOT/'data/validation.json').read_text()))
    with tab3:
        st.subheader('Fitness app analysis')
        st.write('Analyze activity, sleep and recording patterns to identify testable opportunities for a fitness app’s features and wellness marketing.')
        st.write('The assignment is titled Strava, its case study concerns Bellabeat, and its measurements come from Fitbit/Fitabase exports. These are historical sample records, not a live feed or verified Strava customer data.')
        st.markdown('**How the merge works**')
        st.write('Daily activity anchors the main dashboard at one participant per date. Sleep and weight are aggregated before left joins. Hourly files share a separate participant/timestamp key. Minute and second records are summarized before joining. Overlapping wide and narrow exports are kept separate and never added together.')
        st.markdown('**What the data cannot tell us**')
        st.write('Demographics, purchases, marketing outcomes, device wear time and app sessions are unavailable. Recorded days do not measure app retention. This small historical sample cannot represent all Strava users, Bellabeat customers or women. Associations are descriptive, not causal.')
        st.markdown('**Built with**  Python · SQLite · Streamlit · Plotly')
st.markdown('<div class="footer">FitLens 2.0 · Fitness app analysis · Historical Fitbit/Fitabase sample · All measurements describe recorded observations</div>',unsafe_allow_html=True)
