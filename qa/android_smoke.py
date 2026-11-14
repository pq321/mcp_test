"""Installed APK: finger direction, real auto-next, compact layout, and a real computer receiver."""
import subprocess as sp,time,re,json,xml.etree.ElementTree as ET,threading,tempfile,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'evidence';out.mkdir(exist_ok=True);sys.path.insert(0,str(root/'desktop'))
from progress_server import Receiver
pkg='org.vector.politicsmemory';report={}
def adb(*args):return sp.check_output(['adb',*args],timeout=35).decode(errors='replace')
def shell(*args):return adb('shell',*args)
def nodes():
    shell('uiautomator','dump','/sdcard/politics-ui.xml')
    return list(ET.fromstring(adb('exec-out','cat','/sdcard/politics-ui.xml')).iter('node'))
def match(text):
    found=[n for n in nodes() if n.get('text')==text or n.get('content-desc')==text];assert found,'UI not found: '+text;return found[0]
def bounds(text):return list(map(int,re.findall(r'\d+',match(text).get('bounds'))))
def tap(text):
    a,b,c,d=bounds(text);shell('input','tap',str((a+c)//2),str((b+d)//2));time.sleep(.5)
def screenshot(name):(out/(name+'.png')).write_bytes(sp.check_output(['adb','exec-out','screencap','-p'],timeout=25))
def media():
    txt=shell('dumpsys','activity','service',pkg+'/.SpeechService')
    def v(k):
        m=re.search(r'\b'+k+r'=(\S+)',txt);return m.group(1) if m else None
    return {k:v(k) for k in ['active','paused','speed','position_ms','duration_ms','playlist_size','card_id']}
def wait_media(check):
    for _ in range(30):
        state=media()
        if check(state):return state
        time.sleep(.25)
    raise AssertionError(state)
ids=[c['id'] for c in json.loads((root/'data/suyi-full.json').read_text())['cards']]
shell('wm','size','1080x2340');shell('wm','density','480');shell('am','start','-n',pkg+'/.MainActivity');time.sleep(4)
tap('复习');match('1 / 561')
shell('input','swipe','850','1100','200','1100','280');time.sleep(.6);match('2 / 561')
shell('input','swipe','200','1100','850','1100','280');time.sleep(.6);match('1 / 561')
shell('input','swipe','200','1100','850','1100','280');time.sleep(.6);match('561 / 561')
shell('input','swipe','850','1100','200','1100','280');time.sleep(.6);match('1 / 561')
report['finger_left_next_right_previous_first_last_loop']='PASS'
tap('揭晓');screenshot('android-review-v010-small-k5');tap('记住');match('2 / 561')
tap('播放速度');tap('4.0×');a,b,c,d=bounds('播放或暂停');px=(a+c)//2;py=(b+d)//2
x1,y1,x2,y2=bounds('播放进度');sx=x2-30;sy=(y1+y2)//2
shell('input','tap',str(px),str(py));wait_media(lambda x:x['active']=='true' and x['speed']=='4.0' and int(x['position_ms'])>0)
shell('input','tap',str(px),str(py));wait_media(lambda x:x['paused']=='true')
shell('input','tap',str((x1+x2)//2),str(sy));time.sleep(.6)
a=media();assert abs(int(a['position_ms'])/int(a['duration_ms'])-.5)<.12,a
screenshot('android-player-v010-k5')
shell('input','tap',str(px),str(py));shell('input','tap',str(sx),str(sy))
wait_media(lambda x:x['card_id']==ids[2] and x['paused']=='false')
shell('input','tap',str(px),str(py));wait_media(lambda x:x['paused']=='true');match('3 / 561')
report['real_4x_pause_seek_and_automatic_next']='PASS';report['audio_next_updates_review_without_rating']='PASS'
# An actual Android HTTP upload goes through adb's TCP forwarding to the real receiver.
with tempfile.TemporaryDirectory() as data:
    receiver=Receiver(('127.0.0.1',0),root/'site',Path(data));threading.Thread(target=receiver.serve_forever,daemon=True).start()
    adb('reverse','tcp:18765','tcp:'+str(receiver.server_port))
    connection='http://127.0.0.1:18765#'+receiver.token
    tap('同步');match('连接电脑');tap('电脑连接码');shell('input','text',connection);shell('input','keyevent','4');tap('连接并同步')
    for _ in range(30):
        if receiver.progress.get('reviews'):break
        time.sleep(.3)
    assert any(r['card_id']==ids[0] and r['review_count']==1 for r in receiver.progress['reviews']),receiver.progress
    saved=json.loads((Path(data)/'progress.json').read_text());assert receiver.token not in json.dumps(saved)
    old=receiver.progress['revision'];tap('同步')
    for _ in range(20):
        if receiver.progress['revision']>old:break
        time.sleep(.2)
    assert receiver.progress['revision']>old
    assert len(receiver.progress['events'])==1
    report['android_one_tap_authenticated_upload_to_computer']='PASS'
    report['sync_confirmation_requires_durable_receipt']='PASS'
    receiver.shutdown();receiver.server_close();adb('reverse','--remove','tcp:18765')
    tap('同步');time.sleep(7);match('尚未同步到电脑');tap('关闭')
    report['offline_receiver_does_not_show_success']='PASS'
tap('资料');match('播放或暂停');report['player_survives_tab_switch']='PASS'
shell('wm','density','440');time.sleep(2);tap('复习');screenshot('android-review-v010-density440')
report['display']='1080x2340, emulator density 480 and 440; not physical OPPO K5'
logs=adb('logcat','-d','-v','brief');assert not re.search(r'FATAL EXCEPTION[\s\S]{0,300}Process: '+re.escape(pkg),logs)
(out/'android-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
