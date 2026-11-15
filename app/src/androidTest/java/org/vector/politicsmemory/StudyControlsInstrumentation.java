package org.vector.politicsmemory;

import android.app.Instrumentation;
import android.app.Activity;
import android.content.Context;
import android.os.Bundle;
import android.media.MediaPlayer;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** One installed-device acceptance scenario. Fixture recordings never enter the released APK. */
public final class StudyControlsInstrumentation extends Instrumentation {
    @Override public void onCreate(Bundle args){super.onCreate(args);start();}
    private static void check(boolean ok,String message){if(!ok)throw new AssertionError(message);}
    private static void entry(ZipOutputStream z,String name,byte[] bytes)throws Exception{z.putNextEntry(new ZipEntry(name));z.write(bytes);z.closeEntry();}
    private File bundle(JSONObject resources,JSONObject pack,byte[] audio,String audioName)throws Exception{
        File file=new File(getTargetContext().getCacheDir(),"fixture-study-update.zip");
        try(ZipOutputStream z=new ZipOutputStream(new FileOutputStream(file))){
            entry(z,"update.json","{\"kind\":\"politics-memory-content-update\",\"schema_version\":1,\"resource_update\":true}".getBytes(StandardCharsets.UTF_8));
            entry(z,"study-resources.json",resources.toString().getBytes(StandardCharsets.UTF_8));
            if(pack!=null)entry(z,"packs/"+pack.getString("pack_id")+".json",pack.toString().getBytes(StandardCharsets.UTF_8));
            if(audio!=null)entry(z,audioName,audio);
        }return file;
    }
    @Override public void onStart(){
        Bundle output=new Bundle();StudyStore store=null;
        try{
            Context context=getTargetContext();store=new StudyStore(context);store.installStarterOnce();
            check(store.allCards().size()==561,"561 cards retained after installation upgrade");StudyCard first=store.allCards().get(0);
            check(first.reviewCount==1&&"yes".equals(first.lastRating),"Original v0.11 database rating retained");
            int eventsBefore=store.backup().getJSONArray("events").length();StudyResources resources=new StudyResources(context,store);
            check("苏一".equals(resources.sourceName(first.packId,"")),"source name");
            for(StudyCard card:store.allCards()){
                JSONArray marks=resources.marks(card);boolean cloze=false;int last=0;
                for(int j=0;j<marks.length();j++){JSONObject m=marks.getJSONObject(j);int start=m.getInt("start"),end=m.getInt("end");check(start>=last&&end>start&&card.answer.substring(start,end).equals(m.getString("text")),"annotation exact span");last=end;cloze|=m.optBoolean("cloze");}
                check(cloze,"every current group has cloze anchors");check(resources.answer(card,false).toString().equals(card.answer),"full rendering preserves original text");check(resources.answer(card,true).toString().contains("［　　］"),"cloze rendered without answer");
            }
            check(!store.wasWrong(first.id),"not a question mistake solely from rating");store.setWrong(first.id,true);store.setWrong(first.id,false);check(store.wasWrong(first.id),"question mistake history retained after unmark");
            JSONObject originalPack;try(InputStream in=context.getAssets().open("suyi-full.json")){originalPack=new JSONObject(StudyStore.readText(in,20*1024*1024));}
            JSONObject extra=new JSONObject(originalPack.getJSONArray("cards").getJSONObject(0).toString());extra.put("id","fixture.other.first");
            JSONObject pack=new JSONObject().put("schema_version",1).put("pack_id","fixture-other").put("title","测试来源").put("pack_revision",1).put("cards",new JSONArray().put(extra));
            byte[] audio;try(InputStream in=context.getAssets().open("audio/"+first.id+".mp3")){ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] b=new byte[8192];int n;while((n=in.read(b))!=-1)bytes.write(b,0,n);audio=bytes.toByteArray();}
            String path="audio/fixture/1/"+first.id+".mp3";
            JSONObject item=new JSONObject().put("file",path).put("text_sha256",AudioCatalog.contentHash(first)).put("audio_sha256",AudioCatalog.digest(audio));
            JSONObject voice=new JSONObject().put("name","验收声音（测试）").put("revision",1).put("items",new JSONObject().put(first.id,item));
            JSONObject patch=new JSONObject().put("schema_version",1).put("sources",new JSONObject().put("fixture-other",new JSONObject().put("name","测试来源").put("revision",1))).put("voices",new JSONObject().put("fixture",voice)).put("annotations",new JSONObject());
            ContentUpdate.Result update=ContentUpdate.apply(context,bundle(patch,pack,audio,path),store);check(update.added==1&&store.allCards().size()==562,"independent source add");
            store.saveSetting("speech_voice","fixture");AudioCatalog catalogue=new AudioCatalog(context);check(catalogue.ready(first),"selected voice available");
            MediaPlayer player=new MediaPlayer();try{check(catalogue.attach(player,first),"selected imported MP3 attached");player.prepare();check(player.getDuration()>0,"selected MP3 actually decoded");}finally{player.release();}
            StudyCard preserved=store.allCards().get(0);check(preserved.reviewCount==1&&!preserved.needsReview,"voice/source metadata does not reset mastery");
            check(store.backup().getJSONArray("events").length()==eventsBefore,"resource update adds no scoring event");
            // Corrupt candidate is rejected without changing metadata or the active audio.
            String before=store.setting(StudyResources.SETTING,"");byte[] broken=audio.clone();broken[broken.length-1]^=1;boolean failed=false;
            try{ContentUpdate.apply(context,bundle(patch,null,broken,path),store);}catch(Exception expected){failed=true;}
            check(failed&&store.setting(StudyResources.SETTING,"").equals(before),"corrupt audio rejected without active metadata change");
            store.rate("fixture.other.first","fuzzy");pack.put("pack_revision",2).put("cards",new JSONArray());
            ContentUpdate.apply(context,bundle(patch,pack,audio,path),store);check(store.allCards().size()==561,"only other pack retired");
            boolean kept=false;JSONArray reviews=store.backup().getJSONArray("reviews");for(int n=0;n<reviews.length();n++)kept|="fixture.other.first".equals(reviews.getJSONObject(n).getString("card_id"));check(kept,"retired source retains history");
            store.saveSetting("speech_voice","default");store.saveSetting(StudyResources.SETTING,"{}");
            output.putString("stream","PASS: legacy database keeps ratings; 561 exact full/cloze renderings; independent source add/retire; global optional voice import and MediaPlayer decode; corrupt audio rejected; no false question mistake from rating.\n");finish(Activity.RESULT_OK,output);
        }catch(Throwable e){output.putString("stream","FAIL: "+android.util.Log.getStackTraceString(e));finish(Activity.RESULT_CANCELED,output);}
        finally{if(store!=null)store.close();}
    }
}
