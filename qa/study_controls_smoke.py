#!/usr/bin/env python3
"""Focused UI regression of the four approved additions. No broad test scaffolding."""
import argparse,copy,json,sys,tempfile,threading,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/'desktop'))
from progress_server import Receiver
from study_resource_bundle import inspect_bundle
sys.path.insert(0,str(HERE/'scripts'))
from publish_study_resources import publish

MOCK_STORE="Object.defineProperty(window,'localStorage',{configurable:true,value:{data:{},getItem(k){return this.data[k]||null},setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}}})"

def run(site,isolated=False):
    pack=json.loads((HERE/'data/suyi-full.json').read_text());resources=json.loads((HERE/'data/study-resources.json').read_text());cards=pack['cards'];first=cards[0]
    report={'mode':'isolated DOM' if isolated else 'real HTTP receiver + browser'}
    for c in cards:
        a=resources['annotations'][c['id']];assert a['answer_sha256']==hashlib.sha256(c['answer'].encode()).hexdigest()
        assert any(m.get('cloze') for m in a['marks'])
        end=0
        for m in a['marks']:
            assert end<=m['start']<m['end'];assert c['answer'].encode('utf-16-le')[2*m['start']:2*m['end']].decode('utf-16-le')==m['text'];end=m['end']
    report['all_561_annotations_exact_and_nonoverlapping']='PASS'
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);server=Receiver(('127.0.0.1',0),site,root/'state');thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,args=['--no-sandbox'],**({'executable_path':'/usr/bin/chromium'} if Path('/usr/bin/chromium').exists() else {}))
                context=browser.new_context(viewport={'width':393,'height':851},reduced_motion='reduce');page=context.new_page();errors=[];calls=[]
                page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda req:calls.append(req.url) if '/api/' in req.url else None)
                html=(site/'index.html').read_text()
                def load():
                    if isolated:page.set_content(html,wait_until='load')
                    else:page.goto(base,wait_until='load')
                if isolated:page.evaluate(MOCK_STORE)
                load();page.wait_for_timeout(120)
                assert not calls
                assert page.locator('details[data-open="P:politics-suyi-full"] summary').first.inner_text().startswith('苏一')
                assert not page.locator('details[data-open="P:politics-suyi-full"]').evaluate('(e)=>e.open')
                page.locator('details[data-open="P:politics-suyi-full"] > summary').click()
                assert page.locator('details[data-open^="S:"] > summary').count()==5
                assert page.get_by_text('腿姐',exact=True).count()==0
                report['data_driven_suyi_parent_five_existing_subjects']='PASS'
                page.locator('[data-tab="review"]').click();assert page.locator('#recallPrompt').count()==1 and page.locator('#answer').count()==0
                page.locator('#recallPrompt').click();assert page.locator('#answer').get_attribute('data-mode')=='complete'
                assert page.locator('#answer').inner_text()==first['answer']
                assert page.locator('#answer .study-core').count()>0
                assert page.locator('.title').evaluate('(e)=>getComputedStyle(e).fontSize')=='17px'
                assert page.locator('#answer').evaluate('(e)=>getComputedStyle(e).fontSize')=='14px'
                evidence=HERE/'evidence';evidence.mkdir(exist_ok=True);page.screenshot(path=str(evidence/'v012-web-complete.png'))
                page.locator('#answer').click(position={'x':20,'y':15});assert page.locator('#answer').get_attribute('data-mode')=='cloze'
                assert page.locator('.study-blank').count()>0
                assert not page.locator('.study-blank').evaluate_all('(es)=>es.some(e=>e.hasAttribute("title")||e.dataset.answer)')
                page.screenshot(path=str(evidence/'v012-web-cloze.png'))
                page.locator('#answer').click(position={'x':20,'y':15});assert page.locator('#recallPrompt').count()==1
                report['hidden_full_cloze_hidden_and_original_fonts']='PASS'
                # Real finger-like pointer path, same handlers as the touch screen.
                def swipe(x,y):
                    el=page.locator('#reviewContent');el.dispatch_event('pointerdown',{'pointerId':3,'pointerType':'touch','clientX':x,'clientY':220});el.dispatch_event('pointermove',{'pointerId':3,'pointerType':'touch','clientX':y,'clientY':221});el.dispatch_event('pointerup',{'pointerId':3,'pointerType':'touch','clientX':y,'clientY':221});page.wait_for_timeout(150)
                swipe(330,50);assert page.locator('.counter').inner_text()=='2 / 561';assert page.evaluate('PoliticsMemory.getState().app.mode')==0
                swipe(50,330);assert page.locator('.counter').inner_text()=='1 / 561'
                swipe(50,330);assert page.locator('.counter').inner_text()=='561 / 561'
                swipe(330,50);assert page.locator('.counter').inner_text()=='1 / 561'
                report['finger_left_next_right_previous_loop_no_toggle']='PASS'
                page.wait_for_timeout(500);page.locator('#reveal').click();page.locator('[data-rate="no"]').click();page.wait_for_timeout(200)
                assert page.evaluate('(id)=>PoliticsMemory.getState().reviews[id].reviewCount',first['id'])==1
                page.evaluate('(id)=>PoliticsMemory.start(id)',first['id']);assert 'wrong-before' not in page.locator('.title').get_attribute('class')
                page.locator('.title').dispatch_event('contextmenu');assert 'wrong-before' in page.locator('.title').get_attribute('class')
                page.locator('.title').dispatch_event('contextmenu');assert 'wrong-before' in page.locator('.title').get_attribute('class')
                assert page.evaluate('PoliticsMemory.getState().wrong.length')==0
                report['question_mistake_history_distinct_from_forgotten']='PASS'
                page.get_by_label('播放速度',exact=True).click();assert not page.locator('#voiceOptions').evaluate('(e)=>e.open')
                assert page.locator('#dialog [data-speed]').last.get_attribute('data-speed')=='4'
                page.locator('#voiceOptions summary').click();assert page.locator('[data-voice="default"]').count()==1
                page.screenshot(path=str(evidence/'v012-web-voice.png'))
                page.locator('[data-voice="default"]').click()
                assert page.evaluate('PoliticsMemory.getState().app.mode')==1
                assert not calls
                report['global_voice_folded_below_4x_no_automatic_network']='PASS'
                # Optional upload fixture uses the original MP3 solely to test mechanics; it is NOT a production voice.
                extra=copy.deepcopy(first);extra['id']='fixture.other.first'
                pk={'schema_version':1,'pack_id':'fixture-other','title':'测试来源','pack_revision':1,'cards':[extra]}
                filename='audio/fixture/1/'+first['id']+'.mp3';audio=(site/'audio'/(first['id']+'.mp3')).read_bytes();target=root/filename;target.parent.mkdir(parents=True);target.write_bytes(audio)
                patch={'schema_version':1,'sources':{'fixture-other':{'revision':1,'name':'测试来源'}},'voices':{'fixture':{'revision':1,'name':'验收声音（测试）','items':{first['id']:{'file':filename,'text_sha256':hashlib.sha256(((first.get('title') or first['path'][2]).strip()+'\n'+first['answer'].strip()).encode()).hexdigest(),'audio_sha256':hashlib.sha256(audio).hexdigest()}}}},'annotations':{}}
                zpath=root/'content-update.zip';publish(patch,[pk],root,zpath);server.content_path=zpath
                response=server.content_manifest();assert response['packs'][0]['pack_id']=='fixture-other'
                assert server.get_overlay_audio(filename)==audio
                config={'base':base,'token':server.token}
                if isolated:page.route('**/api/content',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(server.content_manifest(),ensure_ascii=False)))
                before=page.evaluate('PoliticsMemory.getState().events.length')
                delta=page.evaluate('(config)=>PoliticsMemory.fetchContentOnManualSync(config)',config)
                assert delta['added']==1 and page.evaluate('PoliticsMemory.getCards().length')==562
                page.get_by_label('播放速度',exact=True).click();page.locator('#voiceOptions summary').click();page.locator('[data-voice="fixture"]').click()
                assert page.evaluate('PoliticsMemory.getState().app.voice')=='fixture'
                assert page.evaluate('PoliticsMemory.getState().events.length')==before
                assert not page.evaluate('(id)=>PoliticsMemory.getState().reviews[id].needsReview',first['id'])
                page.evaluate('PoliticsMemory.nav("books")');assert page.get_by_text('测试来源',exact=True).count()==1
                pk['pack_revision']=2;pk['cards']=[];publish(patch,[pk],root,zpath)
                page.evaluate('(config)=>PoliticsMemory.fetchContentOnManualSync(config)',config)
                assert page.evaluate('PoliticsMemory.getCards().length')==561
                assert page.evaluate('PoliticsMemory.getState().events.length')==before
                # Voice play reads its synced local cache, not the mutable cloud ZIP.
                zpath.unlink();assert server.get_overlay_audio(filename)==audio
                report['optional_voice_publish_import_global_choice_and_separate_source_retirement']='PASS'
                page.evaluate('PoliticsMemory.nav("review")');load()
                assert page.evaluate('PoliticsMemory.getState().app.mode')==0 and page.evaluate('PoliticsMemory.getState().app.voice')=='fixture'
                assert page.evaluate('(id)=>PoliticsMemory.getState().reviews[id].reviewCount',first['id'])==1
                report['reload_hidden_keeps_voice_progress_and_source_retirement']='PASS'
                assert not errors,errors
                browser.close()
        finally:server.shutdown();server.server_close();thread.join(timeout=2)
    (HERE/'evidence/v012-web.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--site',default=str(HERE/'site'));p.add_argument('--isolated',action='store_true');args=p.parse_args();run(Path(args.site),args.isolated)
