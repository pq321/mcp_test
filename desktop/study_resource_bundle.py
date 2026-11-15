"""Codex-produced optional resources; no network calls and no progress mutation."""
import hashlib,json,re,zipfile

ID=re.compile(r'[A-Za-z0-9._-]{1,128}\Z')
SHA=re.compile(r'[a-f0-9]{64}\Z')
AUDIO=re.compile(r'audio/[A-Za-z0-9._-]+/[1-9][0-9]*/[A-Za-z0-9._-]+\.mp3\Z')
LIMIT=1024*1024*1024

def ident(value):
    if not isinstance(value,str) or not ID.fullmatch(value) or value in ('.','..'):raise ValueError('Invalid resource ID')
    return value

def integer(value):
    if isinstance(value,bool) or not isinstance(value,int) or value<1:raise ValueError('Invalid resource revision')
    return value

def read_json(z,name,limit=20*1024*1024):
    if z.getinfo(name).file_size>limit:raise ValueError('Resource JSON too large')
    return json.loads(z.read(name))

def inspect_bundle(z):
    entries=[i for i in z.infolist() if not i.is_dir()];names={i.filename for i in entries}
    if len(names)!=len(entries) or len(entries)>40000 or sum(i.file_size for i in entries)>LIMIT:raise ValueError('Invalid resource archive size/duplicates')
    for name in names:
        if name not in ('update.json','study-resources.json') and not re.fullmatch(r'packs/[A-Za-z0-9._-]+\.json',name) and not AUDIO.fullmatch(name):raise ValueError('Unexpected resource path')
    meta=read_json(z,'update.json',65536)
    if meta.get('kind')!='politics-memory-content-update' or meta.get('schema_version')!=1 or meta.get('resource_update') is not True:raise ValueError('Resource update protocol mismatch')
    resource=read_json(z,'study-resources.json')
    if resource.get('schema_version')!=1:raise ValueError('Resource schema mismatch')
    packs=[];cards={}
    for name in sorted(names):
        if not name.startswith('packs/'):continue
        pack=read_json(z,name);pid=ident(pack['pack_id']);integer(pack['pack_revision'])
        if name!='packs/'+pid+'.json' or pack.get('schema_version')!=1 or not isinstance(pack.get('cards'),list) or len(pack['cards'])>20000:raise ValueError('Invalid source pack')
        for c in pack['cards']:
            cid=ident(c['id']);integer(c.get('revision',1))
            if cid in cards:raise ValueError('Duplicate knowledge ID across source packs')
            if not isinstance(c.get('answer'),str) or not isinstance(c.get('question'),str) or not isinstance(c.get('path'),list) or len(c['path'])!=3:raise ValueError('Invalid knowledge record')
            cards[cid]=c
        packs.append(pack)
    for pid,source in resource.get('sources',{}).items():
        ident(pid);integer(source['revision'])
        if not isinstance(source.get('name'),str) or not 0<len(source['name'])<=120:raise ValueError('Invalid source name')
    referenced={}
    for vid,voice in resource.get('voices',{}).items():
        ident(vid);revision=integer(voice['revision'])
        if not isinstance(voice.get('name'),str) or not 0<len(voice['name'])<=120:raise ValueError('Invalid voice name')
        if vid=='default' and voice.get('retired'):raise ValueError('Default voice cannot be retired')
        for cid,item in voice.get('items',{}).items():
            ident(cid);name='audio/'+vid+'/'+str(revision)+'/'+cid+'.mp3'
            if item.get('file')!=name or not SHA.fullmatch(item.get('audio_sha256','')) or not SHA.fullmatch(item.get('text_sha256','')):raise ValueError('Invalid voice index')
            if name not in names:raise ValueError('Voice asset missing; publish the current cumulative optional voice set')
            if not 500<=z.getinfo(name).file_size<=16*1024*1024:raise ValueError('Invalid voice file size')
            digest=hashlib.sha256(z.read(name)).hexdigest()
            if digest!=item['audio_sha256']:raise ValueError('Voice file checksum mismatch')
            c=cards.get(cid)
            if c:
                spoken=(c.get('title') or c['path'][2]).strip()+'\n'+c['answer'].strip()
                if hashlib.sha256(spoken.encode()).hexdigest()!=item['text_sha256']:raise ValueError('Voice text checksum mismatch')
            referenced[name]=digest
    if {n for n in names if n.startswith('audio/')}!=set(referenced):raise ValueError('Unindexed voice asset')
    for cid,a in resource.get('annotations',{}).items():
        ident(cid);integer(a['revision'])
        if not SHA.fullmatch(a.get('answer_sha256','')) or not isinstance(a.get('marks'),list):raise ValueError('Invalid annotation metadata')
        previous=0
        for m in a['marks']:
            start=m.get('start');end=m.get('end')
            if not isinstance(start,int) or not isinstance(end,int) or start<previous or end<=start or m.get('kind') not in ('core','confusion','condition') or not isinstance(m.get('text'),str):raise ValueError('Invalid annotation range')
            previous=end
        c=cards.get(cid)
        if c:
            answer=c['answer'];utf16=answer.encode('utf-16-le')
            if hashlib.sha256(answer.encode()).hexdigest()!=a['answer_sha256']:raise ValueError('Stale annotations')
            for m in a['marks']:
                if utf16[2*m['start']:2*m['end']].decode('utf-16-le')!=m['text']:raise ValueError('Annotation text mismatch')
    return {'kind':'politics-memory-content-update','status':'available','resource_update':True,'release':meta,'packs':packs,'study_resources':resource,'_audio_files':referenced}
