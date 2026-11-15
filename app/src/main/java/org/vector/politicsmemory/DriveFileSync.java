package org.vector.politicsmemory;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * Manual-only user-selected cloud document synchronization. No OAuth credentials,
 * cloud API key, background worker or automatic network requests exist here.
 *
 * Files are selected through Android's Storage Access Framework. With the Google
 * Drive DocumentsProvider installed, its persisted content URI can refer to a
 * private Drive document. Provider uploads are eventual: local write verification
 * is NOT proof that the server-side Google Drive upload has completed.
 */
final class DriveFileSync {
    static final int PICK_PROGRESS=81, PICK_CONTENT=82;
    private static final String PREF="politics_drive_documents";
    private static final String PROGRESS="progress_uri", CONTENT="content_uri";
    private DriveFileSync(){}

    static boolean hasProgress(Context ctx){return !prefs(ctx).getString(PROGRESS,"").isEmpty();}
    static boolean hasContent(Context ctx){return !prefs(ctx).getString(CONTENT,"").isEmpty();}
    static void clear(Context ctx){prefs(ctx).edit().remove(PROGRESS).remove(CONTENT).apply();}
    private static SharedPreferences prefs(Context ctx){return ctx.getSharedPreferences(PREF,Context.MODE_PRIVATE);}
    static Intent picker(boolean progress){
        Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType(progress?"application/json":"*/*");
        if(!progress)i.putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"application/zip","application/octet-stream","application/x-zip-compressed"});
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        if(progress)i.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        return i;
    }
    static void remember(Context ctx,boolean progress,Intent picked)throws IOException{
        if(picked==null||picked.getData()==null)throw new IOException("没有选择文件");
        Uri uri=picked.getData();
        int mode=picked.getFlags()&(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        if((mode&Intent.FLAG_GRANT_READ_URI_PERMISSION)==0)throw new IOException("文件没有读取权限");
        if(progress&&(mode&Intent.FLAG_GRANT_WRITE_URI_PERMISSION)==0)throw new IOException("进度文件没有写入权限，请选择 Drive 中可编辑的 progress.json");
        ctx.getContentResolver().takePersistableUriPermission(uri,mode);
        // Save only a provider-owned URI. Access is still mediated by Android's grant.
        if(!prefs(ctx).edit().putString(progress?PROGRESS:CONTENT,uri.toString()).commit())
            throw new IOException("保存文件选择失败");
    }
    static final class Result {
        int reviews=0,added=0,updated=0,removed=0;
        boolean contentChanged=false,resourcesChanged=false;
        String message(){return "本机进度文件已更新 · "+reviews+"条；资料"+(contentChanged?"新增"+added+"，更新"+updated+"，停用"+removed:"无变化")+(resourcesChanged?"；声音/标注已更新":"")+"。云盘实际上传由 Google Drive 完成。";}
    }
    static Result sync(Context ctx, StudyStore store) throws Exception {
        final String progressValue=prefs(ctx).getString(PROGRESS,"");
        final String contentValue=prefs(ctx).getString(CONTENT,"");
        if(progressValue.isEmpty()||contentValue.isEmpty())throw new IOException("首次需要选择进度文件和知识包");
        final Uri progress=Uri.parse(progressValue),content=Uri.parse(contentValue);
        // The provider may be offline. Read failure cannot be treated as an empty cloud file.
        JSONObject remote;
        try(InputStream in=ctx.getContentResolver().openInputStream(progress)){
            if(in==null)throw new IOException("无法读取 Drive 进度文件");
            remote=new JSONObject(StudyStore.readText(in,8*1024*1024));
        }
        String device=prefs(ctx).getString("device_id","");
        if(device.isEmpty()){
            device=UUID.randomUUID().toString();
            if(!prefs(ctx).edit().putString("device_id",device).commit())throw new IOException("无法保存设备ID");
        }
        JSONObject local=store.progress(device);
        JSONObject merged=merge(remote,local);
        byte[] bytes=(merged.toString()+"\n").getBytes(StandardCharsets.UTF_8);
        // Save exact cloud state before attempting write; no implicit destructive reset.
        File backup=new File(ctx.getFilesDir(),"drive-progress-before-sync.json");
        try(FileOutputStream out=new FileOutputStream(backup)){
            out.write(remote.toString().getBytes(StandardCharsets.UTF_8));out.getFD().sync();
        }
        try(ParcelFileDescriptor fd=ctx.getContentResolver().openFileDescriptor(progress,"rwt")){
            if(fd==null)throw new IOException("进度文件不支持写入");
            try(FileOutputStream out=new FileOutputStream(fd.getFileDescriptor())){
                out.write(bytes);out.flush();
            }
        }
        // Confirm the document provider's current bytes, not remote cloud durability.
        byte[] saved;
        try(InputStream in=ctx.getContentResolver().openInputStream(progress)){
            if(in==null)throw new IOException("无法回读进度文件，未确认写入");
            saved=readLimited(in,8*1024*1024);
        }
        if(!AudioCatalog.digest(bytes).equals(AudioCatalog.digest(saved)))
            throw new IOException("进度文件回读不一致，未确认保存；手机原有记录保持不变");
        store.mergeRemoteProgress(merged);
        Result result=new Result();result.reviews=merged.getJSONArray("reviews").length();

        // Download the chosen update file into private staging, only when user taps Sync.
        File staged=new File(ctx.getCacheDir(),"drive-content-staged.zip");
        try(InputStream in=ctx.getContentResolver().openInputStream(content)){
            if(in==null)throw new IOException("无法读取 Drive 资料更新文件");
            try(FileOutputStream out=new FileOutputStream(staged)){
                byte[] buffer=new byte[8192];int n;long size=0;
                while((n=in.read(buffer))!=-1){size+=n;if(size>ResourceImporter.LIMIT)throw new IOException("更新包超过1GB限制");out.write(buffer,0,n);}
                out.getFD().sync();
            }
        }
        try {
            String sha=AudioZipImporter.digestFileForSync(staged);
            if(!sha.equals(store.setting("drive_content_sha",""))){
                ContentUpdate.Result change=ContentUpdate.apply(ctx,staged,store);
                result.contentChanged=change.changed;result.resourcesChanged=change.resourcesChanged;
                result.added=change.added;result.updated=change.updated;result.removed=change.removed;
                store.saveSetting("drive_content_sha",sha);
            }
        }finally{staged.delete();}
        return result;
    }
    private static byte[] readLimited(InputStream in,int max)throws IOException {
        java.io.ByteArrayOutputStream out=new java.io.ByteArrayOutputStream();byte[] b=new byte[8192];int n;
        while((n=in.read(b))!=-1){if(out.size()+n>max)throw new IOException("数据过大");out.write(b,0,n);}return out.toByteArray();
    }
    /** Union immutable events; newer per-card reviews and per-card wrong flags win. */
    static JSONObject merge(JSONObject old,JSONObject fresh)throws JSONException {
        if(!"politics-memory-progress".equals(old.optString("kind"))||old.optInt("schema_version")!=1)
            throw new JSONException("云盘进度文件格式不兼容，未修改云端文件");
        if(!"politics-memory-progress".equals(fresh.optString("kind")))throw new JSONException("本地进度格式不兼容");
        JSONObject out=new JSONObject();out.put("kind","politics-memory-progress");out.put("schema_version",1);
        out.put("request_id",fresh.optString("request_id",UUID.randomUUID().toString()));
        out.put("device_id",fresh.optString("device_id"));out.put("sent_at",fresh.optLong("sent_at"));
        out.put("revision",Math.max(0,old.optInt("revision",0))+1);
        Map<String,JSONObject> reviews=new HashMap<>();
        for(JSONObject src:new JSONObject[]{old,fresh}){
            JSONArray rs=src.optJSONArray("reviews");if(rs==null)continue;
            if(rs.length()>10000)throw new JSONException("进度条目数量异常");
            for(int i=0;i<rs.length();i++){
                JSONObject row=rs.getJSONObject(i);String id=row.getString("card_id");checkId(id);
                JSONObject before=reviews.get(id);
                if(before==null||row.optLong("last_review_at")>before.optLong("last_review_at")
                    ||(row.optLong("last_review_at")==before.optLong("last_review_at")&&row.optInt("review_count")>before.optInt("review_count")))reviews.put(id,row);
            }
        }
        JSONArray rarr=new JSONArray();for(String id:new java.util.TreeSet<>(reviews.keySet()))rarr.put(reviews.get(id));out.put("reviews",rarr);
        Map<String,JSONObject> events=new HashMap<>();
        for(JSONObject src:new JSONObject[]{old,fresh}){
            JSONArray es=src.optJSONArray("events");if(es==null)continue;
            if(es.length()>100000)throw new JSONException("事件数量异常");
            for(int i=0;i<es.length();i++){
                JSONObject event=es.getJSONObject(i);String id=event.getString("id");checkId(id);
                if(events.containsKey(id)&&!sameEvent(events.get(id),event))throw new JSONException("事件ID冲突："+id);
                events.put(id,event);
            }
        }
        JSONArray earr=new JSONArray();for(String id:new java.util.TreeSet<>(events.keySet()))earr.put(events.get(id));out.put("events",earr);
        JSONObject flags=new JSONObject();
        for(JSONObject src:new JSONObject[]{old,fresh}){
            JSONObject changes=src.optJSONObject("wrong_changes");if(changes==null)continue;
            for(Iterator<String> it=changes.keys();it.hasNext();){
                String id=it.next();checkId(id);JSONObject mark=changes.getJSONObject(id);
                if(!flags.has(id)||mark.optLong("at")>flags.getJSONObject(id).optLong("at"))flags.put(id,mark);
            }
        }
        out.put("wrong_changes",flags);
        JSONArray wrong=new JSONArray();for(Iterator<String> it=flags.keys();it.hasNext();){String id=it.next();if(flags.getJSONObject(id).optBoolean("marked"))wrong.put(id);}out.put("wrong_ids",wrong);
        JSONObject cursor=new JSONObject();
        for(JSONObject src:new JSONObject[]{old,fresh}){
            JSONObject v=src.optJSONObject("cursor");
            if(v!=null&&v.optLong("updated_at")>cursor.optLong("updated_at"))cursor=v;
        }
        out.put("cursor",cursor);
        return out;
    }
    private static boolean sameEvent(JSONObject a,JSONObject b){
        return a.optString("id").equals(b.optString("id"))
            && a.optString("card_id").equals(b.optString("card_id"))
            && a.optString("rating").equals(b.optString("rating"))
            && a.optInt("score_before")==b.optInt("score_before")
            && a.optInt("score_after")==b.optInt("score_after")
            && a.optLong("at")==b.optLong("at");
    }
    private static void checkId(String id)throws JSONException{
        if(id==null||!id.matches("[A-Za-z0-9._-]{1,128}"))throw new JSONException("记录ID非法");
    }
}
