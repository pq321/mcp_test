package org.vector.politicsmemory;

import android.content.Context;
import android.content.res.AssetFileDescriptor;
import android.media.MediaPlayer;
import android.util.Log;

import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HashMap;
import java.util.Map;

/** Resolves prerecorded MP3 by stable card ID AND exact question/answer checksum.
 *  Mismatched or missing audio is never silently played against changed content.
 */
final class AudioCatalog {
    private static final String TAG="PoliticsAudio";
    private final Context ctx;
    private final StudyResources resources;
    private final String selectedVoice;
    private final Map<String,Entry> builtin=new HashMap<>();
    private final Map<String,Entry> imported=new HashMap<>();
    private static final class Entry {String file, textHash;Entry(String f,String h){file=f;textHash=h;}}
    AudioCatalog(Context context){
        ctx=context.getApplicationContext();
        StudyStore store=new StudyStore(ctx);try{resources=new StudyResources(ctx,store);selectedVoice=store.setting("speech_voice","default");}finally{store.close();}
        try(InputStream in=ctx.getAssets().open("audio-index.json")){load(in,builtin);}
        catch(Exception e){Log.w(TAG,"No bundled audio index",e);}
        File file=new File(ctx.getFilesDir(),"audio-index.json");
        if(file.isFile())try(InputStream in=new FileInputStream(file)){load(in,imported);}
        catch(Exception e){Log.w(TAG,"Cannot read imported audio index",e);}
    }
    static String spokenText(StudyCard c){
        String title=c.title==null||c.title.trim().isEmpty()?c.topic:c.title.trim();
        return title+"\n"+c.answer.trim();
    }
    static String contentHash(StudyCard c){return digest(spokenText(c).getBytes(StandardCharsets.UTF_8));}
    static String digest(byte[] value){
        try{byte[] h=MessageDigest.getInstance("SHA-256").digest(value);
            StringBuilder sb=new StringBuilder(64);for(byte b:h)sb.append(String.format(java.util.Locale.US,"%02x",b&255));
            return sb.toString();
        }catch(Exception e){throw new IllegalStateException(e);}
    }
    private static void load(InputStream in,Map<String,Entry> into)throws Exception{
        JSONObject root=new JSONObject(StudyStore.readText(in,5*1024*1024));
        JSONObject items=root.getJSONObject("items");
        java.util.Iterator<String> keys=items.keys();
        while(keys.hasNext()){
            String id=keys.next();JSONObject entry=items.getJSONObject(id);
            if(!id.matches("[A-Za-z0-9._-]{1,128}"))continue;
            String file=entry.getString("file"),hash=entry.getString("text_sha256");
            if(file.equals("audio/"+id+".mp3") && hash.matches("[0-9a-f]{64}"))into.put(id,new Entry(file,hash));
        }
    }
    private Entry voiceEntry(String id,StudyCard c){
        JSONObject v=resources.audio(id,c.id);if(v==null)return null;
        String path=v.optString("file"),hash=v.optString("text_sha256");
        if(!path.matches("audio/[A-Za-z0-9._-]{1,128}/[0-9]+/[A-Za-z0-9._-]{1,128}\\.mp3"))return null;
        return hash.equals(contentHash(c))&&new File(ctx.getFilesDir(),path).isFile()?new Entry(path,hash):null;
    }
    private Entry selectedEntry(StudyCard c){Entry e=voiceEntry(selectedVoice,c);return e!=null?e:voiceEntry("default",c);}
    boolean ready(StudyCard c){
        if(selectedEntry(c)!=null)return true;
        String hash=contentHash(c);
        Entry entry=imported.get(c.id);
        if(entry!=null&&entry.textHash.equals(hash)&&new File(ctx.getFilesDir(),entry.file).isFile())return true;
        entry=builtin.get(c.id);
        return entry!=null&&entry.textHash.equals(hash);
    }
    /** Sets MP3 file descriptor before MediaPlayer.prepareAsync(). */
    boolean attach(MediaPlayer player,StudyCard c){
        Entry custom=selectedEntry(c);
        if(!selectedVoice.equals("default")&&voiceEntry(selectedVoice,c)==null)
            android.widget.Toast.makeText(ctx,"所选声音未覆盖本组，使用默认声音",android.widget.Toast.LENGTH_SHORT).show();
        if(custom!=null){try{player.setDataSource(new File(ctx.getFilesDir(),custom.file).getAbsolutePath());return true;}catch(Exception e){Log.e(TAG,"Voice audio failed",e);}}
        String hash=contentHash(c);Entry entry=imported.get(c.id);
        if(entry!=null&&entry.textHash.equals(hash)){
            File file=new File(ctx.getFilesDir(),entry.file);
            if(file.isFile()){
                try{player.setDataSource(file.getAbsolutePath());return true;}
                catch(Exception e){Log.e(TAG,"Bad local audio: "+c.id,e);}
            }
        }
        entry=builtin.get(c.id);
        if(entry==null||!entry.textHash.equals(hash))return false;
        try(AssetFileDescriptor fd=ctx.getAssets().openFd(entry.file)){
            player.setDataSource(fd.getFileDescriptor(),fd.getStartOffset(),fd.getLength());return true;
        }catch(Exception e){Log.e(TAG,"Bad bundled audio: "+c.id,e);return false;}
    }
}
