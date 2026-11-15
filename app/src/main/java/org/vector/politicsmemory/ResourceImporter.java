package org.vector.politicsmemory;

import android.content.Context;
import android.database.sqlite.SQLiteDatabase;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/** Optional resource bundle on the existing manual sync channel. No background network. */
final class ResourceImporter {
    static final long LIMIT=1024L*1024*1024;
    static boolean isResource(File file)throws Exception{
        try(ZipFile zip=new ZipFile(file)){
            ZipEntry e=zip.getEntry("update.json");
            if(e==null)return false;
            JSONObject d=read(zip,e,65536);
            return d.optBoolean("resource_update");
        }
    }
    private static JSONObject read(ZipFile z,ZipEntry e,int max)throws Exception{
        try(InputStream in=z.getInputStream(e)){return new JSONObject(StudyStore.readText(in,max));}
    }
    static ContentUpdate.Result apply(Context context,File file,StudyStore store)throws Exception{
        ContentUpdate.Result result=new ContentUpdate.Result();
        try(ZipFile zip=new ZipFile(file)){
            JSONObject descriptor=read(zip,zip.getEntry("update.json"),65536);
            if(!"politics-memory-content-update".equals(descriptor.optString("kind"))||descriptor.optInt("schema_version")!=1)
                throw new java.io.IOException("学习资源包协议不匹配");
            Set<String> names=new HashSet<>();long size=0;ArrayList<JSONObject> packs=new ArrayList<>();
            for(java.util.Enumeration<? extends ZipEntry> it=zip.entries();it.hasMoreElements();){
                ZipEntry e=it.nextElement();if(e.isDirectory())continue;String name=e.getName();
                if(!names.add(name)||names.size()>40000)throw new java.io.IOException("资源包文件重复或数量过多");
                if(!(name.equals("update.json")||name.equals("study-resources.json")||name.matches("packs/[A-Za-z0-9._-]{1,80}\\.json")||name.matches("audio/[A-Za-z0-9._-]{1,128}/[0-9]+/[A-Za-z0-9._-]{1,128}\\.mp3")))
                    throw new java.io.IOException("资源包路径不合法："+name);
                size+=e.getSize();if(e.getSize()<0||size>LIMIT||e.getSize()>20L*1024*1024)throw new java.io.IOException("资源包大小超出限制");
                if(name.startsWith("packs/")){
                    JSONObject pack=read(zip,e,20*1024*1024);StudyStore.validateOnly(pack);
                    if(!name.equals("packs/"+pack.getString("pack_id")+".json"))throw new java.io.IOException("资料包路径与ID不一致");
                    packs.add(pack);
                }
            }
            ZipEntry metadata=zip.getEntry("study-resources.json");if(metadata==null)throw new java.io.IOException("缺少学习资源索引");
            JSONObject patch=read(zip,metadata,20*1024*1024);if(patch.optInt("schema_version")!=1)throw new java.io.IOException("学习资源索引版本不兼容");
            Map<String,StudyCard> cards=new HashMap<>();for(StudyCard c:store.allCards())cards.put(c.id,c);
            for(JSONObject pack:packs){JSONArray cs=pack.getJSONArray("cards");for(int n=0;n<cs.length();n++){
                JSONObject c=cs.getJSONObject(n);StudyCard existing=cards.get(c.getString("id"));
                if(existing!=null&&!pack.getString("pack_id").equals(existing.packId))throw new java.io.IOException("不同资料来源的知识点ID冲突");
                StudyCard card=new StudyCard();card.id=c.getString("id");card.packId=pack.getString("pack_id");card.title=c.optString("title",c.getJSONArray("path").getString(2));card.topic=c.getJSONArray("path").getString(2);card.answer=c.getString("answer").trim();cards.put(card.id,card);
            }}
            JSONObject voices=patch.optJSONObject("voices");Set<String> referenced=new HashSet<>();
            if(voices!=null)for(Iterator<String> it=voices.keys();it.hasNext();){
                String id=it.next();JSONObject voice=voices.getJSONObject(id);int rev=voice.optInt("revision",0);
                if((id.equals(".")||id.equals(".."))||!id.matches("[A-Za-z0-9._-]{1,128}")||rev<1||voice.optString("name").trim().isEmpty()||("default".equals(id)&&voice.optBoolean("retired")))throw new java.io.IOException("声音信息不合法");
                JSONObject items=voice.optJSONObject("items");if(items==null)continue;
                for(Iterator<String> keys=items.keys();keys.hasNext();){String cid=keys.next();JSONObject audio=items.getJSONObject(cid);String name=audio.getString("file");
                    if(!cid.matches("[A-Za-z0-9._-]{1,128}")||!name.equals("audio/"+id+"/"+rev+"/"+cid+".mp3"))throw new java.io.IOException("声音文件路径与版本不一致");
                    StudyCard c=cards.get(cid);if(c!=null&&!AudioCatalog.contentHash(c).equals(audio.optString("text_sha256")))throw new java.io.IOException("声音与正文不匹配："+cid);
                    if(!audio.optString("audio_sha256").matches("[a-f0-9]{64}"))throw new java.io.IOException("缺少声音文件校验值");
                    referenced.add(name);File target=new File(context.getFilesDir(),name);ZipEntry e=zip.getEntry(name);
                    if(e==null){if(!target.isFile()||!AudioZipImporter.digestFileForSync(target).equals(audio.getString("audio_sha256")))throw new java.io.IOException("缺少声音文件："+cid);continue;}
                    if(e.getSize()<500||e.getSize()>16L*1024*1024)throw new java.io.IOException("声音文件大小不合法");
                    File parent=target.getParentFile();if(!parent.isDirectory()&&!parent.mkdirs())throw new java.io.IOException("无法建立声音目录");
                    File temp=new File(parent,cid+".pending");MessageDigest digest=MessageDigest.getInstance("SHA-256");
                    try(InputStream in=zip.getInputStream(e);FileOutputStream out=new FileOutputStream(temp)){
                        byte[] b=new byte[8192];int n;long total=0;while((n=in.read(b))!=-1){total+=n;if(total>16L*1024*1024)throw new java.io.IOException("声音文件过大");digest.update(b,0,n);out.write(b,0,n);}out.getFD().sync();
                    }
                    StringBuilder hash=new StringBuilder();for(byte b:digest.digest())hash.append(String.format(java.util.Locale.US,"%02x",b&255));
                    if(!hash.toString().equals(audio.getString("audio_sha256"))){temp.delete();throw new java.io.IOException("声音校验失败："+cid);}
                    if(target.exists()){
                        if(!AudioZipImporter.digestFileForSync(target).equals(hash.toString())){temp.delete();throw new java.io.IOException("声音内容更改必须增加声音版本号");}temp.delete();
                    }else if(!temp.renameTo(target))throw new java.io.IOException("无法保存声音文件");
                }
            }
            for(String name:names)if(name.startsWith("audio/")&&!referenced.contains(name))throw new java.io.IOException("声音文件没有对应索引");
            JSONObject annotations=patch.optJSONObject("annotations");
            if(annotations!=null)for(Iterator<String> it=annotations.keys();it.hasNext();){String id=it.next();JSONObject a=annotations.getJSONObject(id);StudyCard c=cards.get(id);
                if(a.optInt("revision",0)<1||!a.optString("answer_sha256").matches("[a-f0-9]{64}"))throw new java.io.IOException("标注版本或正文校验值不合法");
                if(c==null)continue;
                if(!AudioCatalog.digest(c.answer.getBytes(StandardCharsets.UTF_8)).equals(a.getString("answer_sha256")))throw new java.io.IOException("挖空标记与正文不匹配："+id);
                JSONArray marks=a.getJSONArray("marks");int last=0;for(int n=0;n<marks.length();n++){
                    JSONObject m=marks.getJSONObject(n);int start=m.getInt("start"),end=m.getInt("end");String kind=m.getString("kind");
                    if(start<last||end<=start||end>c.answer.length()||!c.answer.substring(start,end).equals(m.getString("text"))||!(kind.equals("core")||kind.equals("confusion")||kind.equals("condition")))throw new java.io.IOException("挖空位置不合法："+id);last=end;
                }
            }
            JSONObject sources=patch.optJSONObject("sources");if(sources!=null)for(Iterator<String> it=sources.keys();it.hasNext();){String id=it.next();JSONObject source=sources.getJSONObject(id);if((id.equals(".")||id.equals(".."))||!id.matches("[A-Za-z0-9._-]{1,80}")||source.optInt("revision",0)<1||source.optString("name").trim().isEmpty())throw new java.io.IOException("资料来源信息不合法");}
            JSONObject old=new JSONObject(store.setting(StudyResources.SETTING,"{}"));JSONObject next=StudyResources.merge(old,patch);
            SQLiteDatabase db=store.getWritableDatabase();db.beginTransaction();
            try{
                for(JSONObject pack:packs){StudyStore.ImportResult change=store.importPayload(pack);result.added+=change.added;result.updated+=change.updated;result.removed+=change.removed;}
                store.saveSetting(StudyResources.SETTING,next.toString());db.setTransactionSuccessful();
            }finally{db.endTransaction();}
            result.resourcesChanged=!old.toString().equals(next.toString());result.changed=result.resourcesChanged||result.added+result.updated+result.removed>0;
            return result;
        }
    }
}
