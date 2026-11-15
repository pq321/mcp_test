#!/usr/bin/env python3
"""Paired phone -> computer progress receiver. Local/trusted-LAN only, no cloud account.

The token lives in local-data/sync-config.json, never in Git or the APK.
Only this file and Python's standard library are needed on a computer.
"""
import argparse, hashlib, hmac, ipaddress, json, os, re, secrets, shutil, socket
import sys, tempfile, threading, time, webbrowser, zipfile
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote, urlencode
from study_resource_bundle import inspect_bundle

MAX_BODY = 8 * 1024 * 1024
ID = re.compile(r'^[A-Za-z0-9._-]{1,128}$')

def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode('utf-8')

def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(encode(value)); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
        try: path.chmod(0o600)
        except OSError: pass
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def number(v, maximum=10**16):
    if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= maximum:
        raise ValueError('Invalid integer in progress')
    return v

def identifier(v):
    if not isinstance(v, str) or not ID.fullmatch(v): raise ValueError('Invalid record ID')
    return v

def validate(payload):
    if not isinstance(payload, dict) or payload.get('kind') != 'politics-memory-progress' or payload.get('schema_version') != 1:
        raise ValueError('Unsupported progress format')
    identifier(payload.get('request_id')); identifier(payload.get('device_id'))
    number(payload.get('sent_at'))
    reviews = payload.get('reviews', []); events = payload.get('events', [])
    if not isinstance(reviews, list) or not isinstance(events, list) or len(reviews)>10000 or len(events)>100000:
        raise ValueError('Too many records')
    for r in reviews:
        identifier(r['card_id']); number(r['score'],4); number(r['review_count'],10000000)
        number(r['last_review_at']); number(r['due_at'])
        if r.get('last_rating') not in ['', 'yes', 'no', 'fuzzy']: raise ValueError('Invalid rating')
        if not isinstance(r.get('last_yes_day',''),str) or len(r.get('last_yes_day',''))>10: raise ValueError('Invalid study date')
        if not isinstance(r.get('needs_review',False),bool): raise ValueError('Invalid review flag')
    for e in events:
        identifier(e['id']); identifier(e['card_id']); number(e['score_before'],4); number(e['score_after'],4); number(e['at'])
        if e.get('rating') not in ['yes','no','fuzzy']: raise ValueError('Invalid event rating')
    changes=payload.get('wrong_changes',{})
    if not isinstance(changes,dict) or len(changes)>10000: raise ValueError('Invalid wrong-question records')
    for cid,c in changes.items():
        identifier(cid); number(c['at'])
        if not isinstance(c['marked'],bool): raise ValueError('Invalid wrong-question flag')
    cursor=payload.get('cursor',{})
    if cursor:
        identifier(cursor['card_id']); number(cursor['updated_at'])
    return payload

def empty():
    return {'kind':'politics-memory-progress','schema_version':1,'revision':0,'reviews':[],'events':[], 'wrong_changes':{},'wrong_ids':[], 'cursor':{}}

def merge(old, incoming):
    result=json.loads(json.dumps(old))
    reviews={r['card_id']:r for r in old.get('reviews',[])}
    for r in incoming['reviews']:
        previous=reviews.get(r['card_id'])
        if previous is None or (r['last_review_at'],r['review_count'])>(previous['last_review_at'],previous['review_count']):
            reviews[r['card_id']]=r
    events={e['id']:e for e in old.get('events',[])}
    for e in incoming['events']:
        if e['id'] in events and events[e['id']]!=e: raise ValueError('Conflicting event ID; existing progress was not overwritten')
        events[e['id']]=e
    changes=result.setdefault('wrong_changes',{})
    for cid,c in incoming.get('wrong_changes',{}).items():
        if cid not in changes or c['at']>changes[cid]['at']: changes[cid]=c
    if incoming.get('cursor',{}).get('updated_at',0)>result.get('cursor',{}).get('updated_at',0):
        result['cursor']=incoming['cursor']
    result['reviews']=sorted(reviews.values(),key=lambda r:r['card_id'])
    result['events']=sorted(events.values(),key=lambda e:(e['at'],e['id']))
    result['wrong_ids']=sorted(cid for cid,c in changes.items() if c['marked'])
    result['revision']=old.get('revision',0)+1
    result['updated_at']=int(time.time()*1000)
    return result

def private_host(host):
    if host=='localhost':return True
    try:
        ip=ipaddress.ip_address(host)
        return ip.is_loopback or (ip.version==4 and any(ip in ipaddress.ip_network(n) for n in ['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16']))
    except ValueError:return False

class Receiver(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self, address, root, data_dir, token=None):
        self.root=Path(root).resolve(); self.data_dir=Path(data_dir).resolve(); self.lock=threading.Lock()
        config=self.data_dir/'sync-config.json'
        if config.exists(): self.token=json.loads(config.read_text())['token']
        else:
            self.token=token or secrets.token_hex(32);atomic_json(config,{'token':self.token})
        if not re.fullmatch('[0-9a-f]{64}',self.token):raise ValueError('Invalid receiver credential')
        progress=self.data_dir/'progress.json'
        self.progress_path=progress
        self.content_path=self.data_dir/'content-update.zip'
        self.progress=json.loads(progress.read_text(encoding='utf-8')) if progress.exists() else empty()
        super().__init__(address,Handler)
    def reload_progress(self):
        if self.progress_path.exists():
            fresh=json.loads(self.progress_path.read_text(encoding='utf-8'))
            if fresh.get('kind')!='politics-memory-progress' or fresh.get('schema_version')!=1:
                raise ValueError('Google Drive progress.json has an incompatible format')
            self.progress=fresh
        return self.progress
    def content_manifest(self):
        if not self.content_path.is_file():return {'kind':'politics-memory-content-update','status':'not-configured'}
        with zipfile.ZipFile(self.content_path,'r') as z:
            names=set(z.namelist())
            if 'update.json' not in names:raise ValueError('content-update.zip has no update.json')
            meta=json.loads(z.read('update.json'))
            if meta.get('kind')!='politics-memory-content-update' or meta.get('schema_version')!=1:
                raise ValueError('content-update.zip protocol mismatch')
            if meta.get('resource_update'):
                result=inspect_bundle(z)
                # Install only during the explicit /api/content Sync request.
                cache=self.data_dir/'study-audio'
                for name,digest in result.pop('_audio_files').items():
                    target=cache/name
                    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest()==digest:continue
                    target.parent.mkdir(parents=True,exist_ok=True)
                    temp=target.with_suffix('.mp3.pending')
                    try:
                        with z.open(name) as src,temp.open('wb') as out:shutil.copyfileobj(src,out)
                        os.replace(temp,target)
                    finally:
                        if temp.exists():temp.unlink()
                return result
            if 'pack.json' not in names:return {'kind':'politics-memory-content-update','status':'no-change','release':meta}
            if 'audio-index.json' not in names:raise ValueError('content-update.zip missing audio-index.json')
            pack=json.loads(z.read('pack.json'));audio=json.loads(z.read('audio-index.json'))
            if pack.get('pack_id')!='politics-suyi-full' or audio.get('pack_id')!=pack.get('pack_id'):
                raise ValueError('content-update.zip pack ID mismatch')
            if len(pack.get('cards',[]))>20000:raise ValueError('content pack too large')
            return {'kind':'politics-memory-content-update','status':'available','release':meta,'pack':pack,'audio_index':audio}
    def get_overlay_audio(self,name):
        if re.fullmatch(r'audio/[A-Za-z0-9._-]+/[1-9][0-9]*/[A-Za-z0-9._-]+\.mp3',name):
            cache=(self.data_dir/'study-audio').resolve();target=(cache/name).resolve()
            if not target.is_relative_to(cache) or not target.is_file():return None
            return target.read_bytes()
        if not self.content_path.is_file():return None
        with zipfile.ZipFile(self.content_path,'r') as z:
            if name not in z.namelist():return None
            if z.getinfo(name).file_size>16*1024*1024:raise ValueError('Content update audio too large')
            b=z.read(name)
            if len(b)<500:raise ValueError('Content update audio missing')
            return b

class Handler(BaseHTTPRequestHandler):
    server_version='PoliticsMemorySync/1'
    def setup(self):
        super().setup(); self.connection.settimeout(15)
    def log_message(self,fmt,*args):
        # Never print bearer tokens, request bodies, or connection fragments.
        pass
    def allowed(self):
        try:host=urlsplit('http://'+self.headers.get('Host','')).hostname
        except ValueError:return False
        return private_host(host) and private_host(self.client_address[0])
    def cors(self):
        origin=self.headers.get('Origin','')
        if origin=='null' or (origin and private_host(urlsplit(origin).hostname)):
            self.send_header('Access-Control-Allow-Origin',origin)
            self.send_header('Vary','Origin')
        self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Authorization, Content-Type, If-None-Match')
        self.send_header('Access-Control-Expose-Headers','ETag')
        self.send_header('Access-Control-Allow-Private-Network','true')
    def reply(self,status,value):
        b=encode(value);self.send_response(status);self.cors()
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(b)
    def authorized(self):
        return hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+self.server.token)
    def do_OPTIONS(self):
        if not self.allowed():return self.reply(403,{'error':'Local network only'})
        self.send_response(204);self.cors();self.send_header('Content-Length','0');self.end_headers()
    def do_GET(self):
        if not self.allowed():return self.reply(403,{'error':'Local network only'})
        path=urlsplit(self.path).path
        if path.startswith('/api/'):
            if not self.authorized():return self.reply(401,{'error':'电脑连接码无效，请重新连接'})
            if path=='/api/health':return self.reply(200,{'service':'politics-memory-sync','protocol':1})
            if path=='/api/progress':
                try:
                    with self.server.lock:snapshot=self.server.reload_progress()
                    return self.reply(200,snapshot)
                except (OSError,ValueError,json.JSONDecodeError):return self.reply(503,{'error':'云端进度文件损坏或不可读取'})
            if path=='/api/content':
                try:return self.reply(200,self.server.content_manifest())
                except (OSError,ValueError,zipfile.BadZipFile,json.JSONDecodeError):return self.reply(503,{'error':'云端知识包无法读取或未校验'})
            return self.reply(404,{'error':'Not found'})
        name=unquote(path).lstrip('/') or 'index.html'
        if name not in ['index.html','audio-index.json'] and not re.fullmatch(r'audio/(?:[A-Za-z0-9._-]+/[1-9][0-9]*/)?[A-Za-z0-9._-]+\.mp3',name):
            return self.reply(404,{'error':'Not found'})
        if name.startswith('audio/'):
            try:overlay=self.server.get_overlay_audio(name)
            except (OSError,ValueError,zipfile.BadZipFile):return self.reply(503,{'error':'更新音频读取失败'})
            if overlay is not None:
                size=len(overlay);start=0;end=size-1;status=200
                requested=self.headers.get('Range')
                if requested:
                    match=re.fullmatch(r'bytes=(\d*)-(\d*)',requested)
                    if not match or not (match[1] or match[2]):return self.reply(416,{'error':'Invalid range'})
                    start=int(match[1]) if match[1] else max(0,size-int(match[2]));end=min(size-1,int(match[2])) if match[1] and match[2] else size-1
                    if start>end or start>=size:return self.reply(416,{'error':'Invalid range'})
                    status=206
                self.send_response(status);self.send_header('Content-Type','audio/mpeg')
                self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes');self.send_header('Cache-Control','no-store')
                if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
                self.end_headers();self.wfile.write(overlay[start:end+1]);return
        target=self.server.root/name
        if not target.is_file() or not target.resolve().is_relative_to(self.server.root):return self.reply(404,{'error':'Not found'})
        size=target.stat().st_size;start=0;end=size-1;status=200
        requested=self.headers.get('Range')
        if requested:
            m=re.fullmatch(r'bytes=(\d*)-(\d*)',requested)
            if not m or not (m[1] or m[2]):return self.reply(416,{'error':'Invalid range'})
            start=int(m[1]) if m[1] else max(0,size-int(m[2]));end=min(size-1,int(m[2])) if m[1] and m[2] else size-1
            if start>end or start>=size:return self.reply(416,{'error':'Invalid range'})
            status=206
        self.send_response(status)
        self.send_header('Content-Type','audio/mpeg' if name.endswith('.mp3') else 'text/html; charset=utf-8' if name.endswith('.html') else 'application/json; charset=utf-8')
        self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes');self.send_header('Cache-Control','no-store');self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Content-Type-Options','nosniff')
        if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        with target.open('rb') as f:
            f.seek(start);remaining=end-start+1
            try:
                while remaining:
                    b=f.read(min(65536,remaining))
                    if not b:break
                    self.wfile.write(b);remaining-=len(b)
            except (BrokenPipeError,ConnectionResetError):pass
    def do_POST(self):
        if not self.allowed():return self.reply(403,{'error':'Local network only'})
        if not self.authorized():return self.reply(401,{'error':'电脑连接码无效，请重新连接'})
        if urlsplit(self.path).path!='/api/progress':return self.reply(404,{'error':'Not found'})
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.reply(415,{'error':'JSON required'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=MAX_BODY:return self.reply(413,{'error':'Progress file too large'})
            raw=self.rfile.read(size)
            if len(raw)!=size:raise ValueError('Incomplete request')
            received_sha256=hashlib.sha256(raw).hexdigest()
            payload=validate(json.loads(raw,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Invalid number'))))
            with self.server.lock:
                combined=merge(self.server.reload_progress(),payload)
                dest=self.server.progress_path
                if dest.exists():shutil.copy2(dest,self.server.data_dir/'progress.previous.json')
                # Reuse the same Drive Desktop file ID by updating it in place.
                # os.replace can create a new Drive file, invalidating Android's SAF URI.
                raw=encode(combined)
                dest.parent.mkdir(parents=True,exist_ok=True)
                with dest.open('wb') as fp:fp.write(raw);fp.flush();os.fsync(fp.fileno())
                if dest.read_bytes()!=raw:raise OSError('Cloud progress write verification failed')
                self.server.progress=combined
            return self.reply(200,{'ok':True,'request_id':payload['request_id'],'received_sha256':received_sha256,'revision':combined['revision'],'saved_at':combined['updated_at'],'review_count':len(payload['reviews'])})
        except (ValueError,TypeError,KeyError) as e:return self.reply(400,{'error':str(e)})
        except OSError:return self.reply(503,{'error':'电脑无法写入进度，尚未保存，请检查磁盘或目录权限'})

def lan_ip():
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        try:s.connect(('8.8.8.8',80));return s.getsockname()[0]
        except OSError:return '127.0.0.1'

def main():
    # Frozen Windows programs may inherit cp1252 even when PYTHONIOENCODING is set.
    # Explicit UTF-8 keeps the Chinese connection instructions from crashing startup.
    for stream in (sys.stdout,sys.stderr):
        if stream is not None and hasattr(stream,'reconfigure'):
            stream.reconfigure(encoding='utf-8',errors='backslashreplace')
    here=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
    default=here if (here/'index.html').is_file() else here.parent/'web-preview'
    parser=argparse.ArgumentParser(description='PoliticsMemory phone-to-computer sync receiver')
    parser.add_argument('--root',type=Path,default=default);parser.add_argument('--data-dir',type=Path)
    parser.add_argument('--port',type=int,default=18765);parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--drive-folder',type=Path,help='Google Drive for desktop mirrored folder containing progress.json and content-update.zip')
    parser.add_argument('--select-drive-folder',action='store_true')
    args=parser.parse_args()
    if not (args.root/'index.html').is_file():parser.error('index.html not found; keep this receiver beside the complete web preview')
    data=args.data_dir or args.root.parent/'local-data'
    # Keep the receiver's bearer token in local-data, NEVER in Google Drive.
    cloud=args.drive_folder
    saved=data/'drive-folder-path.txt'
    if cloud is None and saved.is_file():
        cloud=Path(saved.read_text(encoding='utf-8').strip())
    if args.select_drive_folder and cloud is None:
        try:
            import tkinter as tk
            from tkinter import filedialog
            window=tk.Tk();window.withdraw();window.attributes('-topmost',True)
            path=filedialog.askdirectory(parent=window,title='选择 Google Drive 桌面版同步的 PoliticsMemory 文件夹')
            window.destroy()
            if path:cloud=Path(path)
        except Exception as e:print('文件夹选择器不可用:',e,flush=True)
        if cloud is not None:
            data.mkdir(parents=True,exist_ok=True)
            saved.write_text(str(cloud),encoding='utf-8')
    server=Receiver(('0.0.0.0',args.port),args.root,data)
    if cloud is not None:
        if not cloud.is_dir() or not (cloud/'progress.json').is_file():
            parser.error('所选 Google Drive 文件夹无法读取 progress.json；请检查 Google Drive 桌面版同步')
        server.progress_path=cloud/'progress.json'
        server.content_path=cloud/'content-update.zip'
        server.progress=server.reload_progress()
    host=lan_ip();connection=f'http://{host}:{server.server_port}#{server.token}'
    # Token stays in the browser fragment, not HTTP request logs or referrers.
    local=f'http://127.0.0.1:{server.server_port}/#'+urlencode({'sync':f'http://127.0.0.1:{server.server_port}#{server.token}','pair':connection})
    print('\nPoliticsMemory — 电脑同步已开启\n',flush=True)
    print('手机首次点击同步，粘贴此连接码（仅发给自己的设备）：\n'+connection,flush=True)
    print('\n进度文件：'+str(server.progress_path)+'\n点击网页同步后会写入该文件；手机从 Google Drive 文档读取。\nCtrl+C 关闭。',flush=True)
    if not args.no_browser:threading.Timer(.3,lambda:webbrowser.open(local)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()

