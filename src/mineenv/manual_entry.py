"""Offline-first manual data entry: ONE html file, no server, no internet. Entries are queued in the browser's
localStorage and exported as a CSV that the pipeline imports from the manual_entries folder.

The form validates data entry only (required fields, numeric, physically implausible values). It deliberately does
NOT compare readings with review criteria or show any good/bad judgement: it is not an alarm.
"""
import json

from .config import STD_UNITS, UNIT_LABEL, PARAM_LABEL, CONVERSIONS, PLAUSIBLE

CSS = """
:root{--s:#fcfcfb;--p:#f9f9f7;--ink:#0b0b0b;--ink2:#52514e;--g:#e1e0d9;--a:#c3c2b7;--acc:#2a78d6}
body{margin:0;background:var(--p);color:var(--ink);font:15px/1.45 system-ui,-apple-system,'Segoe UI',sans-serif;padding:16px;max-width:760px;margin:auto}
h1{font-size:21px;margin:0 0 4px}.sub{color:var(--ink2);font-size:13px}.box{background:var(--s);border:1px solid var(--g);border-radius:8px;padding:12px 14px;margin:12px 0}
.safety{border:2px solid var(--ink);border-radius:8px;padding:9px 12px;font-size:13px;margin:12px 0;background:#fafaf7}
label{display:block;font-size:12.5px;color:var(--ink2);margin:10px 0 3px}input,select,textarea,button{font:inherit;padding:8px 10px;border:1px solid var(--a);border-radius:6px;background:var(--s);color:var(--ink);width:100%;box-sizing:border-box}
button{width:auto;cursor:pointer}button.pri{background:var(--acc);color:#fff;border-color:var(--acc)}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.err{color:#a02424;font-size:13px;margin-top:8px;min-height:18px}.warn{color:#7a5200;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:12.5px}th,td{border-bottom:1px solid var(--g);padding:5px 6px;text-align:left}.pending{font-weight:600}
@media(max-width:560px){.row{grid-template-columns:1fr}}
"""

JS = r"""
const KEY='mineenv_manual_queue_v1', $=id=>document.getElementById(id);
let queue=[]; try{queue=JSON.parse(localStorage.getItem(KEY)||'[]')}catch(e){queue=[]}
function save(){try{localStorage.setItem(KEY,JSON.stringify(queue))}catch(e){$('err').textContent='Could not save to this browser. Export now.'}}
function pad(n){return String(n).padStart(2,'0')}
function nowLocal(){const d=new Date();return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())+'T'+pad(d.getHours())+':'+pad(d.getMinutes())}
function fmtTs(v){return v.replace('T',' ')+':00'}
function csvCell(s){s=String(s??'');return /[",\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s}
function unitsFor(p){const std=CFG.stdUnits[p];return [std].concat(Object.keys(CFG.conv).filter(k=>k.split('|')[1]===std).map(k=>k.split('|')[0]))}
function validateEntry(e,confirmed){
 if(!e.timestamp)return 'Enter the date and time of the measurement.';
 if(!e.instrument_id)return 'Choose the instrument.'; if(!e.location_id)return 'Choose the location.'; if(!e.parameter)return 'Choose the parameter.';
 if(e.value===''||isNaN(Number(e.value)))return 'Enter the value as a number.';
 if(!e.entered_by)return 'Enter who took the measurement.';
 if(new Date(e.timestamp.replace(' ','T'))>new Date(Date.now()+10*60000))return 'The measurement time is in the future.';
 const std=CFG.stdUnits[e.parameter]; let v=Number(e.value);
 const c=CFG.conv[e.unit+'|'+std]; if(e.unit!==std&&c)v=v*c[0]+c[1];
 const r=CFG.plausible[e.parameter];
 if(r&&(v<r[0]||v>r[1])&&!confirmed)return 'This value is outside the physically possible range ('+r[0]+' to '+r[1]+' '+std+'). Check the unit and the instrument display. If it is exactly what the instrument showed, tick the confirmation box.';
 return '';}
function fillInst(){const s=$('inst');s.innerHTML='<option value="">Choose...</option>'+CFG.instruments.filter(i=>i.status!=='removed').map(i=>'<option value="'+i.id+'">'+i.id+' - '+i.type+(i.status==='out_of_service'?' (OUT OF SERVICE)':'')+'</option>').join('')}
function onInst(){const i=CFG.instruments.find(x=>x.id===$('inst').value);const loc=$('loc'),par=$('par');
 $('oos').textContent=i&&i.status==='out_of_service'?'This instrument is marked out of service in the register. Record the reading only if it was genuinely taken, and tell the instrument owner.':'';
 par.innerHTML=i?i.parameters.map(p=>'<option value="'+p+'">'+(CFG.labels[p]||p)+'</option>').join(''):'';
 if(i&&i.location_id){loc.innerHTML='<option value="'+i.location_id+'">'+i.location_id+' - '+(CFG.locations[i.location_id]||'')+'</option>';loc.disabled=true}
 else{loc.disabled=false;loc.innerHTML='<option value="">Choose...</option>'+Object.keys(CFG.locations).map(k=>'<option value="'+k+'">'+k+' - '+CFG.locations[k]+'</option>').join('')}
 onPar()}
function onPar(){const p=$('par').value;$('unit').innerHTML=p?unitsFor(p).map(u=>'<option value="'+u+'">'+(CFG.unitLabels[u]||u)+'</option>').join(''):''}
function render(){const t=$('q');t.innerHTML='<tr><th>Time</th><th>Instrument</th><th>Location</th><th>Parameter</th><th>Value</th><th>By</th><th></th></tr>'+queue.map((e,i)=>
 '<tr><td>'+e.timestamp+'</td><td>'+e.instrument_id+'</td><td>'+e.location_id+'</td><td>'+e.parameter+'</td><td>'+e.value+' '+(CFG.unitLabels[e.unit]||e.unit)+'</td><td>'+e.entered_by+'</td><td><button onclick="del('+i+')" aria-label="Delete entry '+(i+1)+'">Delete</button></td></tr>').join('');
 $('cnt').textContent=queue.length?queue.length+' entr'+(queue.length===1?'y':'ies')+' saved on this device, NOT yet exported':'No entries waiting.';$('cnt').className=queue.length?'pending':''}
function del(i){if(confirm('Delete this entry?')){queue.splice(i,1);save();render()}}
function add(){const e={timestamp:fmtTs($('ts').value),instrument_id:$('inst').value,parameter:$('par').value,value:$('val').value.trim(),unit:$('unit').value,
 quality:$('qual').value,source:'manual',entered_by:$('by').value.trim(),comment:$('com').value.trim(),location_id:$('loc').value};
 const m=validateEntry(e,$('conf').checked);$('err').textContent=m;if(m)return;
 try{localStorage.setItem('mineenv_by',e.entered_by)}catch(x){}
 queue.push(e);save();render();$('val').value='';$('com').value='';$('conf').checked=false;$('ok').textContent='Saved on this device. Export the CSV when you have a connection to the office computer.';setTimeout(()=>$('ok').textContent='',5000);$('val').focus()}
function exportCsv(){if(!queue.length){$('err').textContent='Nothing to export.';return}
 const H=['timestamp','instrument_id','parameter','value','unit','quality','source','entered_by','comment','location_id'];
 const csv=H.join(',')+'\n'+queue.map(e=>H.map(h=>csvCell(e[h])).join(',')).join('\n')+'\n';
 const d=new Date(),name='manual_entries_'+d.getFullYear()+pad(d.getMonth()+1)+pad(d.getDate())+'_'+pad(d.getHours())+pad(d.getMinutes())+'.csv';
 const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download=name;a.click();
 setTimeout(()=>{if(confirm('Was '+name+' saved successfully? OK clears the saved entries from this device. Cancel keeps them.')){queue=[];save();render()}},800)}
if(typeof document!=='undefined'&&document.getElementById){window.addEventListener('DOMContentLoaded',()=>{
 $('ts').value=nowLocal();try{$('by').value=localStorage.getItem('mineenv_by')||''}catch(e){}
 fillInst();$('inst').onchange=onInst;$('par').onchange=onPar;$('add').onclick=add;$('exp').onclick=exportCsv;$('now').onclick=()=>$('ts').value=nowLocal();render()})}
"""


def build_form(instruments, locations, title="Manual measurement entry (offline)"):
    inst = [dict(id=r.instrument_id, type=r.instrument_type, status=r.status, location_id=r.location_id,
                 parameters=[p.strip() for p in r.parameters.split(";") if p.strip()]) for r in instruments.itertuples() if r.status != "removed"]
    cfg = dict(instruments=inst, locations=dict(zip(locations.location_id, locations.name)), stdUnits=STD_UNITS, labels=PARAM_LABEL, unitLabels=UNIT_LABEL,
               conv={f"{a}|{b}": v for (a, b), v in CONVERSIONS.items()}, plausible={k: list(v) for k, v in PLAUSIBLE.items()})
    body = f"""<h1>{title}</h1><div class='sub'>Works without internet. Entries stay on this device until you export them.</div>
<div class='safety'><b>Data entry only.</b> This form records measurements; it does not assess them and is not an alarm or gas monitor. Follow site procedures for any reading of concern, whatever this form shows.</div>
<div class='box'><div class='row'><div><label for='ts'>Date and time of measurement</label><input type='datetime-local' id='ts'></div><div style='align-self:end'><button id='now' type='button'>Use current time</button></div></div>
<label for='inst'>Instrument</label><select id='inst'></select><div id='oos' class='warn'></div>
<div class='row'><div><label for='loc'>Location</label><select id='loc'></select></div><div><label for='par'>Parameter</label><select id='par'></select></div></div>
<div class='row'><div><label for='val'>Value as shown on the instrument</label><input id='val' inputmode='decimal' autocomplete='off'></div><div><label for='unit'>Unit</label><select id='unit'></select></div></div>
<div class='row'><div><label for='qual'>Quality (optional)</label><select id='qual'><option value=''>Not stated</option><option value='GOOD'>Good</option><option value='SUSPECT'>Suspect (instrument or reading doubtful)</option></select></div>
<div><label for='by'>Taken by</label><input id='by' autocomplete='name'></div></div>
<label for='com'>Comment (optional)</label><textarea id='com' rows='2'></textarea>
<label><input type='checkbox' id='conf' style='width:auto'> Confirm: the value is exactly what the instrument showed (only needed if the form says the value is outside the physically possible range)</label>
<div class='err' id='err' role='alert'></div><div id='ok' class='sub' role='status'></div><button class='pri' id='add' type='button'>Save entry on this device</button></div>
<div class='box'><div id='cnt'></div><table id='q'></table><p><button id='exp' type='button'>Export CSV file</button></p>
<div class='sub'>Copy the exported file into the <b>manual_entries</b> folder on the office computer, then run the pipeline.</div></div>"""
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{title}</title>"
            f"<style>{CSS}</style></head><body>{body}<script>const CFG={json.dumps(cfg, separators=(',', ':'))};{JS}</script></body></html>")
