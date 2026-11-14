"""Exercise the installed APK on a fresh emulator; no mock media player."""
import subprocess as sp, time, re,json,xml.etree.ElementTree as ET
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'evidence';out.mkdir(exist_ok=True)
pkg='org.vector.politicsmemory';report={}
def adb(*args):return sp.check_output(['adb',*args],timeout=35).decode(errors='replace')
def shell(*args):return adb('shell',*args)
def nodes():
    shell('uiautomator','dump','/sdcard/politics-ui.xml')
    return list(ET.fromstring(adb('exec-out','cat','/sdcard/politics-ui.xml')).iter('node'))
def match(text):
    found=[n for n in nodes() if n.get('text')==text or n.get('content-desc')==text]
    assert found,'UI element not found: '+text
    return found[0]
def tap(text):
    n=match(text);a,b,c,d=map(int,re.findall(r'\d+',n.get('bounds')));shell('input','tap',str((a+c)//2),str((b+d)//2));time.sleep(.5)
def screenshot(name):
    (out/(name+'.png')).write_bytes(sp.check_output(['adb','exec-out','screencap','-p'],timeout=25))
def media():
    txt=shell('dumpsys','activity','service',pkg+'/.SpeechService')
    def val(k):
        m=re.search(r'\b'+k+r'=(\S+)',txt);return m.group(1) if m else None
    return {k:val(k) for k in ['active','paused','speed','position_ms','duration_ms','playlist_size']}
shell('wm','size','1080x2340');shell('wm','density','480')
shell('am','start','-n',pkg+'/.MainActivity');time.sleep(4)
screenshot('android-catalogue-k5');tap('复习');match('1 / 561')
screenshot('android-review-hidden-k5')
shell('input','swipe','850','1100','200','1100','280');time.sleep(.6);match('561 / 561')
shell('input','swipe','200','1100','850','1100','280');time.sleep(.6);match('1 / 561')
shell('input','swipe','850','1100','200','1100','280');time.sleep(.6);tap('揭晓');tap('记住');match('1 / 561')
report['global_loop_and_rating_wrap']='PASS'
tap('播放速度');tap('4.0×');play=match('播放或暂停');bounds=list(map(int,re.findall(r'\d+',play.get('bounds'))));play_x=(bounds[0]+bounds[2])//2;play_y=(bounds[1]+bounds[3])//2;shell('input','tap',str(play_x),str(play_y));time.sleep(2)
a=media();assert a['active']=='true' and a['speed']=='4.0' and int(a['position_ms'])>0,a
# Pause via stable geometry obtained before the moving progress ticks start.
shell('input','tap',str(play_x),str(play_y));time.sleep(.4)
if media()['paused']!='true':
    # Toggle via the UI text. On some emulator navigation geometries the y differs.
    tap('播放或暂停')
a=media();assert a['paused']=='true',a
screenshot('android-player-4x-k5');tap('播放速度');tap('2.0×');assert media()['paused']=='true'
tap('播放速度');tap('4.0×');assert media()['paused']=='true'
n=match('播放进度');x1,y1,x2,y2=map(int,re.findall(r'\d+',n.get('bounds')))
shell('input','tap',str((x1+x2)//2),str((y1+y2)//2));time.sleep(.6)
a=media();assert abs(int(a['position_ms'])/int(a['duration_ms'])-.5)<.12,a
report['real_media_4x_pause_and_seek']='PASS'
tap('资料');assert match('播放或暂停') is not None
report['player_survives_tab_switch']='PASS'
tap('同步');texts=[n.get('text') for n in nodes()];assert '同步数据' in texts and '工具' not in texts
assert '每日背诵目标' not in texts;shell('input','keyevent','4')
shell('wm','density','440');time.sleep(2);screenshot('android-k5-density440')
report['display']='1080x2340, emulator density 480 and 440; not physical OPPO hardware'
# Crash log is checked only for this process, not unrelated emulator system services.
logs=adb('logcat','-d','-v','brief');assert not re.search(r'FATAL EXCEPTION[\s\S]{0,300}Process: '+re.escape(pkg),logs)
(out/'android-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
