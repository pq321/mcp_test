package org.vector.politicsmemory;

import android.content.Context;

import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Set;
import java.util.UUID;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/** Optional offline course pack: pack.json + audio-index.json + audio/<id>.mp3.
 *  The existing JSON import remains valid. MP3s are separately versioned by card text hash.
 */
final class AudioZipImporter {
    private AudioZipImporter(){}
    static StudyStore.ImportResult importPack(Context ctx,InputStream input,StudyStore store) throws Exception {
        File staging=new File(ctx.getCacheDir(),"pending-audio-"+UUID.randomUUID());
        if(!staging.mkdirs())throw new IOException("无法创建临时导入目录");
        try{
            int entries=0;long total=0;Set<String> names=new HashSet<>();
            try(ZipInputStream zin=new ZipInputStream(input)){
                ZipEntry ze;byte[] buffer=new byte[8192];
                while((ze=zin.getNextEntry())!=null){
                    String name=ze.getName();
                    if(ze.isDirectory()){zin.closeEntry();continue;}
                    if(++entries>20020)throw new IOException("ZIP文件数量过多");
                    if(!("pack.json".equals(name)||"audio-index.json".equals(name)||"update.json".equals(name)||name.matches("audio/[A-Za-z0-9._-]{1,128}\\.mp3")))
                        throw new IOException("文件路径不符合素材包规范: "+name);
                    if(!names.add(name))throw new IOException("ZIP重复文件: "+name);
                    File target=new File(staging,name);
                    File parent=target.getParentFile();if(!parent.exists()&&!parent.mkdirs())throw new IOException("无法建立目录");
                    try(FileOutputStream out=new FileOutputStream(target)){
                        int n;long thisFile=0;
                        while((n=zin.read(buffer))!=-1){
                            thisFile+=n;total+=n;
                            if(thisFile>16L*1024*1024||total>250L*1024*1024)throw new IOException("音频包超出大小限制");
                            out.write(buffer,0,n);
                        }
                    }
                    zin.closeEntry();
                }
            }
            File packFile=new File(staging,"pack.json");File indexFile=new File(staging,"audio-index.json");
            if(!packFile.isFile()||!indexFile.isFile())throw new IOException("缺少pack.json或audio-index.json");
            JSONObject pack;
            try(InputStream in=new FileInputStream(packFile)){pack=new JSONObject(StudyStore.readText(in,20*1024*1024));}
            JSONObject manifest;
            try(InputStream in=new FileInputStream(indexFile)){manifest=new JSONObject(StudyStore.readText(in,5*1024*1024));}
            if(manifest.optInt("schema_version")!=1||!manifest.getString("pack_id").equals(pack.getString("pack_id")))
                throw new IOException("音频索引版本或素材包ID不匹配");
            JSONObject items=manifest.getJSONObject("items");
            JSONObject hashes=new JSONObject();
            org.json.JSONArray cards=pack.getJSONArray("cards");
            for(int j=0;j<cards.length();j++){
                JSONObject c=cards.getJSONObject(j);
                org.json.JSONArray path=c.getJSONArray("path");
                StudyCard card=new StudyCard();
                card.id=c.getString("id");
                card.subject=path.getString(0);card.chapter=path.getString(1);card.topic=path.getString(2);
                card.title=c.optString("title",card.topic).trim();
                card.question=c.getString("question");card.answer=c.getString("answer");
                card.notes=c.optString("notes","");
                // Must match the generator and AudioCatalog: path + title + question + answer + notes.
                hashes.put(card.id,AudioCatalog.contentHash(card));
            }
            Iterator<String> keys=items.keys();
            while(keys.hasNext()){
                String id=keys.next();
                if(!id.matches("[A-Za-z0-9._-]{1,128}")||!hashes.has(id))throw new IOException("音频ID不存在或无效: "+id);
                JSONObject item=items.getJSONObject(id);
                String name=item.getString("file");
                if(!name.equals("audio/"+id+".mp3"))throw new IOException("音频路径不符合规范: "+id);
                if(!item.getString("text_sha256").equals(hashes.getString(id)))throw new IOException("音频与题目答案不匹配: "+id);
                File file=new File(staging,name);
                if(!file.isFile()||file.length()<500)throw new IOException("音频文件缺失: "+id);
                String actual=digestFile(file);
                if(!actual.equals(item.getString("audio_sha256")))throw new IOException("音频哈希校验失败: "+id);
            }
            // Database transaction comes first; it never deletes old ratings. Audio is published atomically per file.
            StudyStore.ImportResult result=store.importPayload(pack);
            File dir=new File(ctx.getFilesDir(),"audio");if(!dir.exists()&&!dir.mkdirs())throw new IOException("无法建立本地音频目录");
            keys=items.keys();
            while(keys.hasNext()){
                String id=keys.next();
                File src=new File(staging,"audio/"+id+".mp3");
                File target=new File(dir,id+".mp3");
                File temp=new File(dir,id+".mp3.new");copy(src,temp);
                if(!temp.renameTo(target)){if(target.exists()&&!target.delete())throw new IOException("无法替换旧音频: "+id);
                    if(!temp.renameTo(target))throw new IOException("无法保存音频: "+id);}
            }
            File global=new File(ctx.getFilesDir(),"audio-index.json");
            JSONObject all=new JSONObject();JSONObject allItems=new JSONObject();
            if(global.isFile())try(InputStream in=new FileInputStream(global)){
                all=new JSONObject(StudyStore.readText(in,5*1024*1024));
                JSONObject old=all.optJSONObject("items");if(old!=null){Iterator<String> it=old.keys();while(it.hasNext()){String id=it.next();allItems.put(id,old.getJSONObject(id));}}
            }
            keys=items.keys();while(keys.hasNext()){String id=keys.next();allItems.put(id,items.getJSONObject(id));}
            all.put("schema_version",1);all.put("items",allItems);
            File temp=new File(ctx.getFilesDir(),"audio-index.json.new");
            try(FileOutputStream out=new FileOutputStream(temp)){out.write(all.toString().getBytes(StandardCharsets.UTF_8));out.getFD().sync();}
            if(!temp.renameTo(global)){if(global.exists()&&!global.delete())throw new IOException("无法替换音频索引");
                if(!temp.renameTo(global))throw new IOException("无法更新音频索引");}
            return result;
        }finally{deleteTree(staging);}
    }
    private static void copy(File from,File to)throws IOException{
        try(InputStream in=new FileInputStream(from);FileOutputStream out=new FileOutputStream(to)){
            byte[] b=new byte[8192];int n;while((n=in.read(b))!=-1)out.write(b,0,n);out.getFD().sync();
        }
    }
    static String digestFileForSync(File f)throws Exception{return digestFile(f);}
    private static String digestFile(File f)throws Exception{
        MessageDigest md=MessageDigest.getInstance("SHA-256");
        try(InputStream in=new FileInputStream(f)){byte[] b=new byte[8192];int n;while((n=in.read(b))!=-1)md.update(b,0,n);}
        StringBuilder sb=new StringBuilder();for(byte v:md.digest())sb.append(String.format(java.util.Locale.US,"%02x",v&255));return sb.toString();
    }
    private static void deleteTree(File f){if(f.isDirectory()){File[] children=f.listFiles();if(children!=null)for(File c:children)deleteTree(c);}if(f.exists())f.delete();}
}