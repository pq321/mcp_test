package org.vector.politicsmemory;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.media.AudioAttributes;
import android.media.MediaPlayer;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;

/** Foreground offline playback of prerendered MP3. No network or on-device TTS. */
public final class SpeechService extends Service {
    static final String PLAY="org.vector.politicsmemory.PLAY";
    static final String TOGGLE="org.vector.politicsmemory.TOGGLE";
    static final String STOP="org.vector.politicsmemory.STOP";
    static final String EXTRA_FIRST="first_card_id";
    static final String EXTRA_IDS="session_ids";
    private static final String CHANNEL="memorizer_speech";
    private static final int NOTIFICATION_ID=187;
    private static final String TAG="PoliticsAudio";
    static volatile boolean active=false;
    static volatile boolean paused=false;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final ArrayList<StudyCard> playlist=new ArrayList<>();
    private MediaPlayer player;
    private AudioCatalog catalogue;
    private int generation=0,cardIndex=0;
    private boolean prepared=false;

    @Override public void onCreate(){
        super.onCreate();
        if(Build.VERSION.SDK_INT>=26){
            NotificationChannel ch=new NotificationChannel(CHANNEL,"政治背诵朗读",NotificationManager.IMPORTANCE_LOW);
            ch.setDescription("内置音频连续朗读，息屏仍可暂停和停止");
            NotificationManager m=getSystemService(NotificationManager.class);
            if(m!=null)m.createNotificationChannel(ch);
        }
        catalogue=new AudioCatalog(this);
    }
    @Override public IBinder onBind(Intent i){return null;}
    @Override public int onStartCommand(Intent i,int flags,int startId){
        if(i==null)return START_NOT_STICKY;
        String action=i.getAction();
        if(STOP.equals(action)){stopPlayback();return START_NOT_STICKY;}
        if(TOGGLE.equals(action)){
            if(active){if(paused)resumePlayback();else pausePlayback();}
            return START_NOT_STICKY;
        }
        if(!PLAY.equals(action))return START_NOT_STICKY;
        generation++;releasePlayer();playlist.clear();cardIndex=0;paused=false;prepared=false;
        // Reload after an audio-pack import while the app is already running.
        catalogue=new AudioCatalog(this);
        StudyStore store=new StudyStore(this);
        try{
            ArrayList<StudyCard> all=store.allCards();
            ArrayList<String> ids=i.getStringArrayListExtra(EXTRA_IDS);
            if(ids!=null&&!ids.isEmpty()){
                Map<String,StudyCard> map=new HashMap<>();for(StudyCard c:all)map.put(c.id,c);
                for(String id:ids){StudyCard c=map.get(id);if(c!=null)playlist.add(c);}
            }else{
                String first=i.getStringExtra(EXTRA_FIRST);int at=0;
                if(first!=null&&!first.isEmpty()){
                    at=-1;for(int n=0;n<all.size();n++)if(first.equals(all.get(n).id)){at=n;break;}
                }
                if(at>=0)for(int n=at;n<all.size();n++)playlist.add(all.get(n));
            }
        }catch(Exception e){Log.e(TAG,"Failed loading playlist",e);}finally{store.close();}
        if(playlist.isEmpty()){stopPlayback();return START_NOT_STICKY;}
        boolean any=false;for(StudyCard c:playlist){if(catalogue.ready(c)){any=true;break;}}
        if(!any){Log.w(TAG,"No matching prerecorded MP3; import audio bundle for these cards");stopPlayback();return START_NOT_STICKY;}
        active=true;
        try{
            if(Build.VERSION.SDK_INT>=29)startForeground(NOTIFICATION_ID,notification(),ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK);
            else startForeground(NOTIFICATION_ID,notification());
        }catch(Exception e){Log.e(TAG,"Foreground media playback rejected",e);stopPlayback();return START_NOT_STICKY;}
        playCurrent();return START_NOT_STICKY;
    }
    private void playCurrent(){
        if(!active||paused)return;
        releasePlayer();prepared=false;
        while(cardIndex<playlist.size()&&!catalogue.ready(playlist.get(cardIndex)))cardIndex++;
        if(cardIndex>=playlist.size()){stopPlayback();return;}
        final int token=generation;final int index=cardIndex;
        MediaPlayer next=new MediaPlayer();player=next;
        try{
            next.setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build());
            if(!catalogue.attach(next,playlist.get(cardIndex))){advance(token,index);return;}
            next.setOnPreparedListener(p->{
                if(!active||token!=generation||index!=cardIndex||p!=player)return;
                prepared=true;
                if(!paused)p.start();
            });
            next.setOnCompletionListener(p->handler.post(()->advance(token,index)));
            next.setOnErrorListener((p,what,extra)->{handler.post(()->advance(token,index));return true;});
            updateNotification();next.prepareAsync();
        }catch(Exception e){Log.e(TAG,"MP3 decoding error",e);advance(token,index);}
    }
    private void advance(int token,int index){
        if(!active||paused||token!=generation||index!=cardIndex)return;
        cardIndex++;playCurrent();
    }
    private void pausePlayback(){
        if(!active)return;paused=true;
        try{if(player!=null&&prepared&&player.isPlaying())player.pause();}catch(Exception e){Log.w(TAG,"pause",e);}
        updateNotification();
    }
    private void resumePlayback(){
        if(!active)return;paused=false;
        try{if(player!=null&&prepared)player.start();else if(player==null)playCurrent();}
        catch(Exception e){Log.e(TAG,"resume",e);playCurrent();}
        updateNotification();
    }
    private void releasePlayer(){
        MediaPlayer old=player;player=null;prepared=false;
        if(old!=null){try{old.reset();old.release();}catch(Exception ignored){}}
    }
    private void stopPlayback(){
        active=false;paused=false;generation++;releasePlayer();
        stopForeground(true);stopSelf();
    }
    private PendingIntent serviceIntent(String action,int request){
        Intent i=new Intent(this,SpeechService.class);i.setAction(action);
        return PendingIntent.getService(this,request,i,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
    }
    private Notification notification(){
        String label=playlist.isEmpty()?"准备音频": "第"+(cardIndex+1)+"/"+playlist.size()+"条 · "+playlist.get(Math.min(cardIndex,playlist.size()-1)).topic;
        Notification.Builder b=Build.VERSION.SDK_INT>=26?new Notification.Builder(this,CHANNEL):new Notification.Builder(this);
        Intent open=new Intent(this,MainActivity.class);open.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent show=PendingIntent.getActivity(this,0,open,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        b.setContentTitle(paused?"政治背诵 · 已暂停":"政治背诵 · 内置音频播放中")
         .setContentText(label).setSmallIcon(android.R.drawable.ic_media_play).setContentIntent(show)
         .setOngoing(!paused).setOnlyAlertOnce(true).setVisibility(Notification.VISIBILITY_PUBLIC)
         .addAction(paused?android.R.drawable.ic_media_play:android.R.drawable.ic_media_pause,
              paused?"继续":"暂停",serviceIntent(TOGGLE,1))
         .addAction(android.R.drawable.ic_menu_close_clear_cancel,"停止",serviceIntent(STOP,2));
        return b.build();
    }
    private void updateNotification(){
        NotificationManager m=getSystemService(NotificationManager.class);
        if(m!=null&&active)m.notify(NOTIFICATION_ID,notification());
    }
    @Override public void onDestroy(){active=false;paused=false;generation++;releasePlayer();super.onDestroy();}
}
