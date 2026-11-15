/* PoliticsMemory v0.11 — user-triggered progress+content synchronization; no background sync. */
(()=>{'use strict';
const PACK=window.POLITICS_PACK,AUDIO_INDEX=window.POLITICS_AUDIO_INDEX||{schema_version:1,items:{}};if(!PACK||!Array.isArray(PACK.cards)){document.getElementById('main').textContent='资料未加载。请保留预览文件完整。';return}
const KEY='politics_suyi_grouped_v07',LEGACY='politics_web_preview_v1',SUBJECTS=['马原','毛中特','新思想','史纲','思修'],SPEEDS=[.75,1,1.25,1.5,1.75,2,2.5,3,3.5,4];
const $=id=>document.getElementById(id),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let stored={};try{stored=JSON.parse(localStorage.getItem(KEY)||'{}')||{}}catch(e){stored={}}
let cards=PACK.cards.map(c=>({...c}));let reviews=stored.reviews||{},events=Array.isArray(stored.events)?stored.events:[],wrong=new Set(stored.wrong||[]),imports=Array.isArray(stored.imports)?stored.imports:[],wrongChanges=stored.wrongChanges||{};
let retired=new Set(stored.retired||[]),contentRevision=Math.max(PACK.pack_revision||1,Number(stored.contentRevision)||0),audioUpdates=stored.audioUpdates||{};
Object.assign(AUDIO_INDEX.items,audioUpdates);
const validCard=c=>c&&typeof c.id==='string'&&c.id.length<200&&Array.isArray(c.path)&&c.path.length===3&&c.path.every(x=>typeof x==='string')&&typeof c.question==='string'&&typeof c.answer==='string';
function mergeCards(list){for(const c of list){if(!validCard(c))throw Error('卡片必须有 id、三层 path、question、answer');const old=cards.find(x=>x.id===c.id);if(old){if((c.revision||1)<(old.revision||1))continue;if(old.question!==c.question||old.answer!==c.answer){if(reviews[c.id])reviews[c.id].needsReview=true}Object.assign(old,c)}else cards.push({...c})}}
try{mergeCards(imports.filter(validCard));cards=cards.filter(c=>!retired.has(c.id))}catch(e){}
const sig=c=>{let h=2166136261;for(const ch of c.question+'\n'+c.answer)h=Math.imul(h^ch.codePointAt(0),16777619);return (h>>>0).toString(16)};
for(const c of cards){const r=reviews[c.id];if(r&&r.contentSig&&r.contentSig!==sig(c))r.needsReview=true}
let app={tab:stored.tab==='review'?'review':'books',show:!!stored.show,goal:Math.max(1,Math.min(500,Number(stored.goal)||25)),speed:SPEEDS.includes(Number(stored.speed))?Number(stored.speed):1,index:Number(stored.index)||0,scope:'全部知识组',positionAt:Number(stored.positionAt)||0,session:[],search:'',open:new Set(stored.open||[])};
const savedCurrent=(stored.session||[])[Number(stored.index)||0]||'';app.session=cards.slice();app.index=Math.max(0,cards.findIndex(c=>c.id===savedCurrent));
let toastTimer,moving=false,suppressUntil=0,gesture=null,audio=new Audio(),playingId='';audio.preload='none';audio.preservesPitch=true;audio.playbackRate=app.speed;
function persist(){try{localStorage.setItem(KEY,JSON.stringify({version:11,reviews,events,wrong:[...wrong],wrongChanges,positionAt:app.positionAt,imports,retired:[...retired],contentRevision,audioUpdates,show:app.show,goal:app.goal,speed:app.speed,index:app.index,scope:app.scope,session:app.session.map(c=>c.id),tab:app.tab,open:[...app.open]}));delete document.body.dataset.storage;return true}catch(e){document.body.dataset.storage='failed';toast('浏览器未允许保存，请点同步把进度保存到电脑。');return false}}
function toast(t){$('toast').textContent=t;$('toast').classList.add('on');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('on'),2400)}
function state(c){return reviews[c.id]||{score:0,reviewCount:0,lastRating:'',lastYesDay:'',dueAt:0,lastReviewAt:0,needsReview:false}}
function mastered(c){const r=state(c);return r.score>=3&&r.lastRating==='yes'&&!r.needsReview}
function label(c){const r=state(c);return r.needsReview?'待复核':!r.reviewCount?'未学':r.lastRating==='no'?'忘记':r.lastRating==='fuzzy'?'模糊':mastered(c)?'已掌握':'待巩固'}
function summary(list){return{total:list.length,studied:list.filter(c=>state(c).reviewCount>0).length,mastered:list.filter(mastered).length,due:list.filter(c=>state(c).reviewCount>0&&(state(c).needsReview||state(c).dueAt<=Date.now())).length}}
function today(){const due=cards.filter(c=>state(c).reviewCount>0&&(state(c).needsReview||state(c).dueAt<=Date.now())).sort((a,b)=>state(a).dueAt-state(b).dueAt);const unseen=cards.filter(c=>!state(c).reviewCount);return [...due,...unseen,...cards.filter(c=>!due.includes(c)&&!unseen.includes(c))]}
function current(){return app.session[app.index]}
function setScope(list,name,start){app.session=cards.slice();app.scope=name;app.index=Math.max(0,app.session.findIndex(c=>c.id===(start||list[0]?.id)));app.tab='review';app.positionAt=Date.now();render();persist()}
function nav(tab){app.tab=tab;if(tab==='review'&&!app.session.length){app.session=today();app.index=0;app.scope='今日复习'}render();persist()}
function renderNav(){$('nav').innerHTML=[['review','复习'],['books','资料'],['stats','统计']].map(([k,t])=>`<button data-tab="${k}" class="${app.tab===k?'active':''}" aria-current="${app.tab===k?'page':'false'}">${t}</button>`).join('');$('nav').querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>nav(b.dataset.tab))}
function toolbar(){const is=app.tab==='review',c=current();$('toolbar').innerHTML=is?'<button id="back" aria-label="返回资料">‹</button><span class="counter">'+(app.session.length?app.index+1:0)+' / '+app.session.length+'</span><button id="reveal">'+(app.show?'收起':'揭晓')+'</button><button id="more" aria-label="同步数据">同步</button>':'<span class="brand">政治背诵</span><button id="more" aria-label="同步数据">同步</button>';$('more').onclick=syncData;$('more').title='v0.11 · 仅点击时同步；长按重新连接';$('more').oncontextmenu=e=>{e.preventDefault();connectComputer()};if(is){$('back').onclick=()=>nav('books');$('reveal').onclick=toggle}}
function render(){gesture=null;renderNav();$('ratings').innerHTML='';if(app.tab==='review'){if(!app.session.length)app.session=today();app.index=app.session.length?((app.index%app.session.length)+app.session.length)%app.session.length:0;renderReview()}else if(app.tab==='books')renderBooks();else renderStats();toolbar();updatePlayer()}
function renderReview(){const c=current();if(!c){$('main').innerHTML='<div class="empty">当前没有待复习的知识组。<br>从资料选择科目或章节，随时开始背诵。</div>';return}
 const paragraphs=c.answer.split(/\n\s*\n/);const answer=paragraphs.length>1?paragraphs.map(p=>`<p>${esc(p)}</p>`).join(''):c.answer.split('\n').map(p=>`<div class="line">${esc(p)}</div>`).join('');
 $('main').innerHTML=`<article class="review-content" id="reviewContent"><div class="path">${esc(c.path.join(' › '))}</div><h1 class="title">${esc(c.title||c.path[2])}</h1><p class="question">${esc(c.question)}</p><hr class="separator">${app.show?`<div class="answer" id="answer">${answer}</div>${c.notes?`<p class="note">${esc(c.notes)}</p>`:''}`:'<div class="recall-prompt" id="recallPrompt">先回忆，再点击揭晓</div>'}</article>`;
 $('main').scrollTop=0;
 $('ratings').innerHTML=`<div class="grade-row"><button class="grade no" data-rate="no" ${app.show?'':'disabled'}>忘记</button><button class="grade fuzzy" data-rate="fuzzy" ${app.show?'':'disabled'}>模糊</button><button class="grade yes" data-rate="yes" ${app.show?'':'disabled'}>记住</button></div>`;
 $('ratings').querySelectorAll('[data-rate]').forEach(b=>b.onclick=()=>rate(b.dataset.rate));
 const title=$('main').querySelector('.title');title.oncontextmenu=e=>{e.preventDefault();wrong.has(c.id)?wrong.delete(c.id):wrong.add(c.id);wrongChanges[c.id]={marked:wrong.has(c.id),at:Date.now()};persist();toast(wrong.has(c.id)?'已加入错题':'已移出错题')};
 const el=$('reviewContent');el.onclick=e=>{if(Date.now()<suppressUntil||moving||e.target.closest('button,select,a'))return;toggle()};
 el.addEventListener('pointerdown',e=>{if(e.pointerType==='mouse'&&e.button!==0)return;gesture={id:e.pointerId,x:e.clientX,y:e.clientY,dx:0,dy:0,axis:null};});
 el.addEventListener('pointermove',e=>{if(!gesture||gesture.id!==e.pointerId||moving)return;const g=gesture;g.dx=e.clientX-g.x;g.dy=e.clientY-g.y;if(!g.axis&&Math.max(Math.abs(g.dx),Math.abs(g.dy))>9)g.axis=Math.abs(g.dx)>Math.abs(g.dy)*1.35?'x':'y';if(g.axis==='x'){e.preventDefault();try{el.setPointerCapture(e.pointerId)}catch(err){}el.style.transform=`translateX(${g.dx}px)`;suppressUntil=Date.now()+350}else if(g.axis==='y')suppressUntil=Date.now()+250});
 const end=e=>{if(!gesture||gesture.id!==e.pointerId)return;const g=gesture;gesture=null;if(g.axis==='x'){suppressUntil=Date.now()+450;if(Math.abs(g.dx)>60){step(g.dx>0?-1:1,g.dx); // Finger x decreases -> next; finger x increases -> previous.
return}bounce(el)}else if(g.axis==='y')suppressUntil=Date.now()+300};el.addEventListener('pointerup',end);el.addEventListener('pointercancel',()=>{gesture=null;suppressUntil=Date.now()+300;bounce(el)});
}
function reduced(){return matchMedia('(prefers-reduced-motion: reduce)').matches}
function bounce(el){if(!el)return;el.style.transition=reduced()?'none':'transform 160ms ease-out';el.style.transform='translateX(0)';setTimeout(()=>{el.style.transition=''},170)}
function toggle(){if(moving||!current())return;app.show=!app.show;renderReview();toolbar();persist()}
function step(dir,startDx=0){if(moving||app.tab!=='review'||!app.session.length)return;const count=app.session.length,target=(app.index+dir+count)%count,el=$('reviewContent');moving=true;const sign=dir>0?-1:1,dist=Math.max(100,$('main').clientWidth);if(el){el.style.transition=reduced()?'none':'transform 150ms ease-out';el.style.transform='translateX('+sign*dist+'px)'}setTimeout(()=>{app.index=target;app.positionAt=Date.now();renderReview();toolbar();if(playSource==='review'&&playingId)playQueue(rotated(app.session,app.index),'review',audio.paused);updatePlayer();const incoming=$('reviewContent');if(incoming&&!reduced()){incoming.style.transition='none';incoming.style.transform='translateX('+(-sign*dist)+'px)';requestAnimationFrame(()=>requestAnimationFrame(()=>{incoming.style.transition='transform 170ms ease-out';incoming.style.transform='translateX(0)'}))}persist();setTimeout(()=>{moving=false;if(incoming)incoming.style.transition=''},reduced()?0:190)},reduced()?0:155)}
function day(ms){const d=new Date(ms);return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-')}
function nextDay(now,n){const d=new Date(now);d.setDate(d.getDate()+n);return +d}
function rate(kind){if(!app.show||moving||!current()||!['no','fuzzy','yes'].includes(kind))return;const c=current(),r=state(c),now=Date.now();let score=r.score,yesDay=r.lastYesDay||'';if(kind==='no')score=0;else if(kind==='fuzzy')score=Math.max(1,score-1);else{score=yesDay===day(now)?Math.max(2,score):Math.min(4,Math.max(2,score+1));yesDay=day(now)}const due=kind==='no'?now+600000:kind==='fuzzy'?nextDay(now,1):nextDay(now,score===2?1:score===3?3:7);
 reviews[c.id]={score,reviewCount:r.reviewCount+1,lastRating:kind,lastYesDay:yesDay,lastReviewAt:now,dueAt:due,needsReview:false,contentSig:sig(c)};events.push({id:globalThis.crypto?.randomUUID?.()||`${now}-${Math.random()}`,card_id:c.id,rating:kind,score_before:r.score,score_after:score,at:now});persist();step(1)}
const unique=x=>[...new Set(x)];
function knowledgeRow(c){return `<div class="entry-row"><button class="entry-name" data-review="${esc(c.id)}">${esc(c.title||c.question)}</button><span class="badge">${esc(label(c))}</span><button class="entry-play" data-play="${esc(c.id)}" aria-label="播放${esc(c.title||c.question)}">▶</button></div>`}
function renderBooks(){
 let h='<div class="page"><h1>资料</h1><input id="search" class="search" placeholder="搜索知识点、问题或正文" aria-label="搜索知识点">';
 if(app.search.trim()){
  const q=app.search.trim().toLocaleLowerCase(),found=cards.filter(c=>([...c.path,c.title,c.question,c.answer,c.notes].join(' ')).toLocaleLowerCase().includes(q));
  h+='<p class="small">'+found.length+' 组</p>'+found.map(knowledgeRow).join('');
 }else{
  for(const sub of SUBJECTS.concat(unique(cards.map(c=>c.path[0])).filter(x=>!SUBJECTS.includes(x)))){
   const list=cards.filter(c=>c.path[0]===sub);
   h+=branch('S:'+sub,sub,list,()=>unique(list.map(c=>c.path[1])).map(ch=>{
    const cl=list.filter(c=>c.path[1]===ch);
    return branch('C:'+sub+'|'+ch,ch,cl,()=>unique(cl.map(c=>c.path[2])).map(t=>{
     const tl=cl.filter(c=>c.path[2]===t);return branch('T:'+sub+'|'+ch+'|'+t,t,tl,()=>tl.map(knowledgeRow).join(''));
    }).join(''));
   }).join(''));
  }
  const wrongCards=cards.filter(c=>wrong.has(c.id)),weak=cards.filter(c=>['no','fuzzy'].includes(state(c).lastRating));
  h+=branch('wrong','错题',wrongCards,()=>'<div class="small">做题错题</div>'+(wrongCards.map(knowledgeRow).join('')||'<p class="small">暂无标记</p>')+'<div class="small">背诵薄弱</div>'+weak.map(knowledgeRow).join(''),true);
  if(!cards.some(c=>c.path[0]==='时政'))h+='<details class="branch"><summary><span class="name">时政</span><span class="count">待导入</span></summary><p class="small">等待你的时政资料。</p></details>';
 }
 $('main').innerHTML=h+'</div>';
 $('main').querySelectorAll('details[data-open]').forEach(d=>d.ontoggle=()=>{d.open?app.open.add(d.dataset.open):app.open.delete(d.dataset.open);persist()});
 $('main').querySelectorAll('[data-review]').forEach(b=>b.onclick=()=>setScope(cards,'全部知识组',b.dataset.review));
 $('main').querySelectorAll('[data-play]').forEach(b=>b.onclick=()=>playAudioCard(cards.find(c=>c.id===b.dataset.play)));
 $('main').querySelectorAll('[data-start]').forEach(b=>b.onclick=e=>{e.preventDefault();e.stopPropagation();const path=JSON.parse(b.dataset.start);playQueue(cards.filter(c=>path.every((v,i)=>c.path[i]===v)),'catalogue')});
 const input=$('search');input.value=app.search;input.oninput=()=>{const pos=input.selectionStart;app.search=input.value;renderBooks();$('search').focus();$('search').setSelectionRange(pos,pos)};
}
function branch(key,name,list,child,special=false){const z=summary(list),path=special?[]:key.startsWith('S:')?[name]:key.slice(2).split('|');return `<details class="branch" data-open="${esc(key)}" ${app.open.has(key)?'open':''}><summary><span class="name">${esc(name)}</span><span class="count">${special?list.length:z.mastered+'/'+list.length}</span>${!special&&list.length?`<button class="start" data-start="${esc(JSON.stringify(path))}" aria-label="播放${esc(name)}">▶</button>`:''}</summary>${child()}</details>`}
function renderStats(){const s=summary(cards),weak=cards.filter(c=>['no','fuzzy'].includes(state(c).lastRating)).length;$('main').innerHTML=`<div class="page"><h1>统计</h1><div class="stat-total">${s.mastered}<span class="small"> / ${s.total} 组</span></div><div class="small">已掌握完整知识组</div><div class="stat-grid"><div><b>${s.studied}</b><span class="small">已评分</span></div><div><b>${s.due}</b><span class="small">到期复习</span></div><div><b>${s.total-s.studied}</b><span class="small">未学习</span></div></div>${SUBJECTS.map(name=>{const z=summary(cards.filter(c=>c.path[0]===name));return `<div class="stat-row"><span>${name}</span><span>已背 ${z.studied}/${z.total} · 掌握 ${z.mastered}</span></div>`}).join('')}<p class="small">做题错题 ${wrong.size} 组 · 背诵薄弱 ${weak} 组</p><p class="small">在不同日期至少两次选择“记住”，且最近一次仍为“记住”，才计入掌握。只是揭晓、翻页不计分。评分按整组；只会其中一部分应选“模糊”。</p><p class="small">旧版93条短卡记录保持原样，不自动转换为新知识组已掌握。</p></div>`}
function modal(title,body){const d=$('dialog');d.innerHTML=`<button class="close" aria-label="关闭">×</button><h2>${esc(title)}</h2>${body}`;d.querySelector('.close').onclick=()=>d.close();if(!d.open)d.showModal()}
// One-time computer pairing, then one tap uploads directly. Credentials never enter backups.
const SYNC_KEY='politics_computer_sync_v1';let syncConfig=null,pairCode='',syncBusy=false,lastSyncedRevision=0;
function connectionFrom(code){
 const u=new URL(code.trim()),host=u.hostname,token=u.hash.slice(1),n=host.split('.').map(Number);
 const local=host==='localhost'||(n.length===4&&n.every(v=>Number.isInteger(v)&&v>=0&&v<=255)&&(n[0]===127||n[0]===10||(n[0]===192&&n[1]===168)||(n[0]===172&&n[1]>=16&&n[1]<=31)));
 if(!/^[0-9a-f]{64}$/.test(token)||u.username||u.password||u.search||(u.pathname&&u.pathname!=='/')||!(u.protocol==='https:'||(u.protocol==='http:'&&local)))throw Error('请粘贴电脑显示的完整连接码；HTTP只允许可信局域网地址');
 return {base:u.origin,token};
}
try{const saved=JSON.parse(localStorage.getItem(SYNC_KEY)||'null');if(saved){syncConfig=connectionFrom(saved.connection);pairCode=saved.pair||''}}catch(e){}
function saveConnection(config,pair=''){
 localStorage.setItem(SYNC_KEY,JSON.stringify({connection:config.base+'#'+config.token,pair}));syncConfig=config;pairCode=pair;lastSyncedRevision=0;
}
function newId(){return globalThis.crypto?.randomUUID?.()||Date.now()+'-'+Math.random().toString(16).slice(2)}
function progressSnapshot(){
 let device=localStorage.getItem('politics_sync_device');if(!device){device=newId();localStorage.setItem('politics_sync_device',device)}
 const list=Object.entries(reviews).map(([id,r])=>({card_id:id,score:r.score,review_count:r.reviewCount,last_rating:r.lastRating,last_yes_day:r.lastYesDay,due_at:r.dueAt,last_review_at:r.lastReviewAt,needs_review:!!r.needsReview,content_sig:r.contentSig||''}));
 for(const id of wrong)if(!wrongChanges[id])wrongChanges[id]={marked:true,at:1};
 return {kind:'politics-memory-progress',schema_version:1,request_id:newId(),device_id:device,sent_at:Date.now(),reviews:list,events,wrong_changes:wrongChanges,cursor:current()?{card_id:current().id,updated_at:app.positionAt||0}:{}};
}
function applyProgress(remote){
 if(remote.kind!=='politics-memory-progress'||remote.schema_version!==1||!Array.isArray(remote.reviews)||!Array.isArray(remote.events))throw Error('电脑返回的进度格式无效');
 for(const r of remote.reviews){const c=cards.find(c=>c.id===r.card_id);if(!c)continue;const old=reviews[r.card_id],at=Number(r.last_review_at)||0;
  if(!old||at>old.lastReviewAt||(at===old.lastReviewAt&&r.review_count>old.reviewCount))reviews[r.card_id]={score:Math.max(0,Math.min(4,r.score)),reviewCount:r.review_count,lastRating:r.last_rating,lastYesDay:r.last_yes_day||'',lastReviewAt:at,dueAt:r.due_at,needsReview:!!r.needs_review||!!old?.needsReview,contentSig:r.content_sig||sig(c)};
 }
 const known=new Set(events.map(e=>e.id));for(const e of remote.events)if(e.id&&!known.has(e.id)){events.push(e);known.add(e.id)}
 for(const [id,c] of Object.entries(remote.wrong_changes||{}))if(!wrongChanges[id]||c.at>wrongChanges[id].at){wrongChanges[id]=c;c.marked?wrong.add(id):wrong.delete(id)}
 if(remote.cursor?.updated_at>(app.positionAt||0)){
  const at=app.session.findIndex(c=>c.id===remote.cursor.card_id);
  if(at>=0){app.index=at;app.positionAt=remote.cursor.updated_at}
 }
 if(!persist())throw Error('电脑进度已收到，但浏览器无法持久保存');
 if(!moving)render();return remote.revision;
}
async function syncRequest(config,path,method='GET',body){
 const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),12000);
 try{
  const r=await fetch(config.base+path,{method,headers:{Authorization:'Bearer '+config.token,...(body?{'Content-Type':'application/json'}:{})},body,signal:ctrl.signal,cache:'no-store',redirect:'error'});
  if(r.status===401)throw Error('电脑连接码已失效，请长按同步重新连接');
  if(!r.ok)throw Error('电脑未确认保存（HTTP '+r.status+'）');
  return await r.json();
 }finally{clearTimeout(timer)}
}
async function pullProgress(){
 if(!syncConfig||syncBusy)return;
 try{const o=await syncRequest(syncConfig,'/api/progress');if(o.revision>lastSyncedRevision)lastSyncedRevision=applyProgress(o)}catch(e){/* No false success, and no recurring popups while the computer is offline. */}
}
async function fetchContentOnManualSync(config){
 const response=await syncRequest(config,'/api/content');
 if(response.kind!=='politics-memory-content-update')throw Error('更新包协议不匹配');
 if(response.status!=='available')return{added:0,updated:0,removed:0};
 const pack=response.pack,manifest=response.audio_index;
 if(!pack||pack.pack_id!=='politics-suyi-full'||pack.schema_version!==1||!Array.isArray(pack.cards)||pack.cards.length>20000)
  throw Error('知识包内容不合法');
 if(!manifest||manifest.pack_id!==pack.pack_id)throw Error('更新音频索引不匹配');
 if(pack.pack_revision<=contentRevision)return{added:0,updated:0,removed:0};
 const ids=new Set(),prior=new Map(cards.map(c=>[c.id,c]));
 for(const c of pack.cards){if(!validCard(c)||ids.has(c.id))throw Error('知识点ID重复或格式非法');ids.add(c.id)}
 const additions=pack.cards.filter(c=>!prior.has(c.id)).length;
 const modifications=pack.cards.filter(c=>prior.has(c.id)&&JSON.stringify(prior.get(c.id))!==JSON.stringify(c)).length;
 const removed=cards.filter(c=>!ids.has(c.id)).length;
 // Preserve all review history; changes to wording require a new recall.
 for(const c of pack.cards){const old=prior.get(c.id);if(old&&(old.question!==c.question||old.answer!==c.answer)&&reviews[c.id])reviews[c.id].needsReview=true}
 for(const [id,item] of Object.entries(manifest.items||{})){
  if(item.file!=='audio/'+id+'.mp3'||!ids.has(id)||!(/^[0-9a-f]{64}$/.test(item.text_sha256)))throw Error('新增录音索引无效');
  const c=pack.cards.find(x=>x.id===id);
  if(await sha256Hex(spokenText(c))!==item.text_sha256)throw Error('更新录音与正文不匹配');
 }
 // The server itself serves new audio from the selected Drive update ZIP.
 audioUpdates={...audioUpdates,...(manifest.items||{})};Object.assign(AUDIO_INDEX.items,audioUpdates);
 retired=new Set([...new Set([...PACK.cards.map(c=>c.id),...prior.keys()])].filter(id=>!ids.has(id)));
 const baseline=new Map(PACK.cards.map(c=>[c.id,c]));
 imports=pack.cards.filter(c=>!baseline.has(c.id)||JSON.stringify(baseline.get(c.id))!==JSON.stringify(c));
 cards=pack.cards.map(c=>({...c}));contentRevision=pack.pack_revision;
 const keep=current()?.id;app.session=cards.slice();app.index=Math.max(0,cards.findIndex(c=>c.id===keep));
 if(!persist())throw Error('资料已读取，但无法保存到浏览器');
 render();return{added:additions,updated:modifications,removed};
}
async function uploadToComputer(config=syncConfig){
 if(syncBusy)return;syncBusy=true;toast('正在同步到电脑…');
 try{
  const payload=progressSnapshot(),body=JSON.stringify(payload),hash=await sha256Hex(body);
  const ack=await syncRequest(config,'/api/progress','POST',body);
  if(!ack.ok||ack.request_id!==payload.request_id||ack.received_sha256!==hash)throw Error('电脑保存回执不匹配');
  if(config!==syncConfig)saveConnection(config);
  const latest=await syncRequest(config,'/api/progress');lastSyncedRevision=applyProgress(latest);
  const delta=await fetchContentOnManualSync(config);
  if($('dialog').open)$('dialog').close();toast('同步完成 · '+ack.review_count+'条记录 · 资料新增'+delta.added+' 更新'+delta.updated+' 停用'+delta.removed+'；云盘上传由 Google Drive 完成');
 }catch(e){toast('尚未同步：'+(e.name==='AbortError'?'电脑未响应':e.message)+'。请确认电脑接收器已开启、所选同步文件夹可读取；长按同步可重新连接。')}
 finally{syncBusy=false}
}
function connectComputer(){
 if(pairCode){
  modal('电脑同步已连接','<p class="small">电脑接收器已开启。请在接收器中选择 Google Drive 同步文件夹；手机在 APP 中关联同一文件夹的 progress.json 和 content-update.zip。两端各自点击同步，不要求同一 Wi-Fi。下方连接码只用于重新连接电脑接收器。</p><input id="pairCode" aria-label="电脑连接码" readonly><button class="menu-item" id="copyCode">复制电脑连接码</button>');
  $('pairCode').value=pairCode;$('copyCode').onclick=async()=>{try{await navigator.clipboard.writeText(pairCode)}catch(e){$('pairCode').select();document.execCommand('copy')}toast('电脑连接码已复制')};
 }else{
  modal('连接电脑','<p class="small">先在电脑运行 start-sync.cmd，并选择 Google Drive 同步文件夹。首次粘贴电脑接收器显示的连接码，以后只在点击同步时更新进度和资料。手机端请通过 Google Drive 选择对应文件。</p><input id="connection" aria-label="电脑连接码" placeholder="粘贴电脑连接码" autocomplete="off" spellcheck="false"><button class="menu-item" id="connect">连接并同步</button>');
  $('connection').value=syncConfig?syncConfig.base+'#'+syncConfig.token:'';
  $('connect').onclick=()=>{try{uploadToComputer(connectionFrom($('connection').value))}catch(e){toast(e.message)}};
 }
}
function syncData(){if(syncConfig)uploadToComputer();else connectComputer()}
function bootSync(){
 const params=new URLSearchParams(location.hash.slice(1));
 if(params.has('sync')){
  try{saveConnection(connectionFrom(params.get('sync')),params.get('pair')||'');history.replaceState(null,'',location.pathname+location.search);if(pairCode)connectComputer()}catch(e){toast(e.message)}
 }
 /* No automatic sync: only the visible Sync control performs requests. */
}

function sourceDetail(){const c=current();modal('本组来源',`<p>${esc(c.source||'导入资料')}</p><p class="small">${c.content_status==='VISUALLY_REORGANIZED'?'本组按苏一原图逐页阅读后重组。':'本组按既有结构化底稿和原有知识分支重组，未宣称逐字终审。'}</p>${c.source_notes?.length?'<h3>原图旁注留存（未逐字终审）</h3><p class="small warning">旁注用于对照来源，不作为已核实的老师技巧；未能准确定位的旁注按原页保留。</p>'+c.source_notes.map(n=>`<p class="source-note">${esc(n.text)}</p>`).join(''):''}<p class="small">编号：${esc(c.id)}</p>`)}
function about(){const audioCount=Object.keys(AUDIO_INDEX.items||{}).length;modal('苏一全科 v0.11',`<p>五科共 ${cards.length} 组，依据苏一正文印刷1—135页（PDF6—140页）整理。封面、目录、封底不作为背诵卡。</p><p>印刷76—135页按原图重新整理；印刷1—75页按既有结构化底稿分组，所有已标注结构节点均已纳入分组。全科覆盖不等于全书逐字终审。</p><p>当前离线录音索引：${audioCount}/${cards.length} 组。播放前会校验正文SHA-256；倍速支持0.75×—4×。</p><p>学习时离线保存；电脑接收器关联 Drive 同步文件夹后，只在点击同步时更新进度和资料。手机需关联同一文件夹的两份文件；云盘上传由 Google Drive 完成。</p><p class="small">原有短卡浏览器记录没有被清除；完整备份保留可读取的旧版记录。时政资料等待用户提供。</p>`)}
function setSpeed(n){if(!SPEEDS.includes(n))return;app.speed=n;audio.playbackRate=n;audio.defaultPlaybackRate=n;persist();updatePlayer()}
async function sha256Hex(value){const bytes=new TextEncoder().encode(value);if(!window.crypto?.subtle)return sha256Fallback(bytes);const digest=await crypto.subtle.digest('SHA-256',bytes);return [...new Uint8Array(digest)].map(x=>x.toString(16).padStart(2,'0')).join('')}
// SHA-256 also works on a trusted LAN http origin where SubtleCrypto is unavailable.
function sha256Fallback(bytes){
 const K=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
 const h=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19],len=bytes.length,data=new Uint8Array(Math.ceil((len+9)/64)*64);data.set(bytes);data[len]=128;
 const view=new DataView(data.buffer);view.setUint32(data.length-8,Math.floor(len/0x20000000));view.setUint32(data.length-4,(len*8)>>>0);
 const rotate=(x,n)=>(x>>>n)|(x<<(32-n)),w=new Uint32Array(64);
 for(let base=0;base<data.length;base+=64){
  for(let i=0;i<16;i++)w[i]=view.getUint32(base+4*i);
  for(let i=16;i<64;i++){const x=w[i-15],y=w[i-2];w[i]=(w[i-16]+(rotate(x,7)^rotate(x,18)^(x>>>3))+w[i-7]+(rotate(y,17)^rotate(y,19)^(y>>>10)))>>>0}
  let [a,b,c,d,e,f,g,z]=h;
  for(let i=0;i<64;i++){const t1=(z+(rotate(e,6)^rotate(e,11)^rotate(e,25))+((e&f)^(~e&g))+K[i]+w[i])>>>0,t2=((rotate(a,2)^rotate(a,13)^rotate(a,22))+((a&b)^(a&c)^(b&c)))>>>0;z=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0}
  [a,b,c,d,e,f,g,z].forEach((v,i)=>h[i]=(h[i]+v)>>>0);
 }
 return h.map(v=>v.toString(16).padStart(8,'0')).join('');
}

function spokenText(c){return (c.title||c.path[2]||'').trim()+'\n'+c.answer.trim()}
let playList=[],playAt=0,playSource='',playToken=0,playerSeeking=false;
async function loadTrack(paused=false){
 const token=++playToken,c=playList[playAt];if(!c)return;
 const entry=AUDIO_INDEX.items?.[c.id];
 try{
  if(!entry||entry.file!=='audio/'+c.id+'.mp3')throw Error('本组尚无匹配录音');
  if(await sha256Hex(spokenText(c))!==entry.text_sha256)throw Error('录音与知识组不匹配');
  if(token!==playToken)return;
  audio.pause();playingId=c.id;if(playSource==='review'){const at=app.session.findIndex(x=>x.id===c.id);if(at>=0&&app.index!==at){app.index=at;app.positionAt=Date.now();if(app.tab==='review'){renderReview();toolbar()}persist()}}audio.src=(window.POLITICS_AUDIO_BASE||'')+entry.file;audio.preload='metadata';audio.playbackRate=app.speed;
  if(!paused)await audio.play();else audio.load();updatePlayer();
 }catch(e){if(token===playToken){audio.pause();playingId='';playList=[];playSource='';toast(e.message);updatePlayer()}}
}
function playQueue(list,source='catalogue',paused=false){if(!list.length)return;playList=list.slice();playAt=0;playSource=source;return loadTrack(paused)}
function rotated(list,start){return list.slice(start).concat(list.slice(0,start))}
function playAudioCard(c){if(c)return playQueue(rotated(cards,Math.max(0,cards.findIndex(x=>x.id===c.id))))}
function playCurrentAudio(){return playQueue(rotated(app.session,app.index),'review')}
function toggleAudio(){if(playingId&&audio.getAttribute('src')){if(audio.paused)audio.play().catch(e=>toast(e.message));else audio.pause()}else playCurrentAudio();updatePlayer()}
function fmtTime(s){if(!Number.isFinite(s))return '0:00';return Math.floor(s/60)+':'+String(Math.floor(s%60)).padStart(2,'0')}
function updatePlayer(){
 const p=$('player');if(!p)return;
 p.hidden=!playingId&&app.tab!=='review';
 if(!$('playerToggle')){
  p.innerHTML='<div class="player-info"><span id="playerTitle"></span><span id="playerTime">0:00 / 0:00</span></div><div class="player-controls"><button id="playerToggle" aria-label="播放或暂停">▶</button><input id="seek" aria-label="播放进度" type="range" min="0" max="1000" value="0"><select id="playerSpeed" aria-label="播放速度">'+SPEEDS.map(v=>'<option value="'+v+'">'+v+'×</option>').join('')+'</select></div>';
  $('playerToggle').onclick=toggleAudio;$('playerSpeed').onchange=e=>setSpeed(Number(e.target.value));
  $('seek').oninput=()=>{playerSeeking=true;updateProgress()};
  $('seek').onchange=e=>{if(Number.isFinite(audio.duration)&&audio.duration>0)audio.currentTime=Number(e.target.value)*audio.duration/1000;playerSeeking=false;updateProgress()};
  $('seek').onblur=()=>{playerSeeking=false;updateProgress()};
 }
 const c=playingId?cards.find(c=>c.id===playingId):current();
 $('playerTitle').textContent=c?.title||c?.question||'';
 $('playerToggle').textContent=playingId&&!audio.paused?'Ⅱ':'▶';$('playerSpeed').value=String(app.speed);
 $('seek').disabled=!playingId||!Number.isFinite(audio.duration)||audio.duration<=0;updateProgress();
}
function updateProgress(){if(!$('seek'))return;const duration=playingId&&Number.isFinite(audio.duration)?audio.duration:0,position=playingId?audio.currentTime:0;if(!playerSeeking)$('seek').value=duration?Math.round(position/duration*1000):0;$('playerTime').textContent=fmtTime(playerSeeking?Number($('seek').value)*duration/1000:position)+' / '+fmtTime(duration)}
audio.ontimeupdate=updateProgress;audio.onplay=updatePlayer;audio.onpause=updatePlayer;audio.onloadedmetadata=updatePlayer;audio.onseeked=updateProgress;
audio.onerror=()=>{toast('录音加载失败');updatePlayer()};
audio.onended=()=>{if(playList.length){playAt=(playAt+1)%playList.length;loadTrack()}else updatePlayer()};
function download(name,text,type){const a=document.createElement('a'),url=URL.createObjectURL(new Blob([text],{type:type||'application/json;charset=utf-8'}));a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000)}
function exportBackup(){let legacy=null;try{legacy=JSON.parse(localStorage.getItem(LEGACY)||'null')}catch(e){}const list=Object.entries(reviews).map(([id,r])=>({card_id:id,score:r.score,review_count:r.reviewCount,last_rating:r.lastRating,last_yes_day:r.lastYesDay,due_at:r.dueAt,last_review_at:r.lastReviewAt,needs_review:!!r.needsReview,content_sig:r.contentSig}));download('政治背诵_成组备份_'+day(Date.now())+'.json',JSON.stringify({kind:'politics-memory-backup',schema_version:1,exported_at:Date.now(),packs:[{...PACK,cards}],reviews:list,events,wrong_ids:[...wrong],preferences:{goal:app.goal,speed:app.speed,show_answer:app.show},legacy_atomic_preview:legacy},null,2));toast('备份已导出')}
function exportCSV(){const q=x=>'"'+String(x??'').replaceAll('"','""')+'"';const rows=[['id','subject','chapter','topic','title','question','answer','notes','score','review_count','last_rating','last_review_at','due_at','needs_review','wrong_question']];for(const c of cards){const r=state(c);rows.push([c.id,...c.path,c.title,c.question,c.answer,c.notes,r.score,r.reviewCount,r.lastRating,r.lastReviewAt,r.dueAt,!!r.needsReview,wrong.has(c.id)])}download('政治背诵_成组进度.csv','\ufeff'+rows.map(r=>r.map(q).join(',')).join('\r\n'),'text/csv;charset=utf-8')}
$('import').onchange=async e=>{const f=e.target.files?.[0];if(!f)return;try{if(f.size>30000000)throw Error('JSON文件超过30MB');const o=JSON.parse(await f.text());let packs=o.kind==='politics-memory-backup'?o.packs:[o];packs=packs.filter(p=>p.pack_id!=='politics-sixiu-k');if(!Array.isArray(packs)||!packs.length||packs.some(p=>p.schema_version!==1||!Array.isArray(p.cards)||p.cards.some(c=>!validCard(c))))throw Error('素材格式不完整');if(!confirm('将素材合并到当前网页，保留较新的学习记录？'))return;const incoming=packs.flatMap(p=>p.cards);mergeCards(incoming);const imported=new Map(imports.map(c=>[c.id,c]));for(const c of incoming){const prev=imported.get(c.id);if(!prev||(c.revision||1)>=(prev.revision||1))imported.set(c.id,c)}imports=[...imported.values()];if(o.kind==='politics-memory-backup'){for(const r of o.reviews||[]){if(!r||typeof r.card_id!=='string')continue;const old=reviews[r.card_id];const at=Number(r.last_review_at)||0;if(!old||at>old.lastReviewAt){reviews[r.card_id]={score:Math.max(0,Math.min(4,Number(r.score)||0)),reviewCount:Math.max(0,Number(r.review_count)||0),lastRating:['no','fuzzy','yes'].includes(r.last_rating)?r.last_rating:'',lastYesDay:r.last_yes_day||'',lastReviewAt:at,dueAt:Number(r.due_at)||0,needsReview:!!r.needs_review,contentSig:r.content_sig||''}}}const known=new Set(events.map(x=>x.id));for(const x of o.events||[])if(x&&x.id&&!known.has(x.id)){events.push(x);known.add(x.id)}for(const id of o.wrong_ids||[])if(typeof id==='string')wrong.add(id);if(Object.prototype.hasOwnProperty.call(o,'legacy_atomic_preview')){try{if(o.legacy_atomic_preview===null)localStorage.removeItem(LEGACY);else localStorage.setItem(LEGACY,JSON.stringify(o.legacy_atomic_preview))}catch(e){toast('旧版记录已保留在备份文件中，但当前浏览器无法写入旧版记录')}}const pref=o.preferences||o.settings||{};const goal=pref.goal??pref.daily_goal;if(Number.isInteger(Number(goal))&&Number(goal)>=1&&Number(goal)<=500)app.goal=Number(goal);if(SPEEDS.includes(Number(pref.speed??pref.speech_speed)))app.speed=Number(pref.speed??pref.speech_speed);if(typeof pref.show_answer==='boolean')app.show=pref.show_answer;else if(pref.show_answer==='true'||pref.show_answer==='false')app.show=pref.show_answer==='true';audio.playbackRate=app.speed}for(const c of cards){const r=reviews[c.id];if(r&&r.contentSig&&r.contentSig!==sig(c))r.needsReview=true}const keep=current()?.id;app.session=cards.slice();app.index=Math.max(0,app.session.findIndex(c=>c.id===keep));persist();$('dialog').close();nav('books');toast('导入完成，较新的记录已保留')}catch(err){toast('导入失败：'+err.message)}finally{e.target.value=''}};
document.addEventListener('keydown',e=>{if(app.tab!=='review'||$('dialog').open||e.target.closest('input,select,textarea')||e.ctrlKey||e.metaKey||e.altKey)return;if(e.code==='Space'){e.preventDefault();toggle()}else if(e.key==='ArrowLeft'){e.preventDefault();step(-1)}else if(e.key==='ArrowRight'){e.preventDefault();step(1)}else if(['1','2','3'].includes(e.key)){e.preventDefault();rate({1:'no',2:'fuzzy',3:'yes'}[e.key])}});
$('dialog').addEventListener('click',e=>{if(e.target===$('dialog')){const r=$('dialog').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('dialog').close()}});
// Test hooks expose no network or user credentials. They exercise the same production paths.
window.PoliticsMemory={version:11,fetchContentOnManualSync,sha256Hex,sha256Fallback,spokenText,syncData,progressSnapshot,applyProgress,getCards:()=>cards,getState:()=>({app,reviews,events,wrong:[...wrong]}),start:id=>{const c=cards.find(x=>x.id===id);if(c)setScope(cards.filter(x=>x.path.every((p,i)=>p===c.path[i])),c.path[2],id)},rate,toggle,step,nav,exportBackup,playCurrentAudio,toggleAudio,setSpeed,playQueue,getPlayback:()=>({playingId,source:playSource,queue:playList.map(c=>c.id),at:playAt,time:audio.currentTime,duration:audio.duration,paused:audio.paused,speed:audio.playbackRate})};
render();bootSync();
})();
