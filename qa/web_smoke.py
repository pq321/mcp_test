"""Browser/receiver integration using real MP3, real playback completion and real storage."""
import json,sys,threading,tempfile,os,time
from pathlib import Path
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'desktop'))
from progress_server import Receiver
out=root/'evidence';out.mkdir(exist_ok=True);report={};errors=[]

def swipe(page,x1,x2):
    box=page.locator('#reviewContent').bounding_box();y=box['y']+100
    page.mouse.move(x1,y);page.mouse.down();page.mouse.move(x2,y,steps=9);page.mouse.up();page.wait_for_timeout(500)

def seek_end(page):
    page.locator('#seek').focus();page.locator('#seek').press('End')

with tempfile.TemporaryDirectory() as data,tempfile.TemporaryDirectory() as profile:
    server=Receiver(('127.0.0.1',0),root/'site',Path(data));threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}';connection=base+'#'+server.token
    with sync_playwright() as p:
        launch=dict(headless=True,viewport={'width':360,'height':780},device_scale_factor=3)
        if os.environ.get('CHROMIUM_EXECUTABLE'):launch['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
        context=p.chromium.launch_persistent_context(profile,**launch);page=context.pages[0]
        page.on('pageerror',lambda e:errors.append(str(e)));page.goto(base)
        assert page.evaluate('PoliticsMemory.version')==10
        ids=page.evaluate('PoliticsMemory.getCards().map(c=>c.id)');assert len(ids)==561
        page.locator('[data-tab="review"]').click()
        assert page.locator('.counter').inner_text()=='1 / 561'
        swipe(page,285,75);assert page.locator('.counter').inner_text()=='2 / 561'
        swipe(page,75,285);assert page.locator('.counter').inner_text()=='1 / 561'
        swipe(page,75,285);assert page.locator('.counter').inner_text()=='561 / 561'
        swipe(page,285,75);assert page.locator('.counter').inner_text()=='1 / 561'
        page.evaluate('PoliticsMemory.start(PoliticsMemory.getCards()[560].id)');page.locator('#reveal').click();page.get_by_role('button',name='记住',exact=True).click();page.wait_for_timeout(500)
        assert page.locator('.counter').inner_text()=='1 / 561'
        report['finger_left_next_right_previous_first_last_and_rating_wrap']='PASS'
        assert page.evaluate('getComputedStyle(document.querySelector(".answer")).fontSize')=='14px'
        assert page.evaluate('getComputedStyle(document.querySelector(".title")).fontSize')=='17px'
        page.screenshot(path=str(out/'web-review-v010-small.png'))
        page.locator('#playerSpeed').select_option('4');page.locator('#playerToggle').click()
        page.wait_for_function('PoliticsMemory.getPlayback().time>0 && PoliticsMemory.getPlayback().duration>0')
        assert page.evaluate('PoliticsMemory.getPlayback().speed')==4
        page.locator('#playerToggle').click();assert page.evaluate('PoliticsMemory.getPlayback().paused')
        box=page.locator('#seek').bounding_box();page.mouse.click(box['x']+box['width']/2,box['y']+box['height']/2)
        page.wait_for_function('Math.abs(PoliticsMemory.getPlayback().time/PoliticsMemory.getPlayback().duration-.5)<.1')
        page.screenshot(path=str(out/'web-player-v010.png'))
        page.locator('#playerToggle').click();seek_end(page)
        page.wait_for_function('(id)=>PoliticsMemory.getPlayback().playingId===id && !PoliticsMemory.getPlayback().paused',arg=ids[1],timeout=10000)
        assert page.locator('.counter').inner_text()=='2 / 561'
        page.locator('#playerToggle').click();report['real_ended_autonext_and_review_follow']='PASS'
        page.evaluate('PoliticsMemory.start(PoliticsMemory.getCards()[560].id)');page.evaluate('PoliticsMemory.playCurrentAudio()');page.wait_for_function('PoliticsMemory.getPlayback().duration>0&&!PoliticsMemory.getPlayback().paused')
        seek_end(page);page.wait_for_function('(id)=>PoliticsMemory.getPlayback().playingId===id',arg=ids[0],timeout=10000)
        page.locator('#playerToggle').click();report['audio_last_to_first_loop']='PASS'
        page.locator('[data-tab="books"]').click();page.locator('#search').fill(page.evaluate('PoliticsMemory.getCards()[2].title'))
        page.locator('[data-play="'+ids[2]+'"]').click();page.wait_for_function('(id)=>PoliticsMemory.getPlayback().playingId===id&&PoliticsMemory.getPlayback().duration>0',arg=ids[2])
        assert len(page.evaluate('PoliticsMemory.getPlayback().queue'))==561
        seek_end(page);page.wait_for_function('(id)=>PoliticsMemory.getPlayback().playingId===id',arg=ids[3],timeout=10000);page.locator('#playerToggle').click()
        report['individual_play_continues_to_next']='PASS'
        # A second actual browser represents the computer. First browser is the paired phone.
        computer=context.new_page();computer.goto(base+'/#'+urlencode({'sync':connection,'pair':connection}));computer.locator('.close').click()
        # Use a separate browser context, not two tabs sharing localStorage, for the phone.
        mobile=p.chromium.launch(**{k:v for k,v in launch.items() if k not in ['viewport','device_scale_factor']});mc=mobile.new_context(viewport={'width':360,'height':780});phone=mc.new_page();phone.goto(base)
        phone.locator('[data-tab="review"]').click();phone.locator('#reveal').click();phone.get_by_role('button',name='记住',exact=True).click();phone.wait_for_timeout(450)
        phone.locator('#more').click();assert phone.locator('#dialog h2').inner_text()=='连接电脑'
        phone.locator('#connection').fill(connection);phone.locator('#connect').click()
        phone.wait_for_function('document.getElementById("toast").textContent.startsWith("已同步到电脑")')
        computer.wait_for_function('(id)=>PoliticsMemory.getState().reviews[id]?.reviewCount===1',arg=ids[0],timeout=10000)
        saved=json.loads((Path(data)/'progress.json').read_text());assert any(r['card_id']==ids[0] and r['review_count']==1 for r in saved['reviews'])
        n=len(saved['events']);phone.locator('#more').click();phone.wait_for_timeout(600)
        assert not phone.locator('#dialog').evaluate('(e)=>e.open')
        assert len(json.loads((Path(data)/'progress.json').read_text())['events'])==n
        assert server.token not in (Path(data)/'progress.json').read_text()
        computer.locator('[data-tab="stats"]').click();computer.screenshot(path=str(out/'web-desktop-received-progress.png'))
        report['one_tap_phone_to_computer_real_http_and_auto_refresh']='PASS'
        mc.close();mobile.close();context.close()
        context=p.chromium.launch_persistent_context(profile,**launch);page=context.pages[0];page.goto(base)
        assert page.evaluate('(id)=>PoliticsMemory.getState().reviews[id]?.reviewCount',arg=ids[0])==1
        report['reopen_preserves_progress']='PASS'
        for width,height in [(320,693),(360,780),(393,851),(412,892),(1280,900)]:
            page.set_viewport_size({'width':width,'height':height});page.evaluate('PoliticsMemory.nav("review")')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            bounds=page.locator('#nav').bounding_box();assert bounds['y']+bounds['height']<=height+1
        report['compact_fonts_and_responsive_layout']='PASS'
        page.goto((root/'site/index.html').as_uri());page.evaluate('PoliticsMemory.nav("review")');page.locator('#playerToggle').click();page.wait_for_function('PoliticsMemory.getPlayback().time>0')
        seek_end(page);page.wait_for_function('(id)=>PoliticsMemory.getPlayback().playingId===id',arg=ids[1],timeout=10000)
        report['offline_file_audio_autonext']='PASS';context.close()
    server.shutdown();server.server_close()
assert not errors,errors
report['card_count']=561;report['browser_errors']=errors
(out/'web-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
