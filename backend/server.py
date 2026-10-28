"""Local-only demo API for the SHAAS banking transaction resilience frontend.
No real rails, accounts, credentials, payments, or reversals are connected.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
import json, sqlite3, hashlib, mimetypes, os
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web'
DB = ROOT / 'backend' / 'data' / 'shaas_demo.sqlite3'
HOST = os.environ.get('SHAAS_HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', '8765'))

TXNS = [
 ('UPI-700413','UPI · Instant',43000,'Pending / Unknown','No final response','09m 42s','VPA masked · n***@upi','idem · a91c…7e10','unknown'),
 ('IMPS-700382','IMPS · Transfer',185000,'Debit posted, credit pending','Partner enquiry due','06m 18s','Beneficiary masked · •••• 8421','RRN · 422817…','success'),
 ('UPI-700351','UPI · Instant',20000,'Possible duplicate debit','Two postings suspected','17m 03s','VPA masked · r***@upi','idem · b44f…12a9','failure'),
 ('NEFT-700299','NEFT · Batch',48000,'Recon break','Timing difference','31m 10s','Beneficiary masked · •••• 1138','UTR · N2810…','success')]
APPROVALS = [
 ('APP-2041','Reverse confirmed duplicate debit','UPI-700351','₹20,000','Two ledger postings share one idempotency reference. Network status must be confirmed before a reversal is approved.','Reversal','SHAAS controller'),
 ('APP-2038','Reconcile debit-credit gap','IMPS-700382','₹1,85,000','Debit is posted and network confirms success. Review pending beneficiary credit completion; no reversal is proposed.','Ledger review','SHAAS controller')]
INCIDENTS = [
 ('INC-9431','Partner response delayed','High','IMPS','Partner bank','42 txns','Diagnosing','88%'),
 ('INC-9429','Possible duplicate posting','Critical','UPI','Core ledger','1 txn · ₹20K','Awaiting approval','96%'),
 ('INC-9428','Gateway timeout increase','Medium','Card','Gateway route','218 txns','Rerouting new traffic','91%'),
 ('INC-9424','EOD file arrival late','Medium','NEFT','SFTP partner','Batch 18','Monitoring','72%')]
RAILS = [('UPI / NPCI','99.31%','148ms','Healthy'),('IMPS','98.94%','321ms','Degraded'),('NEFT / RTGS','99.82%','204ms','Healthy'),('Card gateway · axis-route','97.45%','612ms','Degraded')]
RECON = [
 ('REC-7812','UPI · Network A','Duplicate suspected','₹20,000','17 min','Verify posting, then propose reversal','Review'),
 ('REC-7808','IMPS · Partner B','Debit / credit gap','₹1,85,000','6 min','Confirm network status and beneficiary leg','Review'),
 ('REC-7795','NEFT · Network C','Timing difference','₹48,000','31 min','Auto-match after source confirmation','Matched'),
 ('REC-7791','UPI · Network A','Missing network record','₹7,250','43 min','Request partner status enquiry','Enquiry')]
POLICIES = [
 ('confirm_before_money_action','Confirm status before retry or reversal','No money action while network or ledger state is unknown',1),
 ('reuse_idempotency_key','Reuse original idempotency key','Deduplicate every allowed resubmission',1),
 ('maker_checker','Maker-checker above configured limits','Approver identity differs from the maker',1),
 ('honor_holds','Respect fraud, AML, legal, and account holds','No automatic action on held transactions',1),
 ('amount_velocity_limits','Limit action amount and velocity','Per-action, hourly, and daily controls',1),
 ('fail_safe','Fail safe when source status is unreachable','Preserve pending state and escalate',1),
 ('observe_async','Observe asynchronously','Never block the live payment path',1)]
EVENTS = [
 ('Status enquiry queued','UPI-700413 · pending / unknown','10:18:42','info'),
 ('Maker-checker requested','UPI-700351 · duplicate debit review','10:15:31','amber'),
 ('Provider latency recovered','UPI gateway · new traffic normalized','10:08:12',''),
 ('Auto-match completed','NEFT-700281 · timing difference','09:57:04','')]

def connect():
 c=sqlite3.connect(DB, timeout=10); c.row_factory=sqlite3.Row; return c

def init_db():
 DB.parent.mkdir(parents=True,exist_ok=True)
 with connect() as c:
  c.executescript('''
   CREATE TABLE IF NOT EXISTS transactions(id TEXT PRIMARY KEY,rail TEXT,amount INTEGER,state TEXT,network TEXT,age TEXT,merchant TEXT,key_ref TEXT,enquiry_result TEXT);
   CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY,title TEXT,ref TEXT,amount TEXT,reason TEXT,kind TEXT,maker TEXT,status TEXT DEFAULT 'Pending',checker TEXT DEFAULT '',created TEXT DEFAULT CURRENT_TIMESTAMP);
   CREATE TABLE IF NOT EXISTS incidents(id TEXT PRIMARY KEY,title TEXT,severity TEXT,rail TEXT,hop TEXT,impact TEXT,state TEXT,confidence TEXT);
   CREATE TABLE IF NOT EXISTS reconciliation(id TEXT PRIMARY KEY,rail TEXT,kind TEXT,amount TEXT,age TEXT,suggestion TEXT,status TEXT);
   CREATE TABLE IF NOT EXISTS policies(id TEXT PRIMARY KEY,name TEXT,description TEXT,enabled INTEGER);
   CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,event TEXT,summary TEXT,time TEXT,tone TEXT,actor TEXT,ref TEXT,outcome TEXT);
   CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1),paused INTEGER NOT NULL DEFAULT 0);
   CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT,event TEXT,target TEXT,outcome TEXT,created TEXT,integrity TEXT);
  ''')
  if c.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]==0:
   c.executemany('INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?,?)',TXNS)
   c.executemany('INSERT INTO approvals(id,title,ref,amount,reason,kind,maker) VALUES(?,?,?,?,?,?,?)',APPROVALS)
   c.executemany('INSERT INTO incidents VALUES(?,?,?,?,?,?,?,?)',INCIDENTS)
   c.executemany('INSERT INTO reconciliation VALUES(?,?,?,?,?,?,?)',RECON)
   c.executemany('INSERT INTO policies VALUES(?,?,?,?)',POLICIES)
   c.executemany('INSERT INTO events(event,summary,time,tone,actor,ref,outcome) VALUES(?,?,?,?,?,?,?)',[(e,s,t,n,'SHAAS controller',s.split(' · ')[0],'Recorded') for e,s,t,n in EVENTS])
   c.execute('INSERT OR IGNORE INTO settings(id,paused) VALUES(1,0)')
   for e,s,t,n in EVENTS: audit(c,'SHAAS controller',e,s.split(' · ')[0],'Recorded')

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def audit(c,actor,event,target,outcome):
 stamp=now(); previous=c.execute('SELECT integrity FROM audit ORDER BY id DESC LIMIT 1').fetchone(); prior=previous['integrity'] if previous else 'GENESIS'
 digest=hashlib.sha256(f'{prior}|{stamp}|{actor}|{event}|{target}|{outcome}'.encode()).hexdigest()
 c.execute('INSERT INTO audit(actor,event,target,outcome,created,integrity) VALUES(?,?,?,?,?,?)',(actor,event,target,outcome,stamp,digest))
 c.execute('INSERT INTO events(event,summary,time,tone,actor,ref,outcome) VALUES(?,?,?,?,?,?,?)',(event,f'{target} · {outcome}',stamp[11:19],'amber' if 'reject' in event.lower() or 'unknown' in outcome.lower() else 'info',actor,target,outcome))

def rows(c,table): return [dict(r) for r in c.execute(f'SELECT * FROM {table}').fetchall()]
def fmt_amount(n): return '₹'+format(int(n),',')
def bootstrap(c):
 tx=[]
 for r in c.execute('SELECT * FROM transactions ORDER BY rowid DESC'):
  tx.append({'id':r['id'],'rail':r['rail'],'amount':r['amount'],'state':r['state'],'network':r['network'],'age':r['age'],'merchant':r['merchant'],'key':r['key_ref'],'result':r['enquiry_result']})
 aps=[]
 for r in c.execute("SELECT * FROM approvals WHERE status='Pending' ORDER BY created DESC"):
  aps.append({'id':r['id'],'title':r['title'],'ref':r['ref'],'amount':r['amount'],'reason':r['reason'],'kind':r['kind'],'maker':r['maker']})
 inc=[list(r) for r in c.execute('SELECT * FROM incidents ORDER BY rowid')]
 rails=[list(r) for r in RAILS]
 rec=[list(r) for r in c.execute('SELECT * FROM reconciliation ORDER BY rowid')]
 events=[list(r) for r in c.execute('SELECT event,summary,time,tone FROM events ORDER BY id DESC LIMIT 30')]
 pol={r['id']:bool(r['enabled']) for r in c.execute('SELECT id,enabled FROM policies')}
 paused=bool(c.execute('SELECT paused FROM settings WHERE id=1').fetchone()['paused'])
 pending=sum(1 for x in tx if not any(w in x['state'] for w in ('Success','Matched')))
 return {'transactions':tx,'approvals':aps,'incidents':inc,'rails':rails,'reconciliation':rec,'events':events,'policies':pol,'paused':paused,'metrics':{'stuck':pending,'amountAtRisk':sum(x['amount'] for x in tx if not any(w in x['state'] for w in ('Success','Matched')))}}
class Handler(BaseHTTPRequestHandler):
 server_version='SHAAS-Demo/1.0'
 def log_message(self,fmt,*args): print(f'[{self.log_date_time_string()}] {fmt % args}')
 def send_json(self,status,payload):
  body=json.dumps(payload,ensure_ascii=False).encode('utf-8')
  self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
 def read_json(self):
  n=int(self.headers.get('Content-Length','0'))
  if n>65536: raise ValueError('Request body too large')
  if not n:return {}
  return json.loads(self.rfile.read(n).decode('utf-8'))
 def api(self,method,path):
  c=connect()
  try:
   if method=='GET' and path in ('/api/bootstrap','/api/dashboard'):
    data=bootstrap(c)
    if path.endswith('dashboard'): return 200,{'metrics':data['metrics'],'paused':data['paused']}
    return 200,data
   if method=='GET' and path=='/api/health': return 200,{'status':'ok','mode':'simulated','database':'sqlite'}
   if method=='GET' and path=='/api/transactions': return 200,bootstrap(c)['transactions']
   if method=='GET' and path=='/api/incidents': return 200,bootstrap(c)['incidents']
   if method=='GET' and path=='/api/reconciliation': return 200,bootstrap(c)['reconciliation']
   if method=='GET' and path=='/api/approvals': return 200,bootstrap(c)['approvals']
   if method=='GET' and path=='/api/policies': return 200,{'items':rows(c,'policies')}
   if method=='GET' and path=='/api/audit': return 200,rows(c,'audit')
   if method=='POST' and path=='/api/demo/simulate':
    body=self.read_json(); suffix=datetime.now(timezone.utc).strftime('%H%M%S%f')[-8:]; ident='UPI-70'+suffix
    c.execute('INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?,?)',(ident,'UPI · Instant',int(body.get('amount',12500)),'Pending / Unknown','No final response','Just now','VPA masked · d***@upi','idem · demo…'+suffix,'unknown'))
    audit(c,'SHAAS controller','Stuck transaction detected',ident,'Status enquiry required; no replay')
    c.commit();return 201,{'id':ident,'state':'Pending / Unknown'}
   if method=='POST' and path.startswith('/api/transactions/') and path.endswith('/enquiry'):
    body=self.read_json();ident=unquote(path.split('/')[3]);result=body.get('outcome')
    if result not in ('success','failure','unknown'):return 400,{'error':'outcome must be success, failure, or unknown'}
    t=c.execute('SELECT * FROM transactions WHERE id=?',(ident,)).fetchone()
    if not t:return 404,{'error':'transaction not found'}
    if result=='success': state,network='Success · network confirmed','Confirmed success';message='Network confirms success. Local state updated; no retry or reversal.'
    elif result=='failure': state,network='Failed · reversal review','Confirmed failure';message='Failure confirmed. Reversal routed for maker-checker review.'
    else: state,network='Pending / Unknown','Enquiry unavailable';message='Outcome remains unknown. No retry or reversal; case escalated.'
    c.execute('UPDATE transactions SET state=?,network=? WHERE id=?',(state,network,ident))
    if result=='failure':
     exists=c.execute("SELECT id FROM approvals WHERE ref=? AND status='Pending'",(ident,)).fetchone()
     if not exists:
      aid='APP-'+datetime.now(timezone.utc).strftime('%H%M%S%f')[-8:]
      c.execute('INSERT INTO approvals(id,title,ref,amount,reason,kind,maker) VALUES(?,?,?,?,?,?,?)',(aid,'Review confirmed failed transaction',ident,fmt_amount(t['amount']),'Network status confirms failure. Review ledger debit and configured TAT before approving a reversal through the approved service.','Reversal','SHAAS controller'))
    event='Status enquiry completed';summary=f'{ident} · '+('network success' if result=='success' else 'network failure confirmed' if result=='failure' else 'no authoritative response')
    audit(c,'SHAAS controller',event,ident,message);c.commit();return 200,{'message':message,'state':state,'network':network}
   if method=='POST' and path.startswith('/api/approvals/') and path.endswith('/decision'):
    body=self.read_json();aid=unquote(path.split('/')[3]);decision=body.get('decision');actor=str(body.get('actor','')).strip() or 'Demo operator'
    if decision not in ('approve','reject'):return 400,{'error':'decision must be approve or reject'}
    a=c.execute('SELECT * FROM approvals WHERE id=?',(aid,)).fetchone()
    if not a:return 404,{'error':'approval not found'}
    if a['status']!='Pending':return 409,{'error':'approval is no longer pending'}
    if actor==a['maker']:return 403,{'error':'maker-checker requires a different authenticated actor'}
    outcome='Approved; controlled execution remains pending' if decision=='approve' else 'Rejected and escalated; no money action executed'
    c.execute('UPDATE approvals SET status=?,checker=? WHERE id=?',('Approved' if decision=='approve' else 'Rejected',actor,aid))
    if decision=='approve' and a['kind']=='Reversal':
     c.execute("UPDATE transactions SET state='Reversal approved · execution pending',network='Reversal service gated' WHERE id=?",(a['ref'],))
    audit(c,'A. Morgan' if actor=='Alex Morgan' else actor,'Maker-checker '+decision,a['ref'],outcome);c.commit();return 200,{'message':outcome,'status':'Approved' if decision=='approve' else 'Rejected'}
   if method=='PUT' and path=='/api/policies':
    body=self.read_json();ident=str(body.get('id',''));enabled=bool(body.get('enabled'))
    cur=c.execute('UPDATE policies SET enabled=? WHERE id=?',(int(enabled),ident))
    if cur.rowcount==0:return 404,{'error':'policy not found'}
    name=c.execute('SELECT name FROM policies WHERE id=?',(ident,)).fetchone()['name'];audit(c,'Alex Morgan','Policy updated',name,'Enabled' if enabled else 'Disabled');c.commit();return 200,{'id':ident,'enabled':enabled}
   if method=='POST' and path=='/api/automation':
    body=self.read_json();paused=bool(body.get('paused'));c.execute('UPDATE settings SET paused=? WHERE id=1',(int(paused),));audit(c,'Alex Morgan','Global automation pause' if paused else 'Global automation resume','workspace','Paused' if paused else 'Resumed');c.commit();return 200,{'paused':paused}
   return 404,{'error':'API route not found'}
  except (ValueError,KeyError,json.JSONDecodeError) as e:
   return 400,{'error':str(e)}
  except sqlite3.Error as e:
   return 500,{'error':'database operation failed','detail':str(e)}
  finally:c.close()
 def do_GET(self):
  u=urlparse(self.path);path=unquote(u.path)
  if path.startswith('/api/'):
   status,data=self.api('GET',path);return self.send_json(status,data)
  rel='index.html' if path in ('/','') else path.lstrip('/')
  target=(WEB/rel).resolve()
  if WEB.resolve() not in target.parents and target!=WEB.resolve():return self.send_json(403,{'error':'forbidden'})
  if not target.is_file():return self.send_json(404,{'error':'not found'})
  blob=target.read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(str(target))[0] or 'application/octet-stream');self.send_header('Content-Length',str(len(blob)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(blob)
 def do_POST(self):
  status,data=self.api('POST',urlparse(self.path).path);self.send_json(status,data)
 def do_PUT(self):
  status,data=self.api('PUT',urlparse(self.path).path);self.send_json(status,data)

def main():
 init_db();server=ThreadingHTTPServer((HOST,PORT),Handler)
 print(f'SHAAS banking demo running at http://{HOST}:{PORT}')
 print('Simulated data only. No banking rails or financial accounts are connected.')
 try:server.serve_forever()
 except KeyboardInterrupt:print('\nStopping SHAAS demo server.')
 finally:server.server_close()
if __name__=='__main__':main()


