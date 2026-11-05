"""Single-file offline dashboard (double-click to open; Plotly.js embedded; no server, no internet).

Same design system as the Dash and Streamlit apps (ui.py / themes.py): grouped sidebar, channel cards, status pills,
six selectable themes. Reporting and visualisation only; see the safety banner."""
import html
import json

import numpy as np
import pandas as pd
import plotly.io as pio
from plotly.offline import get_plotlyjs

from . import themes, ui, viz

JS = r"""
const $=id=>document.getElementById(id),TH=THEMES,cfg={displaylogo:false,responsive:true,displayModeBar:'hover'};
let theme='midnight',page='overview';
try{const s=localStorage.getItem('mineenv-theme');if(s&&TH[s])theme=s;else if(!matchMedia('(prefers-color-scheme: dark)').matches)theme='daylight'}catch(e){if(!matchMedia('(prefers-color-scheme: dark)').matches)theme='daylight'}
const T=()=>TH[theme];
function lay(title,x,y,h){const t=T();return {title:{text:title,x:.01,font:{size:15,color:t.ink}},paper_bgcolor:t.surface,plot_bgcolor:t.surface,height:h,font:{family:'system-ui,sans-serif',size:12,color:t.ink2},
 margin:{l:56,r:20,t:56,b:50},legend:{orientation:'h',y:-.22,font:{color:t.ink2}},hoverlabel:{bgcolor:t.surface,font:{color:t.ink},bordercolor:t.axis},
 xaxis:{title:x,gridcolor:t.grid,linecolor:t.axis,zeroline:false,tickfont:{color:t.muted}},yaxis:{title:y,gridcolor:t.grid,linecolor:t.axis,zeroline:false,tickfont:{color:t.muted}}}}
function renderMap(){const t=T(),lv=$('lv').value,L=DATA.locations.filter(l=>l.level===lv),tr=[];
 L.forEach(l=>{if(l.seg)tr.push({type:'scatter',mode:'lines',x:[l.seg[0],l.seg[2]],y:[l.seg[1],l.seg[3]],line:{color:t.axis,width:6},hoverinfo:'skip',showlegend:false})});
 Object.keys(DATA.states).forEach(s=>{const g=L.filter(l=>l.state===s);if(!g.length)return;const S=DATA.states[s],open=S.symbol.indexOf('open')>=0||S.symbol==='x';
  tr.push({type:'scatter',mode:'markers+text',name:S.label,x:g.map(l=>l.x),y:g.map(l=>l.y),text:g.map(l=>l.id),textposition:'top center',textfont:{size:11,color:t.ink2},
   marker:{symbol:S.symbol,size:17,color:S.color,line:{width:2,color:open?S.color:t.surface}},customdata:g.map(l=>[l.name,l.type,l.hover]),
   hovertemplate:'<b>%{customdata[0]}</b> (%{customdata[1]})<br>%{customdata[2]}<extra>'+S.label+'</extra>'})});
 const Lo=lay('State of the latest readings, level '+lv,'Schematic east (m)','Schematic north (m)',470);Lo.yaxis.scaleanchor='x';Lo.yaxis.scaleratio=1;Plotly.react('fig-map',tr,Lo,cfg)}
function renderHist(){const c=DATA.channels[+$('ch').value],t=T();if(!c)return;const tr=[],shapes=[],ann=[],band=(a,b)=>shapes.push({type:'rect',xref:'x',yref:'paper',x0:a,x1:b,y0:0,y1:1,fillcolor:t.muted,opacity:.18,line:{width:0},layer:'below'});
 c.gaps.forEach(g=>band(g[0],g[1]));
 tr.push({type:'scatter',mode:'lines',name:'Readings',x:c.t,y:c.v,connectgaps:false,line:{color:t.accent,width:1.8},hovertemplate:'%{x}<br>%{y:g} '+c.unit+'<extra></extra>'});
 const ix=c.t.map((_,i)=>i),hi=ix.filter(i=>c.f[i]===2),qi=ix.filter(i=>c.f[i]===1);
 if(hi.length)tr.push({type:'scatter',mode:'markers',name:'Meets a review criterion',x:hi.map(i=>c.t[i]),y:hi.map(i=>c.v[i]),marker:{symbol:'diamond',size:9,color:'#d03b3b',line:{width:1,color:t.surface}}});
 if(qi.length)tr.push({type:'scatter',mode:'markers',name:'Quality flag',x:qi.map(i=>c.t[i]),y:qi.map(i=>c.v[i]),marker:{symbol:'triangle-up-open',size:8,color:'#fab219',line:{width:1.6}}});
 c.crit.forEach(k=>{shapes.push({type:'line',xref:'paper',x0:0,x1:1,y0:k.thr,y1:k.thr,line:{color:t.ink2,dash:'dash',width:1.4}});ann.push({xref:'paper',x:0,y:k.thr,text:k.label,showarrow:false,xanchor:'left',yanchor:'bottom',font:{size:10,color:t.ink2}})});
 if(c.openGap){band(c.openGap[0],c.openGap[1]);ann.push({xref:'x',yref:'paper',x:c.openGap[0],y:1,text:'no readings since',showarrow:false,xanchor:'left',font:{size:11,color:t.ink2}})}
 shapes.push({type:'line',xref:'x',yref:'paper',x0:DATA.asOf,x1:DATA.asOf,y0:0,y1:1,line:{color:t.ink,dash:'dot',width:1}});
 const L=lay(c.label+' · grey bands = missing data','',c.ylabel,420);L.shapes=shapes;L.annotations=ann;$('hist-note').textContent=c.reason;$('hist-pill').innerHTML=c.pill;Plotly.react('fig-hist',tr,L,cfg)}
function renderAvail(){const f=FIGS.avail[theme];Plotly.react('fig-avail',f.data,f.layout,cfg)}
function render(){if(page==='overview')renderMap();if(page==='history')renderHist();if(page==='avail')renderAvail()}
function setTheme(n){theme=n;document.documentElement.dataset.theme=n;try{localStorage.setItem('mineenv-theme',n)}catch(e){}$('theme').value=n;document.querySelectorAll('.sw button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.t===n));render()}
function go(p){page=p;document.querySelectorAll('.panel').forEach(x=>x.classList.toggle('on',x.id==='p-'+p));document.querySelectorAll('.nav').forEach(b=>b.classList.toggle('on',b.dataset.p===p));
 document.querySelector('.shell').classList.remove('open');window.scrollTo(0,0);render();setTimeout(()=>window.dispatchEvent(new Event('resize')),30)}
function openHist(i){$('ch').value=String(i);go('history')}
let fil='all';
function applyFilter(){const q=$('q').value.trim().toLowerCase(),F=FILTERS[fil];let n=0;
 document.querySelectorAll('.ch-grid .ch').forEach(c=>{const ok=(!F||F.indexOf(c.dataset.state)>=0)&&(!q||c.dataset.search.indexOf(q)>=0);c.style.display=ok?'':'none';if(ok)n++});
 $('shown').textContent='Showing '+n+' of '+document.querySelectorAll('#grid .ch, .ch-grid .ch').length+' channels';$('noresult').style.display=n?'none':'block'}
window.addEventListener('DOMContentLoaded',()=>{
 DATA.levels.forEach(l=>{const o=document.createElement('option');o.value=l;o.textContent='Level '+l;$('lv').appendChild(o)});
 DATA.channels.forEach((c,i)=>{const o=document.createElement('option');o.value=i;o.textContent=c.label+' ['+c.stateLabel+']';$('ch').appendChild(o)});
 $('lv').onchange=renderMap;$('ch').onchange=renderHist;$('theme').onchange=e=>setTheme(e.target.value);
 document.querySelectorAll('.sw button').forEach(b=>b.onclick=()=>setTheme(b.dataset.t));
 document.querySelectorAll('.nav').forEach(b=>b.onclick=()=>go(b.dataset.p));
 document.querySelectorAll('[data-idx]').forEach(e=>{const f=()=>openHist(+e.dataset.idx);e.onclick=f;e.onkeydown=ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();f()}}});
 document.querySelectorAll('.pt-b').forEach(b=>b.onclick=()=>{fil=b.dataset.f;document.querySelectorAll('.pt-b').forEach(x=>x.setAttribute('aria-selected',x===b));applyFilter()});
 $('q').oninput=()=>{if(page!=='channels')go('channels');applyFilter()};
 document.addEventListener('keydown',e=>{if(e.key==='/'&&document.activeElement.tagName!=='INPUT'&&document.activeElement.tagName!=='SELECT'){e.preventDefault();$('q').focus()}});
 $('menu').onclick=()=>{const s=document.querySelector('.shell');if(matchMedia('(max-width:900px)').matches)s.classList.toggle('open');else s.classList.toggle('collapsed');setTimeout(()=>window.dispatchEvent(new Event('resize')),50)};
 applyFilter();setTheme(theme);go('overview')});
"""


def table_html(df, cols, fmt=None, render=None):
    fmt, render = fmt or {}, render or {}
    if df is None or df.empty:
        return "<p class='empty'>None.</p>"
    h = "".join(f"<th>{html.escape(c.replace('_', ' '))}</th>" for c in cols)
    rows = ""
    for r in df[cols].itertuples(index=False):
        cells = ""
        for c, v in zip(cols, r):
            if c in render:
                s = render[c](v)
            elif v is None or v is pd.NaT or (isinstance(v, float) and np.isnan(v)):
                s = "&ndash;"
            elif isinstance(v, pd.Timestamp):
                s = v.strftime("%Y-%m-%d") if (v.hour, v.minute) == (0, 0) else v.strftime("%Y-%m-%d %H:%M")
            elif c in fmt and not isinstance(v, str):
                s = fmt[c].format(v)
            else:
                s = html.escape(str(v))
            cells += f"<td>{s}</td>"
        rows += f"<tr>{cells}</tr>"
    return f"<div class='tw'><table class='t'><tr>{h}</tr>{rows}</table></div>"


def _series(rd, ch, as_of, gap_factor, max_pts):
    rd = rd.sort_values("ts")
    flag = np.where(rd["criteria_met"] != "", 2, np.where(rd["quality_state"] != "OK", 1, 0))
    keep = np.ones(len(rd), bool)
    if len(rd) > max_pts:                       # decimate quiet data; always keep flagged readings
        stride = int(np.ceil(len(rd) / max_pts)); keep = (np.arange(len(rd)) % stride == 0) | (flag > 0)
    d = rd[keep].assign(f=flag[keep])
    exp = ch["expected_interval_min"]
    ts, v, f, prev = [], [], [], None
    for t, val, fl in zip(d["ts"], d["value"], d["f"]):
        if prev is not None and pd.notna(exp) and (t - prev).total_seconds() / 60 > gap_factor * exp:
            ts.append((prev + (t - prev) / 2).strftime("%Y-%m-%d %H:%M:%S")); v.append(None); f.append(0)
        ts.append(t.strftime("%Y-%m-%d %H:%M:%S")); v.append(None if pd.isna(val) else float(val)); f.append(int(fl)); prev = t
    return ts, v, f


CAL_KIND = {"OVERDUE": "bad", "DUE_SOON": "warn", "OK": "ok"}


def build_offline_html(A, title="Mine environment monitor", gap_factor=2.5, max_points=2000):
    ch, loc, ev, ins, cr, gp = A.channels, A.locations, A.events, A.instruments, A.criteria, A.gaps
    states = {s: dict(color=c, symbol=sy, label=l) for s, (c, sy, l) in viz.STATE_STYLE.items()}
    locs = [dict(id=r.location_id, name=r.name, level=r.level, type=r.type, x=float(r.x), y=float(r.y), state=r.state, hover=viz.hover_for_location(r.location_id, ch),
                 seg=[float(r.x1), float(r.y1), float(r.x2), float(r.y2)] if all(pd.notna(v) for v in (r.x1, r.y1, r.x2, r.y2)) and (r.x1, r.y1) != (r.x2, r.y2) else None)
            for r in loc.itertuples()]
    rows, chans = ch.sort_values(["rank", "location_id", "parameter"]).to_dict("records"), []
    for r in rows:
        rd = A.readings[(A.readings.location_id == r["location_id"]) & (A.readings.instrument_id == r["instrument_id"]) & (A.readings.parameter == r["parameter"])]
        g = gp[(gp.location_id == r["location_id"]) & (gp.instrument_id == r["instrument_id"]) & (gp.parameter == r["parameter"])] if len(gp) else gp
        app = viz.criteria_for(cr, r["location_id"], r["parameter"])
        ts, v, f = _series(rd, r, A.as_of, gap_factor, max_points) if len(rd) else ([], [], [])
        closed, opn = (g[~g["open"]], g[g["open"]]) if len(g) else (g, g)
        fmt = lambda x: x.strftime("%Y-%m-%d %H:%M:%S")
        chans.append(dict(label=viz.channel_label(r), unit=viz.ulabel(r["unit"]), ylabel=f"{viz.plabel(r['parameter'])} ({viz.ulabel(r['unit'])})", state=r["state"],
                          stateLabel=viz.STATE_STYLE[r["state"]][2], reason=r["state_reason"], pill=ui.pill(r["state"]), t=ts, v=v, f=f,
                          gaps=[[fmt(a), fmt(b)] for a, b in zip(closed.gap_start, closed.gap_end)] if len(closed) else [],
                          openGap=[fmt(opn.gap_start.iloc[0]), fmt(opn.gap_end.iloc[0])] if len(opn) else None,
                          crit=[dict(thr=float(c.threshold_std), label=f"{c.criterion_id} {c.comparator} {c.threshold_std:g} ({c.approved_by})") for c in app.itertuples()]))
    data = dict(states=states, locations=locs, levels=sorted(loc.level.unique()), channels=chans, asOf=fmt(A.as_of))
    figs = {"avail": {th: json.loads(pio.to_json(viz.fig_availability(A.availability, th))) for th in themes.ORDER}}
    filters = {k: s for k, _, s in ui.FILTERS}
    counts = ui.filter_counts(ch)
    k = viz.kpis(ch, ev, ins)
    demo = bool(A.notes.get("demo_criteria"))

    att = [(i, r) for i, r in enumerate(rows) if r["state"] != "NO_CRITERION_MET"][:14]
    att_html = "".join(f'<div class="att-i" data-idx="{i}" tabindex="0" role="button"><div><b>{html.escape(viz.channel_label(r))}</b><small>{html.escape(str(r["state_reason"]))}</small></div>{ui.pill(r["state"])}</div>'
                       for i, r in att) or "<p class='empty'>Every channel currently shows &ldquo;none met&rdquo;. This is not a statement that conditions are safe.</p>"
    nav = "".join(f'<div class="ng">{g}</div>' + "".join(f'<button class="nav" data-p="{p}">{ui.icon(ic)}<span>{lab}</span></button>' for p, lab, ic in items) for g, items in ui.NAV)
    sw = "".join(f'<button data-t="{n}" aria-label="{l} theme" title="{l}" aria-pressed="false" style="--a:{themes.THEMES[n]["accent"]};--b:{themes.THEMES[n]["panel"]}"></button>' for n, l in themes.options())
    opts = "".join(f'<option value="{n}">{l}</option>' for n, l in themes.options())
    ptabs = "".join(f'<button class="pt-b" role="tab" data-f="{kk}" aria-selected="{"true" if kk == "all" else "false"}">{lab}<span class="n">{counts[kk]}</span></button>' for kk, lab, _ in ui.FILTERS)

    def head(page, sub):
        return f'<h1 class="pt">{ui.PAGES[page][0]}</h1><p class="ps">{sub}</p>'

    def card(t, body):
        return f'<section class="card"><h2>{t}</h2>{body}</section>'

    ev_t = table_html(ev, ["event_no", "criterion_id", "location_id", "instrument_id", "parameter", "start_ts", "end_ts", "duration_min", "n_readings", "peak_value", "active"],
                {"duration_min": "{:.0f}", "peak_value": "{:g}"}, {"active": lambda v: ui.chip("ACTIVE", "bad") if bool(v) else ui.chip("closed")})
    gp_t = table_html(gp.head(80), ["location_id", "instrument_id", "parameter", "gap_start", "gap_end", "minutes", "open"], {"minutes": "{:.0f}"},
                {"open": lambda v: ui.chip("OPEN: still no data", "warn") if bool(v) else ui.chip("closed")}) if len(gp) else "<p class='empty'>None.</p>"
    ins_t = table_html(ins, ["instrument_id", "instrument_type", "serial_no", "location_id", "status", "last_calibration_date", "cal_due_date", "days_to_cal_due", "cal_status", "calibration_ref"],
                 {"days_to_cal_due": "{:.0f}"}, {"cal_status": lambda v: ui.chip(str(v).replace("_", " "), CAL_KIND.get(str(v), "neutral"))})
    body = f"""<div class='shell'><aside class='side'><div class='brand'><span class='mark'>{ui.icon('logo', 22)}</span><div>Mine Environment<small>Monitor</small></div></div>{nav}
<div class='side-foot'><div class='l'>Theme</div><div class='sw' role='group' aria-label='Theme'>{sw}</div></div></aside>
<main class='main'><div class='topbar'><button class='iconbtn' id='menu' aria-label='Toggle sidebar'>{ui.icon('sidebar', 22)}</button>
<label class='search'>{ui.icon('search')}<input id='q' type='search' placeholder='Search channels, instruments or locations' aria-label='Search channels'><kbd>/</kbd></label>
<div class='top-r'><span class='asof'>As-of {A.as_of:%Y-%m-%d %H:%M} · site time</span><label class='sel'>{ui.icon('palette')}<select id='theme' aria-label='Theme'>{opts}</select></label></div></div>
{ui.banners(demo)}
<section class='panel' id='p-overview'>{head('overview', 'State of the latest readings by location and level. Single file: works offline.')}{ui.kpi_tiles(k)}
<div class='two'><section class='card'><div class='ctl'><h2 style='margin:0'>Level map</h2><select id='lv' class='box' aria-label='Level'></select></div><div id='fig-map' class='plot' style='min-height:470px'></div>{ui.STATUS_KEY}</section>
<section class='card'><h2>Needs attention</h2><div class='att'>{att_html}</div></section></div></section>
<section class='panel' id='p-channels'>{head('channels', 'Every monitored parameter at every location. Select a card to open its history.')}
<section class='card'><div class='pilltabs' role='tablist'>{ptabs}</div><p class='note' id='shown' style='margin:0 0 12px'></p>
{ui.channel_grid(ch, loc, ins, True, rows)}<p class='empty' id='noresult' style='display:none'>No channels match. Clear the search box or choose another filter.</p></section></section>
<section class='panel' id='p-history'>{head('history', 'Readings with missing periods shaded, flagged readings marked and the approved review criteria drawn.')}
<section class='card'><div class='ctl'><label for='ch'>Channel</label><select id='ch' class='box' style='min-width:min(520px,100%)'></select><span id='hist-pill'></span></div><div id='fig-hist' class='plot' style='min-height:420px'></div><p class='note' id='hist-note'></p></section></section>
<section class='panel' id='p-avail'>{head('avail', 'Grey cells mean no readings were received in that period. They are not a sign that conditions were fine.')}<section class='card'><div id='fig-avail' class='plot' style='min-height:340px'></div></section></section>
<section class='panel' id='p-events'>{head('events', 'Runs of readings that met a configured review criterion, and periods with no data.')}{card('Review events', ev_t)}{card('Missing-data gaps', gp_t)}</section>
<section class='panel' id='p-instr'>{head('instr', 'Instrument register and calibration metadata. UNKNOWN means the metadata was not supplied.')}{card('Instruments', ins_t)}</section>
<section class='panel' id='p-crit'>{head('crit', 'Supplied by qualified personnel. This tool never sets or infers limits.')}{card('Review criteria', table_html(cr, ['criterion_id', 'parameter', 'comparator', 'threshold', 'unit', 'name', 'source_reference', 'approved_by', 'approval_date']))}</section>
</main></div>"""
    css = themes.all_themes_css() + ui.BASE_CSS
    return (f"<!doctype html><html lang='en' data-theme='midnight'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{html.escape(title)}</title>"
            f"<style>{css}</style><script>{get_plotlyjs()}</script></head><body>{body}<script>const DATA={json.dumps(data, separators=(',', ':'))};const FIGS={json.dumps(figs, separators=(',', ':'))};"
            f"const THEMES={json.dumps(themes.js_tokens(), separators=(',', ':'))};const FILTERS={json.dumps(filters)};{JS}</script></body></html>")
