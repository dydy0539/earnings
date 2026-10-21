"""Cloud calculation/validation of latest AM and BM using source-verified research.
Fails closed if latest report has no matching, hash-verified research packet.
Research is human/agent prepared; this runner does not invent future research.
"""
from pathlib import Path
from decimal import Decimal as D
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import re,json,hashlib,os,tempfile
ROOT=Path(__file__).resolve().parent.parent
A=ROOT/'analysis'
def strip(s):
 s=re.sub(r'<!-- ONLINE IOMA START -->.*?<!-- ONLINE IOMA END -->','',s,flags=re.S)
 return re.sub(r'<(?:td|th) data-online-ioma="1">.*?</(?:td|th)>','',s,flags=re.S)
def table(headers,rows):
 return '<div class="erqi-scroll"><table><thead><tr>'+''.join('<th>'+str(v)+'</th>' for v in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def pct(v):return f'{v*100:.1f}%'
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def atomic(path,text):
 fd,n=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.')
 try:
  with os.fdopen(fd,'w') as f:f.write(text);f.flush();os.fsync(f.fileno())
  os.replace(n,path)
 finally:
  if os.path.exists(n):os.unlink(n)
def render(target,packet,started):
 original=strip(target.read_text());assert sha(original)==packet['original_sha256'],'Report changed; refresh source research before overwriting'
 soup=BeautifulSoup(original,'html.parser');heading=soup.find(string=re.compile('Filtered companies',re.I));assert heading
 tbl=heading.find_parent().find_next('table');assert tbl
 rows=tbl.find_all('tr');headers=[x.get_text(strip=True) for x in rows[0].find_all(['th','td'])];gi=headers.index('growth_rate')
 tickers=[r.find_all('td')[0].get_text(strip=True) for r in rows[1:] if r.find_all('td')];assert tickers==list(packet['companies'])
 rawtables=list(re.finditer(r'<table\b.*?</table>',original,re.S|re.I));match=next(m for m in rawtables if BeautifulSoup(m.group(),'html.parser').get_text()==tbl.get_text());raw=match.group();rowmatches=list(re.finditer(r'<tr\b.*?</tr>',raw,re.S|re.I))
 assert len(rowmatches)==len(tickers)+1
 notes=[];selected=[];selection=[];calcs={};newrows=[]
 for idx,m in enumerate(rowmatches):
  row=m.group();cells=list(re.finditer(r'<(?:th|td)\b.*?</(?:th|td)>',row,re.S|re.I));assert len(cells)==len(headers)
  if idx==0:extra='<th data-online-ioma="1">IOMA</th><th data-online-ioma="1">IOMA &gt; current margin?</th>'
  else:
   k=tickers[idx-1];x=packet['companies'][k];r,r0,p,p0=[D(x[n]) for n in ['r','r0','p','p0']];dr=r-r0;dp=p-p0
   i=dp/dr if dr else None;cm=p/r if r else None;pm=p0/r0 if r0 else None;div=dr<0 and dp>0;ok=(i is not None and cm is not None and i>=cm-D('.01')) or div
   strict='n/a — zero denominator' if i is None or cm is None else ('Yes' if i>cm else 'No');ip=pct(i) if i is not None else 'n/a — zero revenue change';mp=pct(cm) if cm is not None else 'n/a — zero revenue'
   gap=(i-cm)*100 if i is not None and cm is not None else None
   reason='favorable profit/revenue divergence' if div else ('within threshold' if ok else ('not assessable' if gap is None else 'more than 1.0pp below current margin'))
   if ok:selected.append(k)
   caveat=' Negative revenue denominator.' if dr<0 else ''
   if div:caveat+=' Profit improved on lower revenue; signed negative ratio retained. ERQI override applies.'
   extra=f'<td data-online-ioma="1"><a href="#ioma-{k}">{ip}</a><br>{x["basis"]}{caveat}</td><td data-online-ioma="1">{strict} — {mp}<br>{x["marginbasis"]}</td>'
   notes.append(f'<article id="ioma-{k}"><h3>{k}</h3><p>{x["quarter"]}; USD millions. {x["note"]}</p>'+table(['Input','Current','Prior'],[['Revenue',r,r0],[x['basis'],p,p0],[x['marginbasis'],mp,pct(pm) if pm is not None else 'n/a']])+f'<p>Δ revenue = {dr}; Δ profit = {dp}. IOMA = ({p} − {p0}) / ({r} − {r0}) = {ip}. Current margin = {p}/{r} = {mp}. Strict unrounded comparison: {strict}. Gap = {gap} percentage points. ERQI: {reason}.{caveat} <a href="{x["source"]}">Primary release and reconciliation</a></p></article>')
   selection.append([k,x['basis'],ip,mp,f'{gap:.3f}' if gap is not None else 'n/a',('Selected: ' if ok else 'Excluded: ')+reason])
   calcs[k]={'ioma':str(i),'margin':str(cm),'gap_pp':str(gap),'selected':ok,'strict':strict,'divergence':div}
  at=cells[gi].end();newrows.append(row[:at]+extra+row[at:])
 for m,new in reversed(list(zip(rowmatches,newrows))):raw=raw[:m.start()]+new+raw[m.end():]
 result=original[:match.start()]+raw+original[match.end():]
 date,session=re.search(r'(\d{8})_(AM|BM)',target.name).groups();local=ZoneInfo('Asia/Shanghai');dt=datetime.strptime(date,'%Y%m%d').replace(tzinfo=ZoneInfo('America/New_York'))
 # Report dates are explicitly selected from latest branch filenames, not inferred from delayed execution.
 ny=dt.replace(hour=20,minute=30) if session=='AM' else dt.replace(hour=9,minute=30)
 intended=ny.astimezone(local);actual=datetime.fromisoformat(started);late=(actual-intended).total_seconds()
 metadata=f'Explicit online report selection: {target.name}. Reference scheduled local occurrence {intended.isoformat()} (Asia/Shanghai); corresponding New York {ny.isoformat()}. Actual runner start {started}, runner IANA timezone Etc/UTC; actual Asia/Shanghai {actual.astimezone(local).isoformat()}; signed lateness {late:+.3f} seconds. This is a manual cloud rerun, not a claim about a queued occurrence. Source cutoff {packet["source_cutoff"]}.'
 body=(A/'style.html').read_text()+'<section class="erqi-scope" id="ioma-calculations"><h2>IOMA calculations and source notes</h2><p>'+metadata+'</p>'+''.join(notes)+'</section>'
 notesblock='<!-- ONLINE IOMA START -->'+body+'<!-- ONLINE IOMA END -->'
 pos=match.start()+len(raw);result=result[:pos]+notesblock+result[pos:]
 body='<section class="erqi-scope" id="erqi-results"><h2>ERQI — earnings quality and IOMA durability</h2><p>Rule: unrounded IOMA ≥ same-basis current margin minus 1.0 percentage point, OR chosen profit rises while revenue falls. Equality qualifies; strict table Yes/No remains a separate mathematical comparison. Eligibility does not establish improvement or durability. Source cutoff '+packet['source_cutoff']+'.</p>'+table(['Ticker','Basis','IOMA','Margin','Gap (pp)','Selection'],selection)+'<nav>'+''.join(f'<a href="#erqi-{k}">{k}</a> ' for k in selected)+'</nav>'
 for k in selected:
  research=A/'research'/f'{k}-2026Q3.html';assert research.exists(),f'Missing full ERQI research: {k}'
  content=research.read_text();rs=BeautifulSoup(content,'html.parser');assert len(rs.select('.erqi-card'))==3
  body+=content
 if not selected:body+='<p>No companies qualify for ERQI.</p>'
 body+='</section>'
 block='<!-- ONLINE IOMA START -->'+body+'<!-- ONLINE IOMA END -->';assert result.lower().count('</body>')==1;result=result.replace('</body>',block+'</body>')
 assert strip(result)==original,'Original content changed'
 check=BeautifulSoup(result,'html.parser');ft=check.find(string=re.compile('Filtered companies',re.I)).find_parent().find_next('table')
 for row in ft.find_all('tr'):assert len(row.select('[data-online-ioma]'))==2
 ids=[x['id'] for x in check.select('[id]')];assert len(ids)==len(set(ids)),'Duplicate IDs'
 for link in check.select('a[href^="#"]'):assert link['href'][1:] in ids,link['href']
 assert len(check.select('.erqi-card'))==3*len(selected)
 return result,{'report':target.name,'actual_runner_start':started,'runner_timezone':'Etc/UTC','source_cutoff':packet['source_cutoff'],'original_sha256':sha(original),'result_sha256':sha(result),'original_content_exactly_preserved':True,'filtered_rows':len(tickers),'calculated':len(calcs),'unavailable':0,'selected':selected,'calculations':calcs,'visual_qa':'not performed; structural validation only'}
def main():
 started=datetime.now(timezone.utc).isoformat();pending=[]
 for session in ['AM','BM']:
  target=max(ROOT.glob(f'earnings_report_????????_{session}.html'),key=lambda p:p.name)
  packetpath=A/(target.stem.removeprefix('earnings_report_')+'.json');assert packetpath.exists(),f'Latest {session} report requires new source-verified research: {target.name}'
  packet=json.loads(packetpath.read_text());assert packet['report']==target.name
  result,audit=render(target,packet,started);pending.append((target,result,audit))
 for target,result,audit in pending:
  atomic(target,result);atomic(A/(target.stem+'-validation.json'),json.dumps(audit,indent=2))
  print(json.dumps(audit))
if __name__=='__main__':main()
