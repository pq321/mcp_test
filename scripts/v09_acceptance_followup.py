"""One-time transfer follow-up; retained source changes are committed after acceptance."""
from pathlib import Path
p=Path('qa/web_smoke.py')
s=p.read_text()
old="""class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
"""
new='''class Quiet(SimpleHTTPRequestHandler):
    """Serve real files with byte ranges, required by browser media seeking."""
    def log_message(self,*args):pass
    def send_head(self):
        self.byte_range=None
        path=Path(self.translate_path(self.path))
        requested=self.headers.get('Range')
        if not requested or not path.is_file():
            return super().send_head()
        import re
        match=re.fullmatch(r'bytes=(\\d*)-(\\d*)',requested)
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
'''
if old in s:s=s.replace(old,new)
s=s.replace("state=page.evaluate('PoliticsMemory.getPlayback()');assert abs(state['time']-state['duration']/2)<2", """try:
            page.wait_for_function('Math.abs(PoliticsMemory.getPlayback().time-PoliticsMemory.getPlayback().duration/2)<2',timeout=6000)
        except Exception:
            diagnostic=page.evaluate('({playback:PoliticsMemory.getPlayback(),seekValue:document.getElementById("seek").value})')
            (out/'web-seek-diagnostic.json').write_text(json.dumps(diagnostic,ensure_ascii=False,indent=2))
            page.screenshot(path=str(out/'web-seek-failure.png'))
            print('SEEK FAILURE',json.dumps(diagnostic),flush=True)
            raise
        state=page.evaluate('PoliticsMemory.getPlayback()');assert state['paused']
        report['http_seek']={'time':state['time'],'duration':state['duration']}""")
s=s.replace("report['file_url_offline_audio']='PASS';context.close()", """page.locator('#playerToggle').click();page.locator('#playerSpeed').select_option('4')
        rect=page.locator('#seek').bounding_box();page.mouse.click(rect['x']+rect['width']/2,rect['y']+rect['height']/2)
        page.wait_for_function('Math.abs(PoliticsMemory.getPlayback().time-PoliticsMemory.getPlayback().duration/2)<2',timeout=6000)
        state=page.evaluate('PoliticsMemory.getPlayback()');assert state['paused'] and state['speed']==4
        report['file_url_offline_audio']='PASS';report['offline_seek']={'time':state['time'],'duration':state['duration']};context.close()""")
p.write_text(s)
p=Path('scripts/build_preview.py');s=p.read_text();s=s.replace('preview\\\\n\'','preview\\n\'').replace('speech.\\\\n\'','speech.\\n\'').replace('data.\\\\n\'','data.\\n\'');p.write_text(s)
