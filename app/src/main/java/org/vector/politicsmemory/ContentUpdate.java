package org.vector.politicsmemory;

import android.content.Context;
import org.json.JSONObject;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/** Codex-published update ZIP: update.json + optional authoritative pack.json,
 *  audio-index.json and only the changed MP3 files. Cards absent from a higher
 *  pack revision are hidden, not deleted; rating history is preserved.
 */
final class ContentUpdate {
    static final class Result {
        boolean changed,resourcesChanged;
        int added,updated,removed;
    }
    static Result apply(Context context,File file,StudyStore store)throws Exception{
        if(ResourceImporter.isResource(file))return ResourceImporter.apply(context,file,store);
        Result out=new Result();boolean pack=false,meta=false,index=false;
        String updateText=null;
        Set<String> seen=new HashSet<>();
        try(ZipInputStream in=new ZipInputStream(new FileInputStream(file))){
            ZipEntry entry;long size=0;
            byte[] buffer=new byte[8192];
            while((entry=in.getNextEntry())!=null){
                String name=entry.getName();
                if(entry.isDirectory()){in.closeEntry();continue;}
                if(!seen.add(name))throw new IOException("更新包重复文件");
                if(!(name.equals("update.json")||name.equals("pack.json")||name.equals("audio-index.json")||name.matches("audio/[A-Za-z0-9._-]{1,128}\\.mp3")))
                    throw new IOException("更新包含不允许的文件路径");
                if(name.equals("pack.json"))pack=true;
                if(name.equals("audio-index.json"))index=true;
                if(name.equals("update.json")){
                    java.io.ByteArrayOutputStream b=new java.io.ByteArrayOutputStream();int n;
                    while((n=in.read(buffer))!=-1){size+=n;if(b.size()+n>65536)throw new IOException("更新描述过长");b.write(buffer,0,n);}
                    updateText=b.toString(StandardCharsets.UTF_8.name());meta=true;
                }else{
                    int n;while((n=in.read(buffer))!=-1){size+=n;if(size>250L*1024*1024)throw new IOException("更新包过大");}
                }
                in.closeEntry();
            }
        }
        if(!meta)throw new IOException("缺少 update.json");
        JSONObject descriptor=new JSONObject(updateText);
        if(!"politics-memory-content-update".equals(descriptor.optString("kind"))||descriptor.optInt("schema_version")!=1)
            throw new IOException("更新包协议不匹配");
        if(!"politics-suyi-full".equals(descriptor.optString("pack_id")))
            throw new IOException("更新包不是本项目资料");
        if(!pack){
            if(index||!seen.equals(java.util.Collections.singleton("update.json")))throw new IOException("更新包缺少资料文件");
            if(descriptor.optJSONArray("upserts")==null||descriptor.getJSONArray("upserts").length()!=0||descriptor.optJSONArray("deleted_ids")==null||descriptor.getJSONArray("deleted_ids").length()!=0)
                throw new IOException("没有 pack.json 但声明了资料变更");
            return out;
        }
        if(!index)throw new IOException("资料更新包缺少音频校验表");
        try(FileInputStream in=new FileInputStream(file)){
            StudyStore.ImportResult changed=AudioZipImporter.importPack(context,in,store);
            out.changed=changed.added>0||changed.updated>0||changed.removed>0;
            out.added=changed.added;out.updated=changed.updated;out.removed=changed.removed;
        }
        return out;
    }
}
