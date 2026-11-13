package org.vector.politicsmemory;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.media.AudioAttributes;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.util.Log;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/** Offline system-TTS foreground player. No network access, downloaded audio, or account. */
public final class SpeechService extends Service {
    static final String PLAY="org.vector.politicsmemory.PLAY";
    static final String TOGGLE="org.vector.politicsmemory.TOGGLE";
    static final String STOP="org.vector.politicsmemory.STOP";
    static final String EXTRA_FIRST="first_card_id";
    static final String EXTRA_IDS="session_ids";
    private static final String CHANNEL="memorizer_speech";
    private static final int NOTIFICATION_ID=187;
    private static final String TAG="PoliticsMemorySpeech";
    static volatile boolean active=false;
    static volatile boolean paused=false;

    private final Handler handler=new Handler(Looper.getMainLooper());
    private TextToSpeech tts;
    private boolean ready=false;
    private int generation=0;
    private final ArrayList<StudyCard> playlist=new ArrayList<>();
    private List<String> fragments=new ArrayList<>();
    private int cardIndex=0, fragmentIndex=0;
    private String utteranceId="";

    @Override public void onCreate(){
        super.onCreate();
        if(Build.VERSION.SDK_INT>=26){
            NotificationChannel ch=new NotificationChannel(CHANNEL,"政治背诵朗读",NotificationManager.IMPORTANCE_LOW);
            ch.setDescription("离线连续朗读；可以暂停或结束");
            NotificationManager manager=getSystemService(NotificationManager.class);
            if(manager!=null)manager.createNotificationChannel(ch);
        }
    }
    @Override public IBinder onBind(Intent i){return null;}
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        if(intent==null)return START_NOT_STICKY;
        String action=intent.getAction();
        if(STOP.equals(action)){stopPlayback();return START_NOT_STICKY;}
        if(TOGGLE.equals(action)){
            if(active){if(paused)resumePlayback();else pausePlayback();}
            return START_NOT_STICKY;
        }
        if(!PLAY.equals(action))return START_NOT_STICKY;
        generation++;
        playlist.clear();cardIndex=0;fragmentIndex=0;fragments=new ArrayList<>();
        StudyStore store=new StudyStore(this);
        try{
            ArrayList<StudyCard> all=store.allCards();
            ArrayList<String> ids=intent.getStringArrayListExtra(EXTRA_IDS);
            if(ids!=null&&!ids.isEmpty()){
                Map<String,StudyCard> lookup=new HashMap<>();for(StudyCard c:all)lookup.put(c.id,c);
                for(String id:ids){StudyCard c=lookup.get(id);if(c!=null)playlist.add(c);}
            }else{
                String first=intent.getStringExtra(EXTRA_FIRST);
                int at=0;
                if(first!=null&&!first.isEmpty()){
                    at=-1;for(int i=0;i<all.size();i++)if(first.equals(all.get(i).id)){at=i;break;}
                }
                if(at>=0)for(int i=at;i<all.size();i++)playlist.add(all.get(i));
            }
        }catch(Exception ex){Log.e(TAG,"Failed to read offline study data",ex);}
        finally{store.close();}
        if(playlist.isEmpty()){stopPlayback();return START_NOT_STICKY;}
        active=true;paused=false;
        // A foreground media service is needed so audio continues with the screen locked.
        try{
            Notification n=notification();
            if(Build.VERSION.SDK_INT>=29){startForeground(NOTIFICATION_ID,n,ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK);}
            else startForeground(NOTIFICATION_ID,n);
        }catch(Exception e){Log.e(TAG,"Foreground playback unavailable",e);stopPlayback();return START_NOT_STICKY;}
        if(tts==null){
            ready=false;
            tts=new TextToSpeech(getApplicationContext(),status->handler.post(()->initializeTts(status)));
        }else if(ready){
            tts.stop();readCard();
        }
        return START_NOT_STICKY;
    }
    private void initializeTts(int status){
        if(!active||tts==null)return;
        if(status!=TextToSpeech.SUCCESS){Log.w(TAG,"No local TextToSpeech engine");stopPlayback();return;}
        tts.setAudioAttributes(new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_MEDIA)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build());
        int result=tts.setLanguage(Locale.SIMPLIFIED_CHINESE);
        if(result==TextToSpeech.LANG_MISSING_DATA||result==TextToSpeech.LANG_NOT_SUPPORTED){
            Log.w(TAG,"Chinese offline voice not installed");stopPlayback();return;
        }
        // Never use a network-required voice; installed Chinese voice is a device prerequisite.
        if(Build.VERSION.SDK_INT>=21){
            Set<android.speech.tts.Voice> voices=tts.getVoices();
            if(voices!=null && !voices.isEmpty()){
                android.speech.tts.Voice chosen=null;
                for(android.speech.tts.Voice voice:voices){
                    if("zh".equals(voice.getLocale().getLanguage())&&!voice.isNetworkConnectionRequired()){
                        chosen=voice;
                        if("CN".equals(voice.getLocale().getCountry()))break;
                    }
                }
                if(chosen==null){
                    Log.w(TAG,"No installed Chinese offline voice: user must install one in Android settings");
                    stopPlayback();return;
                }
                tts.setVoice(chosen);
            }
        }
        tts.setSpeechRate(0.88f);
        tts.setOnUtteranceProgressListener(new UtteranceProgressListener(){
            @Override public void onStart(String utteranceId){}
            @Override public void onDone(String id){handler.post(()->completed(id));}
            @Override public void onError(String id){handler.post(()->completed(id));}
        });
        ready=true;
        readCard();
    }
    private void completed(String id){
        if(!active||paused||!utteranceId.equals(id))return;
        fragmentIndex++;
        if(fragmentIndex<fragments.size())speakFragment();
        else {cardIndex++;fragmentIndex=0;readCard();}
    }
    private void readCard(){
        if(!active||paused||!ready||tts==null)return;
        if(cardIndex>=playlist.size()){stopPlayback();return;}
        StudyCard c=playlist.get(cardIndex);
        String full=c.question+"。"+c.answer;
        fragments=chunkText(full,1900);
        fragmentIndex=0;
        updateNotification();
        speakFragment();
    }
    private void speakFragment(){
        if(!active||paused||!ready||fragmentIndex>=fragments.size())return;
        utteranceId=generation+"/"+cardIndex+"/"+fragmentIndex;
        int result=tts.speak(fragments.get(fragmentIndex),TextToSpeech.QUEUE_FLUSH,null,utteranceId);
        if(result==TextToSpeech.ERROR){
            handler.postDelayed(()->completed(utteranceId),200);
        }
    }
    /** Android TTS limits each utterance; split on prose punctuation, never truncate essays. */
    static List<String> chunkText(String source,int max){
        ArrayList<String> pieces=new ArrayList<>();
        String text=source.replaceAll("[\\t\\r]+"," ").trim();
        for(int start=0;start<text.length();){
            int end=Math.min(text.length(),start+max);
            if(end<text.length()){
                int cut=-1;for(int i=end-1;i>=start+max/3;i--){
                    if("。！？；\n，、：,.!?;".indexOf(text.charAt(i))>=0){cut=i+1;break;}
                }
                if(cut>start)end=cut;
            }
            String fragment=text.substring(start,end).trim();if(!fragment.isEmpty())pieces.add(fragment);
            start=end;
        }
        if(pieces.isEmpty())pieces.add("无朗读内容");
        return pieces;
    }
    private void pausePlayback(){
        if(!active)return;
        paused=true;utteranceId="";
        if(tts!=null)tts.stop();
        updateNotification();
    }
    private void resumePlayback(){
        if(!active)return;
        paused=false;
        fragmentIndex=0; // Android TTS offers no exact pause position; replay current item.
        readCard();
    }
    private void stopPlayback(){
        active=false;paused=false;generation++;utteranceId="";
        if(tts!=null)tts.stop();
        stopForeground(true);
        stopSelf();
    }
    private PendingIntent serviceIntent(String action,int request){
        Intent i=new Intent(this,SpeechService.class);i.setAction(action);
        return PendingIntent.getService(this,request,i,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
    }
    private Notification notification(){
        String label=playlist.isEmpty()?"准备朗读":"第"+(cardIndex+1)+"/"+playlist.size()+"条 · "+playlist.get(Math.min(cardIndex,playlist.size()-1)).topic;
        Notification.Builder n=Build.VERSION.SDK_INT>=26?new Notification.Builder(this,CHANNEL):new Notification.Builder(this);
        Intent open=new Intent(this,MainActivity.class);open.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent show=PendingIntent.getActivity(this,0,open,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        n.setContentTitle(paused?"政治背诵 · 已暂停":"政治背诵 · 离线朗读中")
         .setContentText(label).setSmallIcon(android.R.drawable.ic_media_play).setContentIntent(show)
         .setOngoing(!paused).setOnlyAlertOnce(true)
         .setVisibility(Notification.VISIBILITY_PUBLIC)
         .addAction(paused?android.R.drawable.ic_media_play:android.R.drawable.ic_media_pause,
                    paused?"继续":"暂停",serviceIntent(TOGGLE,1))
         .addAction(android.R.drawable.ic_menu_close_clear_cancel,"停止",serviceIntent(STOP,2));
        return n.build();
    }
    private void updateNotification(){
        NotificationManager manager=getSystemService(NotificationManager.class);
        if(manager!=null && active)manager.notify(NOTIFICATION_ID,notification());
    }
    @Override public void onDestroy(){
        active=false;paused=false;generation++;
        if(tts!=null){tts.stop();tts.shutdown();tts=null;}
        super.onDestroy();
    }
}
