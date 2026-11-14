"""Small end-to-end release check; uses the real browser, real MP3 and real storage."""
import json, threading, tempfile, sys, os
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]; out=root/'evidence';out.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
    """Serve real files with byte ranges, required by browser media seeking."""
    def log_message(self,*args):pass
    def send_head(self):
        self.byte_range=None
        path=Path(self.translate_path(self.path))
        requested=self.headers.get('Range')
        if not requested or not path.is_file():
            return super().send_head()
        import re
        match=re.fullmatch(r'bytes=(\d*)-(\d*)',requested)
        size=path.stat().st_size
        if not match or size==0:
            self.send_error(416,'Unsupported byte range');return None
        a,b=match.groups()
        if a:
            start=int(a);end=min(size-1,int(b)) if b else size-1
        elif b:
            start=max(0,size-int(b));end=size-1
        else:
            self.send_error(416,'Invalid byte range');return None
        if start>end or start>=size:
            self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return None
        stream=path.open('rb');stream.seek(start)
        self.send_response(206)
        self.send_header('Content-Type',self.guess_type(str(path)))
        self.send_header('Accept-Ranges','bytes')
        self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length',str(end-start+1))
        self.end_headers();self.byte_range=(start,end)
        return stream
    def copyfile(self,source,outputfile):
        if self.byte_range is None:return super().copyfile(source,outputfile)
        remaining=self.byte_range[1]-self.byte_range[0]+1
        while remaining:
            chunk=source.read(min(65536,remaining))
            if not chunk:break
            outputfile.write(chunk);remaining-=len(chunk)
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(root/'site')))
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}'
report={}; errors=[]
with sync_playwright() as p:
    with tempfile.TemporaryDirectory() as profile:
        launch=dict(headless=True,viewport={'width':360,'height':780},device_scale_factor=3)
        if os.environ.get('CHROMIUM_EXECUTABLE'):launch['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
        context=p.chromium.launch_persistent_context(profile,**launch);page=context.pages[0]
        page.on('pageerror',lambda e:errors.append(str(e)));page.goto(base)
        cards=page.evaluate('PoliticsMemory.getCards().map(c=>({id:c.id,path:c.path}))')
        assert len(cards)==561
        page.locator('[data-tab="review"]').click()
        assert page.locator('.counter').inner_text()=='1 / 561'
        page.screenshot(path=str(out/'web-review-hidden.png'))
        # Real gestures: left first -> last, right last -> first, with animation.
        def swipe(x1,x2):
            page.mouse.move(x1,340);page.mouse.down();page.mouse.move(x2,340,steps=14);page.mouse.up();page.wait_for_timeout(450)
        swipe(290,60);assert page.locator('.counter').inner_text()=='561 / 561'
        swipe(60,290);assert page.locator('.counter').inner_text()=='1 / 561'
        boundary=next(i for i,c in enumerate(cards[:-1]) if c['path'][0]!=cards[i+1]['path'][0])
        page.evaluate('(id)=>PoliticsMemory.start(id)',cards[boundary]['id']);swipe(60,290)
        assert page.evaluate('PoliticsMemory.getState().app.session[PoliticsMemory.getState().app.index].id')==cards[boundary+1]['id']
        page.evaluate('(id)=>PoliticsMemory.start(id)',cards[-1]['id']);page.locator('#reveal').click()
        page.locator('[data-rate="yes"]').click();page.wait_for_timeout(450)
        assert page.locator('.counter').inner_text()=='1 / 561'
        assert page.evaluate('PoliticsMemory.getState().app.show') is True
        report['global_loop_gestures_and_rating']='PASS'
        # Start review sound, pause, set 4x without resuming, seek, resume.
        page.locator('#playerToggle').click();page.wait_for_function('PoliticsMemory.getPlayback().time > 0.3')
        page.locator('#playerToggle').click();page.locator('#playerSpeed').select_option('4')
        page.wait_for_timeout(250);assert page.evaluate('PoliticsMemory.getPlayback().paused')
        assert page.evaluate('PoliticsMemory.getPlayback().speed')==4
        rect=page.locator('#seek').bounding_box();page.mouse.click(rect['x']+rect['width']/2,rect['y']+rect['height']/2);page.wait_for_timeout(300)
        try:
            page.wait_for_function('Math.abs(PoliticsMemory.getPlayback().time-PoliticsMemory.getPlayback().duration/2)<2',timeout=6000)
        except Exception:
            diagnostic=page.evaluate('({playback:PoliticsMemory.getPlayback(),seekValue:document.getElementById("seek").value})')
            (out/'web-seek-diagnostic.json').write_text(json.dumps(diagnostic,ensure_ascii=False,indent=2))
            page.screenshot(path=str(out/'web-seek-failure.png'))
            print('SEEK FAILURE',json.dumps(diagnostic),flush=True)
            raise
        state=page.evaluate('PoliticsMemory.getPlayback()');assert state['paused']
        report['http_seek']={'time':state['time'],'duration':state['duration']}
        page.locator('#playerToggle').click();page.wait_for_timeout(600)
        assert not page.evaluate('PoliticsMemory.getPlayback().paused')
        page.screenshot(path=str(out/'web-player-4x.png'))
        page.locator('[data-tab="books"]').click();assert page.locator('#player').is_visible()
        page.locator('#playerToggle').click()
        # Each heading starts audio in its own scope; titles do not change the review universe.
        page.locator('[data-start]').first.click();page.wait_for_function('PoliticsMemory.getPlayback().source === "catalogue"')
        assert len(page.evaluate('PoliticsMemory.getPlayback().queue'))==127
        page.locator('#playerToggle').click()
        page.locator('details[data-open="S:马原"] > summary .name').click()
        page.locator('details[data-open^="C:马原"] > summary .name').first.click()
        page.locator('details[data-open^="T:马原"] > summary .name').first.click()
        page.locator('[data-play]').first.click();page.wait_for_timeout(600)
        assert len(page.evaluate('PoliticsMemory.getPlayback().queue'))==1
        page.locator('#playerToggle').click();page.screenshot(path=str(out/'web-catalogue.png'))
        page.locator('#more').click();assert page.locator('#dialog h2').inner_text()=='同步数据'
        assert page.locator('#dialog .menu-item').count()==2
        with page.expect_download() as dl:page.locator('#export').click()
        saved=json.loads(Path(dl.value.path()).read_text());assert saved['preferences']['speed']==4
        page.locator('#dialog .close').click()
        report['audio_scope_seek_pause_4x_sync']='PASS'
        # Resizing does not overlap fixed controls or introduce horizontal overflow.
        page.locator('[data-tab="review"]').click()
        for width,height in [(320,640),(360,780),(393,851),(412,892),(1366,900)]:
            page.set_viewport_size({'width':width,'height':height})
            box=page.evaluate('''()=>{const ids=['main','ratings','player','nav'];const r=Object.fromEntries(ids.map(id=>[id,document.getElementById(id).getBoundingClientRect().toJSON()]));return {r,sw:document.documentElement.scrollWidth,w:innerWidth}}''')
            assert box['sw']<=box['w']
            assert box['r']['main']['bottom']<=box['r']['ratings']['top']+1
            assert box['r']['ratings']['bottom']<=box['r']['player']['top']+1
            assert box['r']['player']['bottom']<=box['r']['nav']['top']+1
        page.screenshot(path=str(out/'web-desktop.png'))
        context.close()
        context=p.chromium.launch_persistent_context(profile,**launch);page=context.pages[0];page.goto(base)
        assert page.evaluate('PoliticsMemory.getState().app.speed')==4
        assert page.evaluate('(id)=>PoliticsMemory.getState().reviews[id].lastRating',cards[-1]['id'])=='yes'
        context.close()
        # Direct offline HTML launch uses the very same built product, not a test stub.
        context=p.chromium.launch_persistent_context(profile,**launch);page=context.pages[0];page.goto((root/'site/index.html').as_uri())
        page.locator('[data-tab="review"]').click();page.locator('#playerToggle').click();page.wait_for_function('PoliticsMemory.getPlayback().time > 0.3')
        page.locator('#playerToggle').click();page.locator('#playerSpeed').select_option('4')
        rect=page.locator('#seek').bounding_box();page.mouse.click(rect['x']+rect['width']/2,rect['y']+rect['height']/2)
        page.wait_for_function('Math.abs(PoliticsMemory.getPlayback().time-PoliticsMemory.getPlayback().duration/2)<2',timeout=6000)
        state=page.evaluate('PoliticsMemory.getPlayback()');assert state['paused'] and state['speed']==4
        report['file_url_offline_audio']='PASS';report['offline_seek']={'time':state['time'],'duration':state['duration']};context.close()
        report['responsive_layout_and_real_reopen_persistence']='PASS'
assert not errors,errors
report['card_count']=561;report['browser_errors']=errors
(out/'web-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
server.shutdown();print(json.dumps(report,ensure_ascii=False))
