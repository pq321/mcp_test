#!/usr/bin/env python3
"""Exercise this annotation-only update through the existing visible Sync button."""
import argparse,json,sys,tempfile,threading
from pathlib import Path
from urllib.parse import urlencode,urlsplit
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'desktop'))
from progress_server import Receiver

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--old-site',required=True);parser.add_argument('--update',required=True);args=parser.parse_args()
    resources=json.loads((ROOT/'data/study-resources.json').read_text());evidence=ROOT/'evidence/cloze-r2';evidence.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        server=Receiver(('127.0.0.1',0),Path(args.old_site),Path(td));server.content_path=Path(args.update).resolve()
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':393,'height':851},reduced_motion='reduce');calls=[];errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda r:calls.append((r.method,urlsplit(r.url).path)) if '/api/' in r.url else None)
                page.goto(base+'/#'+urlencode({'sync':base+'#'+server.token}),wait_until='load');assert not calls
                page.get_by_role('button',name='复习',exact=True).click();page.get_by_role('button',name='揭晓',exact=True).click()
                first=page.evaluate('PoliticsMemory.getCards()[0].id');page.get_by_role('button',name='记住',exact=True).click();page.wait_for_timeout(300)
                page.evaluate('(id)=>PoliticsMemory.start(id)',first);page.locator('.title').dispatch_event('contextmenu')
                before=page.evaluate('({cards:JSON.stringify(PoliticsMemory.getCards()),reviews:JSON.stringify(PoliticsMemory.getState().reviews),events:JSON.stringify(PoliticsMemory.getState().events),wrong:JSON.stringify(PoliticsMemory.getState().wrong)})');assert not calls
                def sync():
                    page.get_by_role('button',name='同步数据',exact=True).click()
                    page.wait_for_function('/^(同步完成|尚未同步)/.test(document.getElementById("toast").textContent)')
                    assert page.locator('#toast').inner_text().startswith('同步完成')
                    assert calls==[('POST','/api/progress'),('GET','/api/progress'),('GET','/api/content')],calls
                    calls.clear()
                sync()
                after=page.evaluate('({cards:JSON.stringify(PoliticsMemory.getCards()),reviews:JSON.stringify(PoliticsMemory.getState().reviews),events:JSON.stringify(PoliticsMemory.getState().events),wrong:JSON.stringify(PoliticsMemory.getState().wrong)})');assert before==after
                actual=page.evaluate('Object.fromEntries(PoliticsMemory.getCards().map(c=>[c.id,PoliticsMemory.validMarks(c)]))')
                assert all(actual[cid]==a['marks'] for cid,a in resources['annotations'].items())
                sync();assert page.evaluate('JSON.stringify(PoliticsMemory.getState().events)')==before['events']
                page.reload(wait_until='load');assert not calls and page.evaluate('PoliticsMemory.getState().app.mode')==0
                count=page.evaluate('''()=>{const P=PoliticsMemory;let n=0;for(const c of P.getCards()){P.start(c.id);while(P.getState().app.mode!==1)P.toggle();if(document.getElementById('answer').innerText!==c.answer)throw Error('Original text: '+c.id);P.toggle();if(document.querySelectorAll('.study-blank').length!==P.validMarks(c).filter(m=>m.cloze).length)throw Error('Cloze: '+c.id);P.toggle();if(!document.getElementById('recallPrompt'))throw Error('Recall: '+c.id);n++}return n}''');assert count==561
                cards=page.evaluate('PoliticsMemory.getCards().map(c=>c.id)')
                for number in [87,352,428,501,545]:
                    page.evaluate('(id)=>PoliticsMemory.start(id)',cards[number-1]);page.evaluate('while(PoliticsMemory.getState().app.mode!==2)PoliticsMemory.toggle()');page.screenshot(path=str(evidence/f'card-{number}-cloze.png'))
                assert not errors and not calls,errors
                assert page.evaluate('JSON.stringify(PoliticsMemory.getState().reviews)')==before['reviews']
                report={'real_visible_sync_old_web_to_r2':'PASS','all_561_full_cloze_recall':'PASS','all_561_exact_imported_marks':'PASS','original_cards_reviews_events_wrong_flags_retained':'PASS','repeat_sync_no_duplicate_events':'PASS','reload_persists_r2_no_auto_sync':'PASS','physical_phone':'NOT_TESTED','data':'synthetic test records only'}
                (evidence/'manual-update.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));browser.close()
        finally:server.shutdown();server.server_close();thread.join(timeout=2)
if __name__=='__main__':main()
