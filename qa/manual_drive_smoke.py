#!/usr/bin/env python3
"""Browser/receiver integration tests; no live Drive account or external network."""
import hashlib,io,json,os,subprocess,sys,tempfile,threading,time,zipfile
from pathlib import Path
from urllib import request
from urllib.parse import urlencode, urlsplit

HERE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(HERE/'desktop'))
from progress_server import Receiver,encode,empty
from playwright.sync_api import sync_playwright

PACK_FILE=HERE/'data/suyi-full.json'

def post(url, token, payload):
    content=json.dumps(payload,ensure_ascii=False).encode('utf-8')
    req=request.Request(url,data=content,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    with request.urlopen(req,timeout=5) as r:return json.load(r)

def get(url, token):
    with request.urlopen(request.Request(url,headers={'Authorization':'Bearer '+token}),timeout=5) as r:return json.load(r)

def run():
    pack=json.loads(PACK_FILE.read_text())
    updated=dict(pack)
    updated['cards']=pack['cards'][:-1]
    updated['pack_revision']=pack['pack_revision']+1
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);site=root/'site';site.mkdir();drive=root/'drive';drive.mkdir();local=root/'local';local.mkdir()
        initial=empty();(drive/'progress.json').write_text(json.dumps(initial),encoding='utf-8')
        update={'kind':'politics-memory-content-update','schema_version':1,'pack_id':pack['pack_id'],'pack_revision':updated['pack_revision'],'added_ids':[],'updated_ids':[],'deleted_ids':[pack['cards'][-1]['id']]}
        with zipfile.ZipFile(drive/'content-update.zip','w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('update.json',json.dumps(update))
            z.writestr('pack.json',json.dumps(updated,ensure_ascii=False))
            z.writestr('audio-index.json',json.dumps({'schema_version':1,'pack_id':pack['pack_id'],'items':{}}))
        js=(HERE/'preview/app.js').read_text(encoding='utf-8')
        css=(HERE/'preview/app.css').read_text(encoding='utf-8')
        html='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>'''+css+'''</style></head><body><div id="app"><header id="toolbar"></header><main id="main"></main><section id="ratings"></section><section id="player" hidden></section><nav id="nav"></nav></div><div id="toast"></div><dialog id="dialog"></dialog><input id="import" type="file" hidden><script>window.POLITICS_PACK='''+json.dumps(pack,ensure_ascii=False).replace('</','<\\/')+''';window.POLITICS_AUDIO_INDEX={"schema_version":1,"items":{}};</script><script>'''+js+'''</script></body></html>'''
        (site/'index.html').write_text(html,encoding='utf-8')
        server=Receiver(('127.0.0.1',0),site,local)
        server.progress_path=drive/'progress.json';server.content_path=drive/'content-update.zip';server.progress=server.reload_progress()
        th=threading.Thread(target=server.serve_forever,daemon=True);th.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            assert get(base+'/api/content',server.token)['pack']['pack_revision']==updated['pack_revision']
            data={'kind':'politics-memory-progress','schema_version':1,'request_id':'test-one','device_id':'local-phone','sent_at':int(time.time()*1000),'reviews':[{'card_id':pack['cards'][-1]['id'],'score':2,'review_count':3,'due_at':0,'last_review_at':10000,'last_rating':'fuzzy','last_yes_day':'','needs_review':False}],'events':[{'id':'event-one','card_id':pack['cards'][-1]['id'],'rating':'fuzzy','score_before':1,'score_after':2,'at':10000}],'wrong_changes':{},'cursor':{}}
            response=post(base+'/api/progress',server.token,data)
            assert response['ok'] and response['review_count']==1
            assert (drive/'progress.json').exists()
            assert not (drive/'sync-config.json').exists(),'Credential leaked into Drive'
            # The receiver must reload external changes made by Google Drive Desktop.
            ext=get(base+'/api/progress',server.token);ext['revision']=5;(drive/'progress.json').write_text(json.dumps(ext),encoding='utf-8')
            assert get(base+'/api/progress',server.token)['revision']==5
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,args=['--no-sandbox'],**({'executable_path':'/usr/bin/chromium'} if Path('/usr/bin/chromium').is_file() else {}))
                context=browser.new_context(viewport={'width':390,'height':844})
                page=context.new_page();network=[]
                page.on('request',lambda req:network.append((req.method,urlsplit(req.url).path)) if '/api/' in req.url else None)
                page.goto(base+'/#'+urlencode({'sync':base+'#'+server.token}),wait_until='load');page.wait_for_timeout(800)
                assert not network, 'Opening web UI unexpectedly triggered sync'
                assert page.evaluate('PoliticsMemory.getCards().length')==561
                # Use the visible rating and sync controls against the real HTTP receiver.
                page.get_by_role('button',name='复习',exact=True).click()
                page.get_by_role('button',name='揭晓',exact=True).click()
                page.get_by_role('button',name='记住',exact=True).click()
                page.wait_for_timeout(500)
                assert not network, 'Rating unexpectedly triggered sync'
                def click_sync():
                    page.get_by_role('button',name='同步数据',exact=True).click()
                    page.wait_for_function("/^(同步完成|尚未同步)/.test(document.getElementById('toast').textContent)")
                    message=page.locator('#toast').inner_text()
                    assert message.startswith('同步完成'),message
                click_sync()
                assert network==[('POST','/api/progress'),('GET','/api/progress'),('GET','/api/content')],network
                assert page.evaluate('PoliticsMemory.getCards().length')==560
                assert page.evaluate('(id)=>!!PoliticsMemory.getState().reviews[id]',pack['cards'][-1]['id']), 'Retirement discarded rating history'
                saved=json.loads((drive/'progress.json').read_text())
                event_ids=sorted(e['id'] for e in saved['events'])
                assert len(event_ids)==len(set(event_ids))==2,event_ids
                assert len(saved['reviews'])==2,saved['reviews']
                revision=saved['revision'];network.clear()
                click_sync()
                repeated=json.loads((drive/'progress.json').read_text())
                assert repeated['revision']==revision+1
                assert sorted(e['id'] for e in repeated['events'])==event_ids, 'Repeat sync duplicated events'
                assert repeated['reviews']==saved['reviews'], 'Repeat sync changed ratings'
                assert network==[('POST','/api/progress'),('GET','/api/progress'),('GET','/api/content')],network
                assert page.evaluate('localStorage.getItem("politics_suyi_grouped_v07")')
                network.clear();page.reload(wait_until='load');page.wait_for_timeout(300)
                assert not network, 'Reload unexpectedly triggered sync'
                assert page.evaluate('PoliticsMemory.getCards().length')==560,'Retirement lost on reload'
                assert page.evaluate('(id)=>!!PoliticsMemory.getState().reviews[id]',pack['cards'][-1]['id']), 'Reload discarded retired history'
                context.close();browser.close()
            print('PASS: real Sync button POST/receipt/GET/content flow; repeat sync keeps exactly 2 rating events; retirement and history persist; no automatic sync')
        finally:
            server.shutdown();server.server_close();th.join(timeout=2)

if __name__=='__main__':run()

