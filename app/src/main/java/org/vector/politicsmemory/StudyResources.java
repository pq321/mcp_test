package org.vector.politicsmemory;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Typeface;
import android.text.SpannableString;
import android.text.SpannableStringBuilder;
import android.text.Spanned;
import android.text.style.BackgroundColorSpan;
import android.text.style.ForegroundColorSpan;
import android.text.style.LineBackgroundSpan;
import android.text.style.StyleSpan;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Iterator;

/** Optional, separately versioned display/audio metadata. Never mutates card text or ratings. */
final class StudyResources {
    static final String SETTING="study_resources_v1";
    final JSONObject data;
    StudyResources(Context context,StudyStore store){
        JSONObject base=new JSONObject();
        try(InputStream in=context.getAssets().open("study-resources.json")){
            base=new JSONObject(StudyStore.readText(in,20*1024*1024));
        }catch(Exception ignored){}
        try{data=merge(base,new JSONObject(store.setting(SETTING,"{}")));}
        catch(Exception e){throw new IllegalStateException("学习资源索引无法读取",e);}
    }
    static JSONObject merge(JSONObject base,JSONObject patch)throws Exception{
        JSONObject out=new JSONObject(base.toString());out.put("schema_version",1);
        for(String section:new String[]{"sources","voices","annotations"}){
            JSONObject target=out.optJSONObject(section);if(target==null)target=new JSONObject();
            JSONObject incoming=patch.optJSONObject(section);
            if(incoming!=null)for(Iterator<String> it=incoming.keys();it.hasNext();){
                String key=it.next();JSONObject item=incoming.getJSONObject(key),old=target.optJSONObject(key);
                if(old==null||item.optInt("revision",1)>old.optInt("revision",1))target.put(key,item);
            }
            out.put(section,target);
        }
        return out;
    }
    String sourceName(String id,String fallback){
        JSONObject sources=data.optJSONObject("sources"),s=sources==null?null:sources.optJSONObject(id);
        return s==null?fallback:s.optString("name",fallback);
    }
    static final class Voice {final String id,name;Voice(String i,String n){id=i;name=n;}}
    ArrayList<Voice> voices(){
        ArrayList<Voice> out=new ArrayList<>();out.add(new Voice("default",voiceName("default")));
        JSONObject voices=data.optJSONObject("voices");
        if(voices!=null)for(Iterator<String> it=voices.keys();it.hasNext();){
            String id=it.next();JSONObject v=voices.optJSONObject(id);
            if(!id.equals("default")&&v!=null&&!v.optBoolean("retired")&&v.optJSONObject("items")!=null&&v.optJSONObject("items").length()>0)
                out.add(new Voice(id,v.optString("name",id)));
        }
        return out;
    }
    String voiceName(String id){JSONObject v=voice(id);return v==null?(id.equals("default")?"默认声音":id):v.optString("name",id);}
    JSONObject voice(String id){JSONObject vs=data.optJSONObject("voices");JSONObject v=vs==null?null:vs.optJSONObject(id);return v!=null&&!v.optBoolean("retired")?v:null;}
    JSONObject audio(String voice,String card){JSONObject v=voice(voice);JSONObject items=v==null?null:v.optJSONObject("items");return items==null?null:items.optJSONObject(card);}
    JSONArray marks(StudyCard card){
        JSONObject annotations=data.optJSONObject("annotations"),a=annotations==null?null:annotations.optJSONObject(card.id);
        if(a==null||!AudioCatalog.digest(card.answer.getBytes(StandardCharsets.UTF_8)).equals(a.optString("answer_sha256")))return new JSONArray();
        JSONArray marks=a.optJSONArray("marks");return marks==null?new JSONArray():marks;
    }
    CharSequence answer(StudyCard card,boolean cloze){
        JSONArray marks=marks(card);SpannableStringBuilder out=new SpannableStringBuilder();int cursor=0;
        for(int i=0;i<marks.length();i++){
            JSONObject m=marks.optJSONObject(i);if(m==null)continue;
            int start=m.optInt("start",-1),end=m.optInt("end",-1);
            if(start<cursor||end<=start||end>card.answer.length()||!card.answer.substring(start,end).equals(m.optString("text")))continue;
            out.append(card.answer.substring(cursor,start));int at=out.length();boolean hidden=cloze&&m.optBoolean("cloze",false);
            out.append(hidden?"［　　］":card.answer.substring(start,end));int stop=out.length();
            if(hidden)out.setSpan(new ForegroundColorSpan(0xff778282),at,stop,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            else{
                String kind=m.optString("kind");
                if(kind.equals("core")){out.setSpan(new BackgroundColorSpan(0xfffff0b3),at,stop,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);out.setSpan(new StyleSpan(Typeface.BOLD),at,stop,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);}
                if(kind.equals("confusion")){out.setSpan(new ForegroundColorSpan(0xffb23b3b),at,stop,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);out.setSpan(new StyleSpan(Typeface.BOLD),at,stop,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);}
                if(kind.equals("condition"))out.setSpan(new ForegroundColorSpan(0xff286a9a),at,stop,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            }
            cursor=end;
        }
        out.append(card.answer.substring(cursor));
        if(cloze&&marks.length()==0)out.append("\n\n本组尚未提供匹配的挖空标记。");
        return out;
    }
    /** Exact original-source layout; no source text is stored or rewritten in the sidecar. */
    JSONArray presentation(StudyCard card,boolean brief){
        JSONObject anns=data.optJSONObject("annotations"),a=anns==null?null:anns.optJSONObject(card.id);
        if(a==null||!AudioCatalog.digest(card.answer.getBytes(StandardCharsets.UTF_8)).equals(a.optString("answer_sha256")))return null;
        JSONArray blocks=a.optJSONArray(brief?"brief_layout":"full_layout");
        return blocks!=null&&blocks.length()>0?blocks:null;
    }
    /** Render only literal spans of the original answer with the existing highlight colors. */
    CharSequence styledParts(StudyCard card,JSONArray spans){
        SpannableStringBuilder out=new SpannableStringBuilder();
        if(spans==null)return out;
        JSONArray highlights=marks(card);
        for(int i=0;i<spans.length();i++){
            JSONArray p=spans.optJSONArray(i);if(p==null||p.length()<2)continue;
            int start=p.optInt(0,-1),end=p.optInt(1,-1);
            if(start<0||end>card.answer.length()||end<=start)continue;
            while(start<end&&Character.isWhitespace(card.answer.charAt(start)))start++;
            while(end>start&&Character.isWhitespace(card.answer.charAt(end-1)))end--;
            if(end<=start)continue;
            if(out.length()>0)out.append(" · ");
            int base=out.length();out.append(card.answer.substring(start,end));
            for(int j=0;j<highlights.length();j++){
                JSONObject m=highlights.optJSONObject(j);if(m==null)continue;
                int a=Math.max(start,m.optInt("start",-1)),b=Math.min(end,m.optInt("end",-1));
                if(a<start||b<=a)continue;
                int from=base+a-start,to=base+b-start;
                String kind=m.optString("kind");
                if(kind.equals("core")){
                    out.setSpan(new BackgroundColorSpan(0xfffff0b3),from,to,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                    out.setSpan(new StyleSpan(Typeface.BOLD),from,to,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                }else if(kind.equals("confusion")){
                    out.setSpan(new ForegroundColorSpan(0xffb23b3b),from,to,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                    out.setSpan(new StyleSpan(Typeface.BOLD),from,to,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                }else if(kind.equals("condition"))
                    out.setSpan(new ForegroundColorSpan(0xff286a9a),from,to,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            }
        }
        return out;
    }

    static CharSequence wrongTitle(String title){
        SpannableString s=new SpannableString(title);
        s.setSpan(new LineBackgroundSpan(){
            public void drawBackground(Canvas canvas,Paint paint,int left,int right,int top,int baseline,int bottom,CharSequence text,int start,int end,int line){
                Paint p=new Paint(paint);p.setColor(0xff87918d);p.setStrokeWidth(Math.max(1,paint.getTextSize()/18));
                float width=paint.measureText(text,start,end),unit=Math.max(2,paint.getTextSize()/9),y=Math.min(bottom-1,baseline+unit);
                for(float x=left;x<Math.min(right,left+width);x+=unit*2.2f)canvas.drawLine(x,y,Math.min(x+unit,left+width),y,p);
            }
        },0,s.length(),Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);return s;
    }
}
