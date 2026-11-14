"""Exercise a real receiver: authentication, durable phone uploads, replay and stale data."""
import json,sys,tempfile,threading,time,urllib.request,urllib.error,copy
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'desktop'))
from progress_server import Receiver

def sample():
    now=int(time.time()*1000)
    return {'schema_version':1,'kind':'politics-memory-progress','request_id':'receipt-1','device_id':'sample-phone','sent_at':now,
    'reviews':[{'card_id':'test-card','score':2,'review_count':1,'last_rating':'yes','last_yes_day':'2026-11-14','due_at':now+1000,'last_review_at':now,'needs_review':False}],
    'events':[{'id':'event-1','card_id':'test-card','rating':'yes','score_before':0,'score_after':2,'at':now}],
    'wrong_changes':{'test-card':{'marked':True,'at':now}},'cursor':{'card_id':'test-card','updated_at':now}}

def request(base,token,payload=None,path='/api/progress'):
    req=urllib.request.Request(base+path,data=json.dumps(payload).encode() if payload is not None else None,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=5) as r:return json.load(r)

if __name__=='__main__':
    with tempfile.TemporaryDirectory() as temp:
        server=Receiver(('127.0.0.1',0),root/'site',Path(temp));threading.Thread(target=server.serve_forever,daemon=True).start()
        base=f'http://127.0.0.1:{server.server_port}';p=sample()
        try:
            try:request(base,'0'*64,p);raise AssertionError('Unauthenticated upload accepted')
            except urllib.error.HTTPError as e:assert e.code==401
            ack=request(base,server.token,p);assert ack['ok'] and ack['request_id']==p['request_id']
            saved=json.loads((Path(temp)/'progress.json').read_text());assert saved['reviews']==p['reviews']
            request(base,server.token,p);assert len(request(base,server.token)['events'])==1
            old=copy.deepcopy(p);old['reviews'][0].update(score=0,last_review_at=p['sent_at']-10000,review_count=0);old['events']=[]
            request(base,server.token,old);assert request(base,server.token)['reviews'][0]['score']==2
            conflict=copy.deepcopy(p);conflict['events'][0]['rating']='no'
            try:request(base,server.token,conflict);raise AssertionError('Conflicting immutable event accepted')
            except urllib.error.HTTPError as e:assert e.code==400
            p['wrong_changes']['test-card']={'marked':False,'at':p['sent_at']+100};request(base,server.token,p);assert not request(base,server.token)['wrong_ids']
            try:request(base,server.token,path='/../local-data/sync-config.json');raise AssertionError('Private credential served')
            except urllib.error.HTTPError as e:assert e.code==404
            assert server.token not in (Path(temp)/'progress.json').read_text()
            server.shutdown();server.server_close()
            reopened=Receiver(('127.0.0.1',0),root/'site',Path(temp));assert reopened.token==server.token and len(reopened.progress['events'])==1;reopened.server_close()
        finally:server.server_close()
    out=root/'evidence';out.mkdir(exist_ok=True);(out/'sync-smoke.json').write_text(json.dumps({'authenticated_http_upload':'PASS','durable_reopen':'PASS','stale_and_duplicate_preservation':'PASS','wrong_question_removal':'PASS','no_secrets_in_progress':'PASS','scope':'Synthetic records over real HTTP; not user personal devices'},indent=2)+'\n')
    print('PASS: real receiver upload and persistence')
