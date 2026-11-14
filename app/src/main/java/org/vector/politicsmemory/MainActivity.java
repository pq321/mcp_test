package org.vector.politicsmemory;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.InputMethodManager;
import android.content.Context;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Single offline Activity, platform views, no ad SDK, network access or WebView. */
public final class MainActivity extends Activity {
    private static final int TEAL=Color.rgb(54,172,157), ORANGE=Color.rgb(220,105,65);
    private static final int DARK=Color.rgb(49,54,55), MUTED=Color.rgb(130,136,138);
    private static final int BACK=Color.rgb(247,247,247), WHITE=Color.WHITE;
    private static final int IMPORT=20,EXPORT_JSON=21,EXPORT_CSV=22;
    private final String[] tabs={"复习","资料","统计"};
    private StudyStore store;
    private LinearLayout root,nav;
    private FrameLayout content;
    private int currentTab=1;
    private boolean showAnswer=false;
    private ArrayList<StudyCard> session=new ArrayList<>();
    private SwipePagerLayout pager;
    private String catalogueFilter="";
    private String currentScope="全部资料";
    private int dailyGoal=25;

    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        getWindow().setStatusBarColor(BACK);
        getWindow().setNavigationBarColor(BACK);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        store=new StudyStore(this);
        dailyGoal=parseGoal(store.setting("daily_goal","25"));
        showAnswer="true".equals(store.setting("show_answer","false"));
        buildRoot();
        switchTab(1);
        // Install or upgrade the bundled Su Yi heading map; never delete local ratings.
        new Thread(()->{
            try{store.installStarterOnce();runOnUiThread(()->switchTab(1));}
            catch(Exception e){runOnUiThread(()->error("内置素材初始化失败："+e.getMessage()));}
        }).start();
    }
    @Override protected void onDestroy(){store.close();super.onDestroy();}
    private int parseGoal(String v){try{int k=Integer.parseInt(v);return Math.max(5,Math.min(100,k));}catch(Exception e){return 25;}}
    private int dp(float value){return Math.round(getResources().getDisplayMetrics().density*value);}
    private GradientDrawable bg(int color,float radius){
        GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));return d;
    }
    private GradientDrawable stroke(int color,float radius,int line){
        GradientDrawable d=bg(color,radius);d.setStroke(dp(1),line);return d;
    }
    private GradientDrawable gradient(){
        GradientDrawable g=new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM,new int[]{0xff4e9da8,0xff89c9ce});
        g.setCornerRadius(0);return g;
    }
    private TextView text(String t,float sp,int color,boolean bold){
        TextView v=new TextView(this);v.setText(t);v.setTextColor(color);v.setTextSize(sp);
        v.setIncludeFontPadding(true);if(bold)v.setTypeface(Typeface.DEFAULT,Typeface.BOLD);return v;
    }
    private LinearLayout column(){LinearLayout v=new LinearLayout(this);v.setOrientation(LinearLayout.VERTICAL);return v;}
    private LinearLayout row(){LinearLayout v=new LinearLayout(this);v.setOrientation(LinearLayout.HORIZONTAL);v.setGravity(Gravity.CENTER_VERTICAL);return v;}
    private LinearLayout.LayoutParams lp(int w,int h){return new LinearLayout.LayoutParams(w<0?w:dp(w),h<0?h:dp(h));}
    private void padding(View v,int l,int t,int r,int b){v.setPadding(dp(l),dp(t),dp(r),dp(b));}
    private void spacer(LinearLayout layout,int height){layout.addView(new View(this),lp(-1,height));}
    private void buildRoot(){
        root=column();root.setBackgroundColor(BACK);setContentView(root);
        content=new FrameLayout(this);root.addView(content,new LinearLayout.LayoutParams(-1,0,1));
        nav=row();nav.setBackground(stroke(WHITE,0,0xffeeeeee));
        root.addView(nav,lp(-1,62));
    }
    private void switchTab(int index){
        currentTab=index;content.removeAllViews();pager=null;
        if(index==0)showReview();
        else if(index==1)showCatalogue();
        else showStatistics();
        showNav();
    }
    private void showNav(){
        nav.removeAllViews();
        String[] symbols={"◷","▤","⌁"};
        for(int i=0;i<3;i++){
            final int selected=i;
            LinearLayout cell=column();cell.setGravity(Gravity.CENTER);cell.setClickable(true);
            TextView icon=text(symbols[i],24,i==currentTab?TEAL:0xffa8abad,false);icon.setGravity(Gravity.CENTER);
            TextView name=text(tabs[i],12,i==currentTab?TEAL:0xffa8abad,i==currentTab);name.setGravity(Gravity.CENTER);
            cell.addView(icon);cell.addView(name);
            cell.setOnClickListener(v->switchTab(selected));
            nav.addView(cell,new LinearLayout.LayoutParams(0,-1,1));
        }
    }
    private LinearLayout titleBar(String title,boolean menu){
        LinearLayout bar=row();padding(bar,18,15,16,13);
        TextView t=text(title,22,DARK,false);bar.addView(t,new LinearLayout.LayoutParams(0,-2,1));
        if(menu){
            if(SpeechService.active){
                TextView stop=text("■",19,TEAL,true);padding(stop,10,4,10,4);
                stop.setContentDescription("停止朗读");
                stop.setOnClickListener(v->{stopSpeech();switchTab(currentTab);});bar.addView(stop);
            }
            TextView button=text("⋮",28,DARK,false);padding(button,13,0,5,0);
            button.setOnClickListener(v->showFileMenu());bar.addView(button);
        }
        return bar;
    }
    private void showFileMenu(){
        String[] items={"导入素材、音频包或备份（JSON/ZIP）","导出完整备份（JSON）","导出学习记录（CSV）",
                "朗读倍速："+String.format(Locale.CHINA,"%.2f×",speechSpeed()),"每日目标："+dailyGoal+"组","查看数据格式说明"};
        new AlertDialog.Builder(this).setTitle("本地工具").setItems(items,(d,which)->{
            if(which==0)chooseImport();else if(which==1)chooseExport(false);
            else if(which==2)chooseExport(true);else if(which==3)changeSpeechSpeed();
            else if(which==4)changeGoal();else showFormatHelp();
        }).show();
    }
    private float speechSpeed(){
        try{return Math.max(0.75f,Math.min(2f,Float.parseFloat(store.setting("speech_speed","1.0"))));}
        catch(Exception e){return 1f;}
    }
    private void changeSpeechSpeed(){
        final float[] values={0.75f,1f,1.25f,1.5f,1.75f,2f};
        String[] labels={"0.75×","1.0×","1.25×","1.5×","1.75×","2.0×"};
        int selected=1;for(int i=0;i<values.length;i++)if(Math.abs(values[i]-speechSpeed())<0.001f)selected=i;
        new AlertDialog.Builder(this).setTitle("朗读倍速").setSingleChoiceItems(labels,selected,(dialog,which)->{
            float speed=values[which];store.saveSetting("speech_speed",Float.toString(speed));
            if(SpeechService.active){Intent i=new Intent(this,SpeechService.class);i.setAction(SpeechService.SET_SPEED);i.putExtra(SpeechService.EXTRA_SPEED,speed);startService(i);}
            dialog.dismiss();Toast.makeText(this,"已设置为 "+labels[which],Toast.LENGTH_SHORT).show();
            if(pager!=null)pager.refresh();
        }).setNegativeButton("取消",null).show();
    }
    /** Play all cards from this heading, then continue to the following headings. */
    private TextView playButton(Runnable start){
        TextView button=text("▶",17,TEAL,true);
        button.setGravity(Gravity.CENTER);button.setContentDescription("从此标题开始连续朗读");
        button.setBackground(bg(0xffeaf7f5,22));
        LinearLayout.LayoutParams p=lp(39,35);p.leftMargin=dp(7);button.setLayoutParams(p);
        button.setOnClickListener(v->start.run());return button;
    }
    /** Play exactly the selected subject/chapter/topic, not every later card in the book. */
    private void startContinuousSpeech(List<StudyCard> cards){
        if(cards==null||cards.isEmpty())return;
        Intent i=new Intent(this,SpeechService.class);i.setAction(SpeechService.PLAY);
        ArrayList<String> ids=new ArrayList<>();
        for(StudyCard card:cards)ids.add(card.id);
        i.putStringArrayListExtra(SpeechService.EXTRA_IDS,ids);
        i.putExtra(SpeechService.EXTRA_SPEED,speechSpeed());
        launchSpeech(i);
    }
    private void startReviewSpeech(int position){
        if(SpeechService.active){
            Intent i=new Intent(this,SpeechService.class);i.setAction(SpeechService.TOGGLE);
            startService(i);return;
        }
        if(session.isEmpty())return;
        Intent i=new Intent(this,SpeechService.class);i.setAction(SpeechService.PLAY);
        ArrayList<String> ids=new ArrayList<>();
        for(int j=position;j<session.size();j++)ids.add(session.get(j).id);
        i.putStringArrayListExtra(SpeechService.EXTRA_IDS,ids);i.putExtra(SpeechService.EXTRA_SPEED,speechSpeed());
        launchSpeech(i);
    }
    private void launchSpeech(Intent i){
        try{
            if(android.os.Build.VERSION.SDK_INT>=26)startForegroundService(i);
            else startService(i);
            Toast.makeText(this,"开始播放预制音频 · 通知栏可暂停或停止",Toast.LENGTH_SHORT).show();
        }catch(Exception e){error("无法启动音频播放："+e.getMessage());}
    }
    private void stopSpeech(){
        Intent i=new Intent(this,SpeechService.class);i.setAction(SpeechService.STOP);
        startService(i);
    }
    private void showCatalogue(){
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);
        content.addView(scroll);LinearLayout body=column();padding(body,13,3,13,25);scroll.addView(body);
        body.addView(titleBar("Books · 政治背诵",true));
        EditText search=new EditText(this);search.setSingleLine(true);search.setTextSize(16);
        search.setHint("⌕  搜索知识点 / 考点");search.setGravity(Gravity.CENTER_VERTICAL);
        search.setBackground(bg(WHITE,8));padding(search,16,7,10,7);
        search.setText(catalogueFilter);body.addView(search,lp(-1,48));
        spacer(body,12);
        ArrayList<StudyCard> all=store.allCards();
        final String filter=catalogueFilter.trim();
        if(!filter.isEmpty()){
            showFiltered(body,all,filter);
            return;
        }
        Summary s=summary(all);
        LinearLayout summary=row();
        summary.addView(statCard("今日目标",dailyGoal+"组", "点击复习开始",()->switchTab(0)),new LinearLayout.LayoutParams(0,dp(76),1.45f));
        View gap=new View(this);summary.addView(gap,lp(8,1));
        summary.addView(statCard("平均熟悉度",String.format(Locale.CHINA,"%.1f/4",s.average()),"掌握"+s.mastered+"组",()->switchTab(2)),new LinearLayout.LayoutParams(0,dp(76),1f));
        body.addView(summary);spacer(body,7);
        LinearLayout shortcuts=row();
        shortcuts.addView(tinyMetric("到期",s.due,TEAL,()->switchTab(0)),new LinearLayout.LayoutParams(0,dp(50),1));
        shortcuts.addView(tinyMetric("未学习",s.unseen,MUTED,()->switchTab(0)),new LinearLayout.LayoutParams(0,dp(50),1));
        shortcuts.addView(tinyMetric("待复核",s.needsReview,ORANGE,()->switchTab(0)),new LinearLayout.LayoutParams(0,dp(50),1));
        body.addView(shortcuts);spacer(body,8);
        body.addView(sectionTitle("科目 · 章节 · 考点"));spacer(body,6);
        LinkedHashMap<String,LinkedHashMap<String,LinkedHashMap<String,ArrayList<StudyCard>>>> groups=group(all);
        if(groups.isEmpty()){body.addView(text("尚无资料。点击右上角 ⋮ 导入素材JSON。",15,MUTED,false));return;}
        for(Map.Entry<String,LinkedHashMap<String,LinkedHashMap<String,ArrayList<StudyCard>>>> subject:groups.entrySet()){
            ArrayList<StudyCard> sCards=select(all,subject.getKey(),null,null);
            LinearLayout card=column();card.setBackground(bg(WHITE,9));padding(card,12,8,12,8);
            String key="open_sub_"+subject.getKey();
            LinearLayout inner=column();
            boolean expanded="1".equals(store.setting(key,"1"));inner.setVisibility(expanded?View.VISIBLE:View.GONE);
            LinearLayout sHeader=row();
            TextView st=text((expanded?"▾  ":"▸  ")+subject.getKey(),19,DARK,true);
            sHeader.addView(st,new LinearLayout.LayoutParams(0,-2,1));
            sHeader.addView(playButton(()->startContinuousSpeech(sCards)));
            card.addView(sHeader);card.addView(progressText(summary(sCards)));
            addProgressBar(card,summary(sCards));spacer(card,8);card.addView(inner);
            st.setOnClickListener(v->{boolean open=inner.getVisibility()!=View.VISIBLE;
                inner.setVisibility(open?View.VISIBLE:View.GONE);st.setText((open?"▾  ":"▸  ")+subject.getKey());
                store.saveSetting(key,open?"1":"0");});
            for(Map.Entry<String,LinkedHashMap<String,ArrayList<StudyCard>>> chapter:subject.getValue().entrySet()){
                ArrayList<StudyCard> cCards=select(all,subject.getKey(),chapter.getKey(),null);
                LinearLayout cBlock=column();
                String cKey="open_ch_"+subject.getKey()+"_"+chapter.getKey();
                boolean cExpand="1".equals(store.setting(cKey,"0"));
                LinearLayout cHeader=row();padding(cHeader,0,12,0,3);
                TextView ct=text((cExpand?"▾  ":"▸  ")+chapter.getKey(),15,DARK,true);
                cHeader.addView(ct,new LinearLayout.LayoutParams(0,-2,1));
                cHeader.addView(playButton(()->startContinuousSpeech(cCards)));
                cBlock.addView(cHeader);cBlock.addView(indentedProgress(summary(cCards),1));
                LinearLayout topics=column();cBlock.addView(topics);
                topics.setVisibility(cExpand?View.VISIBLE:View.GONE);
                ct.setOnClickListener(v->{boolean open=topics.getVisibility()!=View.VISIBLE;
                    topics.setVisibility(open?View.VISIBLE:View.GONE);ct.setText((open?"▾  ":"▸  ")+chapter.getKey());
                    store.saveSetting(cKey,open?"1":"0");});
                for(Map.Entry<String,ArrayList<StudyCard>> topic:chapter.getValue().entrySet()){
                    ArrayList<StudyCard> tCards=topic.getValue();Summary ts=summary(tCards);
                    LinearLayout tRow=row();padding(tRow,20,8,0,8);
                    LinearLayout labels=column();
                    String tKey="open_topic_"+subject.getKey()+"_"+chapter.getKey()+"_"+topic.getKey();
                    boolean tExpanded="1".equals(store.setting(tKey,"0"));
                    TextView tTitle=text((tExpanded?"▾  ":"▸  ")+topic.getKey(),14,DARK,false);
                    labels.addView(tTitle);
                    labels.addView(text("已背 "+ts.covered+"/"+ts.total+"   掌握 "+ts.mastered+"/"+ts.total+"   熟悉 "+String.format(Locale.CHINA,"%.1f",ts.average())+"/4",11,MUTED,false));
                    tRow.addView(labels,new LinearLayout.LayoutParams(0,-2,1));
                    tRow.addView(playButton(()->startContinuousSpeech(tCards)));
                    topics.addView(tRow);
                    LinearLayout leaves=column();leaves.setVisibility(tExpanded?View.VISIBLE:View.GONE);
                    for(StudyCard c:tCards){
                        LinearLayout leaf=column();padding(leaf,36,5,9,6);
                        TextView leafTitle=text(c.displayTitle(),13,DARK,true);leaf.addView(leafTitle);
                        TextView recall=text(c.question,11.5f,MUTED,false);recall.setMaxLines(2);
                        recall.setEllipsize(android.text.TextUtils.TruncateAt.END);leaf.addView(recall);
                        if(c.wrongQuestion)leaf.addView(text("做题错题",9,ORANGE,true));
                        leaf.setOnClickListener(v->startScoped(tCards,topic.getKey(),c.id));
                        leaves.addView(leaf);
                    }
                    topics.addView(leaves);
                    labels.setOnClickListener(v->{boolean open=leaves.getVisibility()!=View.VISIBLE;
                        leaves.setVisibility(open?View.VISIBLE:View.GONE);
                        tTitle.setText((open?"▾  ":"▸  ")+topic.getKey());store.saveSetting(tKey,open?"1":"0");});
                }
                inner.addView(cBlock);
            }
            body.addView(card);spacer(body,10);
        }
        spacer(body,4);body.addView(sectionTitle("其他资料"));spacer(body,5);
        ArrayList<StudyCard> wrong=store.wrongCards(),weak=store.weakCards();
        body.addView(collectionRow("错题", "做题错题 "+wrong.size()+"组 · 背诵薄弱 "+weak.size()+"组", ()->showWrongCollections()));
        if(!groups.containsKey("时政")){spacer(body,7);body.addView(collectionRow("时政", "等待导入你的时政资料", ()->showCurrentAffairsInfo()));}
        // TextWatcher is attached after first render; update filtering when user submits.
        search.addTextChangedListener(new android.text.TextWatcher(){
            public void beforeTextChanged(CharSequence s,int st,int c,int a){}
            public void onTextChanged(CharSequence s,int st,int b,int count){catalogueFilter=s.toString();}
            public void afterTextChanged(android.text.Editable e){}
        });
        search.setImeOptions(android.view.inputmethod.EditorInfo.IME_ACTION_SEARCH);
        search.setOnEditorActionListener((v,action,event)->{
            catalogueFilter=search.getText().toString();hideKeyboard(search);showCatalogueReload();return true;
        });
    }
    private void showCatalogueReload(){content.removeAllViews();showCatalogue();}
    private View collectionRow(String title,String subtitle,Runnable action){
        LinearLayout box=column();box.setBackground(bg(WHITE,8));padding(box,14,10,14,10);
        box.addView(text(title,14,DARK,true));box.addView(text(subtitle,11,MUTED,false));box.setOnClickListener(v->action.run());return box;
    }
    private void showWrongCollections(){
        ArrayList<StudyCard> wrong=store.wrongCards(),weak=store.weakCards();
        String[] labels={"做题错题（主动标记）","背诵薄弱（忘记／模糊）"};
        new AlertDialog.Builder(this).setTitle("错题与薄弱知识组").setItems(labels,(d,which)->{
            if(which==0)startScoped(wrong,"做题错题");else startScoped(weak,"背诵薄弱");
        }).show();
    }
    private void showCurrentAffairsInfo(){
        new AlertDialog.Builder(this).setTitle("时政资料").setMessage("时政目录已预留。你把时政资料发来后，可整理为独立知识组导入；不会用未经核实的时政内容填充。")
                .setPositiveButton("知道了",null).show();
    }
    private void hideKeyboard(View v){((InputMethodManager)getSystemService(Context.INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(v.getWindowToken(),0);v.clearFocus();}
    private void showFiltered(LinearLayout parent,ArrayList<StudyCard> all,String query){
        parent.addView(text("搜索结果（按回车查询，清空后回车返回目录）",12,MUTED,false));spacer(parent,8);
        ArrayList<StudyCard> found=new ArrayList<>();String q=query.toLowerCase(Locale.ROOT);
        for(StudyCard c:all) if((c.displayTitle()+" "+c.question+" "+c.answer+" "+c.topic+" "+c.chapter+" "+c.source).toLowerCase(Locale.ROOT).contains(q))found.add(c);
        parent.addView(text("找到 "+found.size()+" 组",14,TEAL,true));spacer(parent,6);
        for(StudyCard c:found){
            LinearLayout item=column();item.setBackground(bg(WHITE,8));padding(item,12,10,12,10);
            item.addView(text(c.displayTitle(),15,DARK,true));item.addView(text(c.question,12,MUTED,false));
            item.addView(text(c.subject+" · "+c.chapter+" · "+c.topic,11,MUTED,false));
            item.setOnClickListener(v->startScoped(found,"搜索结果",c.id));parent.addView(item);spacer(parent,7);
        }
        // Search always allows keyboard submit, including while displaying search results.
        EditText field=null;
        for(int i=0;i<parent.getChildCount();i++) if(parent.getChildAt(i) instanceof EditText){field=(EditText)parent.getChildAt(i);break;}
        if(field!=null){EditText ref=field;ref.setImeOptions(android.view.inputmethod.EditorInfo.IME_ACTION_SEARCH);
            ref.setOnEditorActionListener((v,action,event)->{catalogueFilter=ref.getText().toString();hideKeyboard(ref);showCatalogueReload();return true;});}
    }
    private LinkedHashMap<String,LinkedHashMap<String,LinkedHashMap<String,ArrayList<StudyCard>>>> group(List<StudyCard> all){
        LinkedHashMap<String,LinkedHashMap<String,LinkedHashMap<String,ArrayList<StudyCard>>>> result=new LinkedHashMap<>();
        for(StudyCard c:all)result.computeIfAbsent(c.subject,k->new LinkedHashMap<>())
                .computeIfAbsent(c.chapter,k->new LinkedHashMap<>())
                .computeIfAbsent(c.topic,k->new ArrayList<>()).add(c);
        return result;
    }
    private ArrayList<StudyCard> select(List<StudyCard> all,String s,String ch,String topic){
        ArrayList<StudyCard> out=new ArrayList<>();
        for(StudyCard c:all)if((s==null||s.equals(c.subject))&&(ch==null||ch.equals(c.chapter))&&(topic==null||topic.equals(c.topic)))out.add(c);
        return out;
    }
    private TextView sectionTitle(String label){TextView v=text(label,15,0xff777777,true);padding(v,7,6,0,4);return v;}
    private View statCard(String label,String value,String sub,Runnable action){
        LinearLayout c=column();c.setBackground(bg(WHITE,8));padding(c,14,10,12,6);
        TextView v=text(value,23,TEAL,true);c.addView(v);c.addView(text(label+"  ·  "+sub,12,MUTED,false));
        c.setOnClickListener(w->action.run());return c;
    }
    private View tinyMetric(String label,int count,int color,Runnable action){
        LinearLayout c=column();c.setGravity(Gravity.CENTER);c.setBackground(stroke(WHITE,7,0xfff0f0f0));
        c.addView(text(label+"  "+count,15,color,true));c.setOnClickListener(w->action.run());return c;
    }
    private TextView progressText(Summary s){
        return text("覆盖 "+s.covered+"/"+s.total+"    掌握 "+s.mastered+"/"+s.total+"    熟悉 "+String.format(Locale.CHINA,"%.1f",s.average())+"/4",12,MUTED,false);
    }
    private TextView indentedProgress(Summary s,int level){
        TextView t=progressText(s);padding(t,level==1?23:0,0,0,2);return t;
    }
    private void addProgressBar(LinearLayout parent,Summary s){
        FrameLayout bar=new FrameLayout(this);bar.setBackground(bg(0xffeeeeee,2));
        LinearLayout.LayoutParams bp=lp(-1,5);bp.topMargin=dp(7);parent.addView(bar,bp);
        if(s.total>0){ View fill=new View(this);fill.setBackground(bg(TEAL,2));
            FrameLayout.LayoutParams fp=new FrameLayout.LayoutParams(-1,-1);bar.addView(fill,fp);
            bar.post(()->{FrameLayout.LayoutParams p=(FrameLayout.LayoutParams)fill.getLayoutParams();p.width=Math.round(bar.getWidth()*s.mastered/(float)s.total);fill.setLayoutParams(p);});
        }
    }
    private static final class Summary{
        int total,covered,mastered,unseen,due,needsReview,totalScore;
        double average(){return total==0?0:totalScore/(double)total;}
    }
    private Summary summary(List<StudyCard> cards){
        Summary s=new Summary();long now=System.currentTimeMillis();
        for(StudyCard c:cards){s.total++;s.totalScore+=c.score;
            if(c.reviewCount>0){s.covered++;if(c.dueAt<=now||c.needsReview)s.due++;}
            else s.unseen++;
            if(c.mastered())s.mastered++;
            if(c.needsReview)s.needsReview++;
        }
        return s;
    }
    private void showReview(){
        ArrayList<StudyCard> all=store.allCards();
        ArrayList<StudyCard> due=new ArrayList<>(), newCards=new ArrayList<>();
        long now=System.currentTimeMillis();
        for(StudyCard c:all){
            if(c.reviewCount==0)newCards.add(c);
            else if(c.dueAt<=now ||c.needsReview)due.add(c);
        }
        due.sort(Comparator.comparingLong(x->x.dueAt));
        session=new ArrayList<>();
        for(StudyCard c:due){if(session.size()>=dailyGoal)break;session.add(c);}
        for(StudyCard c:newCards){if(session.size()>=dailyGoal)break;session.add(c);}
        if(session.isEmpty()){
            LinearLayout v=column();v.setGravity(Gravity.CENTER);padding(v,25,10,25,10);
            v.addView(text("今日复习已完成",24,TEAL,true));spacer(v,14);
            TextView t=text("当前没有到期或待学习的新知识组。可以从资料目录选择章节继续背。",15,MUTED,false);
            t.setGravity(Gravity.CENTER);v.addView(t);content.addView(v);return;
        }
        currentScope="今日复习";
        int start=0;String saved=store.setting("last_card_id","");
        for(int i=0;i<session.size();i++)if(session.get(i).id.equals(saved)){start=i;break;}
        renderPager(start);
    }
    private void startScoped(List<StudyCard> cards,String scope){startScoped(cards,scope,cards.isEmpty()?"":cards.get(0).id);}
    private void startScoped(List<StudyCard> cards,String scope,String id){
        if(cards.isEmpty()){Toast.makeText(this,"这一组没有知识点",Toast.LENGTH_SHORT).show();return;}
        session=new ArrayList<>(cards);currentScope=scope;
        currentTab=0;content.removeAllViews();showNav();
        int start=0;for(int i=0;i<session.size();i++)if(session.get(i).id.equals(id)){start=i;break;}
        renderPager(start);
    }
    private void renderPager(int start){
        if(session.isEmpty())return;
        content.removeAllViews();
        pager=new SwipePagerLayout(this,session.size(),start,this::makeStudyPage,index->{
            store.saveSetting("last_card_id",session.get(index).id);
        });
        content.addView(pager,new FrameLayout.LayoutParams(-1,-1));
        store.saveSetting("last_card_id",session.get(start).id);
    }
    private View makeStudyPage(int index){
        StudyCard card=session.get(index);
        LinearLayout page=column();page.setBackgroundColor(WHITE);
        LinearLayout header=column();header.setBackgroundColor(WHITE);padding(header,18,12,18,10);
        LinearLayout bar=row();
        TextView back=text("‹",30,DARK,false);padding(back,2,0,14,0);back.setOnClickListener(v->switchTab(1));bar.addView(back);
        TextView counter=text((index+1)+"/"+session.size(),13,MUTED,false);bar.addView(counter,new LinearLayout.LayoutParams(0,-2,1));
        TextView mode=text(showAnswer?"收起":"揭晓",12,TEAL,true);padding(mode,8,6,8,6);mode.setBackground(bg(0xffeef8f6,7));
        mode.setOnClickListener(v->toggleAnswer());bar.addView(mode);
        TextView speed=text(String.format(Locale.CHINA,"%.2f×",speechSpeed()),11,TEAL,true);padding(speed,8,6,7,6);
        speed.setOnClickListener(v->changeSpeechSpeed());bar.addView(speed);
        TextView speak=text(SpeechService.active?(SpeechService.paused?"▶":"Ⅱ"):"♫",18,TEAL,true);
        speak.setGravity(Gravity.CENTER);padding(speak,8,4,4,4);speak.setContentDescription("播放当前组及后续知识组；再次点击暂停或继续");
        speak.setOnClickListener(v->{startReviewSpeech(pager==null?index:pager.index());
            speak.postDelayed(()->speak.setText(SpeechService.active?(SpeechService.paused?"▶":"Ⅱ"):"♫"),320);
        });bar.addView(speak);
        TextView wrong=text(card.wrongQuestion?"已错题":"错题+",10,card.wrongQuestion?ORANGE:MUTED,true);
        padding(wrong,7,5,2,5);wrong.setOnClickListener(v->{store.setWrong(card.id,!card.wrongQuestion);card.wrongQuestion=!card.wrongQuestion;pager.refresh();});bar.addView(wrong);
        header.addView(bar);spacer(header,15);
        TextView path=text(card.subject+"  /  "+card.chapter+"  /  "+card.topic,10,MUTED,false);
        path.setGravity(Gravity.CENTER);header.addView(path);spacer(header,7);
        TextView title=text(card.displayTitle(),19,DARK,true);title.setGravity(Gravity.CENTER);title.setLineSpacing(dp(2),1.0f);header.addView(title,lp(-1,-2));spacer(header,9);
        TextView question=text(card.question,13,0xff667172,false);question.setGravity(Gravity.CENTER);question.setLineSpacing(dp(3),1.0f);
        header.addView(question,lp(-1,-2));spacer(header,12);
        View divider=new View(this);divider.setBackgroundColor(0xffe9eceb);header.addView(divider,lp(-1,1));
        page.addView(header,lp(-1,-2));
        FrameLayout answerArea=new FrameLayout(this);page.addView(answerArea,new LinearLayout.LayoutParams(-1,0,1));
        if(!showAnswer){
            TextView prompt=text("请根据上面的问题回忆整组知识点\n点击屏幕揭晓答案",15,0xffa1a7a7,false);
            prompt.setGravity(Gravity.CENTER);prompt.setLineSpacing(dp(7),1);
            answerArea.addView(prompt,new FrameLayout.LayoutParams(-1,-1));answerArea.setOnClickListener(v->toggleAnswer());
        }else{
            ScrollView answerScroll=new ScrollView(this);answerScroll.setFillViewport(true);
            LinearLayout box=column();padding(box,21,19,21,22);
            TextView answer=text(card.answer,16,DARK,false);
            answer.setLineSpacing(dp(6),1.08f);answer.setTextIsSelectable(true);box.addView(answer);
            if(card.notes!=null&&!card.notes.trim().isEmpty()){
                spacer(box,13);TextView note=text(card.notes,9,0xffb54444,false);note.setGravity(Gravity.END);box.addView(note);
            }
            answerScroll.addView(box);answerArea.addView(answerScroll,new FrameLayout.LayoutParams(-1,-1));
        }
        LinearLayout rating=column();rating.setBackground(stroke(WHITE,0,0xffededed));padding(rating,15,9,15,12);
        LinearLayout buttonRow=row();String[] names={"忘记","模糊","记住"};String[] codes={"no","fuzzy","yes"};int[] colors={0xffb77c75,0xffb0a092,TEAL};
        for(int i=0;i<3;i++){
            final String code=codes[i];TextView btn=text(names[i],15,showAnswer?colors[i]:0xffbcbcbc,true);
            btn.setGravity(Gravity.CENTER);btn.setBackground(stroke(showAnswer?0xfff9fcfb:0xfff8f8f8,8,showAnswer?colors[i]:0xffeeeeee));
            LinearLayout.LayoutParams bp=new LinearLayout.LayoutParams(0,dp(45),1);if(i>0)bp.leftMargin=dp(9);buttonRow.addView(btn,bp);
            if(showAnswer)btn.setOnClickListener(v->rateCurrent(card,code));
        }
        rating.addView(buttonRow);spacer(rating,7);
        TextView hint=text("← 左滑上一组   ·   右滑下一组 →",10,MUTED,false);hint.setGravity(Gravity.CENTER);rating.addView(hint);
        page.addView(rating,lp(-1,-2));return page;
    }
    private void toggleAnswer(){
        showAnswer=!showAnswer;store.saveSetting("show_answer",showAnswer?"true":"false");
        if(pager!=null)pager.refresh();
    }
    private void rateCurrent(StudyCard c,String choice){
        try{
            long now=System.currentTimeMillis();
            ReviewLogic.Result calc=ReviewLogic.rate(c.score,c.lastYesDay,choice,now);
            store.rate(c.id,choice);
            c.score=calc.score;c.dueAt=calc.dueAt;c.lastYesDay=calc.lastYesDay;
            c.lastRating=choice;c.reviewCount++;c.lastReviewAt=now;c.needsReview=false;
            int current=pager.index();
            if(current+1<session.size())pager.advanceAfterRating();
            else {pager.refresh();Toast.makeText(this,"本组已到最后一组，背诵结果已保存",Toast.LENGTH_SHORT).show();}
        }catch(Exception e){error("保存失败："+e.getMessage());}
    }
    private void showStatistics(){
        ScrollView scroll=new ScrollView(this);content.addView(scroll);
        LinearLayout body=column();padding(body,16,0,16,20);scroll.addView(body);
        body.addView(titleBar("背诵统计",true));spacer(body,14);
        ArrayList<StudyCard> all=store.allCards();Summary total=summary(all);
        LinearLayout panel=column();panel.setBackground(bg(WHITE,9));padding(panel,18,18,18,18);
        panel.addView(text("掌握进度",15,MUTED,false));spacer(panel,7);
        panel.addView(text(total.mastered+" / "+total.total,32,TEAL,true));spacer(panel,7);
        panel.addView(text("已背 "+total.covered+"    未学 "+total.unseen+"    到期 "+total.due+"    待复核 "+total.needsReview,13,MUTED,false));
        spacer(panel,10);addProgressBar(panel,total);body.addView(panel);spacer(body,15);
        body.addView(sectionTitle("各科掌握状况"));
        LinkedHashMap<String,LinkedHashMap<String,LinkedHashMap<String,ArrayList<StudyCard>>>> map=group(all);
        for(String s:map.keySet()){
            Summary v=summary(select(all,s,null,null));
            LinearLayout item=column();item.setBackground(bg(WHITE,8));padding(item,15,13,15,13);
            item.addView(text(s,17,DARK,true));item.addView(progressText(v));addProgressBar(item,v);
            body.addView(item);spacer(body,8);
        }
        spacer(body,16);
        body.addView(text("做题错题 "+store.wrongCards().size()+" 组 · 背诵薄弱 "+store.weakCards().size()+" 组",13,ORANGE,true));spacer(body,8);
        body.addView(text("掌握判定：至少两次不同日期点“记住”，最近评级仍为“记住”，且内容未改版待复核。",13,MUTED,false));
        spacer(body,8);
        body.addView(text("熟悉度 0—4：不会0、模糊1、熟悉2、掌握3、牢固4。点击不会降到0；内容修改后需重新复核。",13,MUTED,false));
    }
    private void changeGoal(){
        String[] choices={"10","20","25","30","50","100"};
        new AlertDialog.Builder(this).setTitle("每日背诵目标").setItems(choices,(dialog,which)->{
            dailyGoal=Integer.parseInt(choices[which]);store.saveSetting("daily_goal",choices[which]);switchTab(currentTab);
        }).show();
    }
    private void showFormatHelp(){
        new AlertDialog.Builder(this).setTitle("素材导入格式 v1")
                .setMessage("JSON顶层字段：schema_version=1、pack_id、pack_revision、title、cards。\n每张卡包含稳定id、revision、path[科目,章节,考点]、title、question、answer、notes、source、content_status和order；type支持group/keypoint/essay。\n同ID更新内容时保留复习历史，正文变更会标记待复核。\n做题错题独立标记，不与背诵忘记／模糊混为一谈。")
                .setPositiveButton("知道了",null).show();
    }
    private void chooseImport(){
        Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("*/*");
        i.putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"application/json","application/zip","application/x-zip-compressed","application/octet-stream"});
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivityForResult(i,IMPORT);
    }
    private void chooseExport(boolean csv){
        Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType(csv?"text/csv":"application/json");
        String today=new SimpleDateFormat("yyyyMMdd-HHmm",Locale.US).format(new Date());
        i.putExtra(Intent.EXTRA_TITLE,csv?"政治背诵-进度-"+today+".csv":"政治背诵-完整备份-"+today+".json");
        startActivityForResult(i,csv?EXPORT_CSV:EXPORT_JSON);
    }
    @Override protected void onActivityResult(int req,int result,Intent data){
        super.onActivityResult(req,result,data);
        if(result!=RESULT_OK||data==null||data.getData()==null)return;
        Uri uri=data.getData();
        if(req==IMPORT){
            new Thread(()->{
                try(InputStream in=getContentResolver().openInputStream(uri)){
                    if(in==null)throw new IOException("无法读取文件");
                    String name="";
                    android.database.Cursor meta=getContentResolver().query(uri,new String[]{android.provider.OpenableColumns.DISPLAY_NAME},null,null,null);
                    if(meta!=null){try{if(meta.moveToFirst())name=meta.getString(0);}finally{meta.close();}}
                    StudyStore.ImportResult outcome;
                    if(name.toLowerCase(java.util.Locale.ROOT).endsWith(".zip")){
                        outcome=AudioZipImporter.importPack(this,in,store);
                    }else{
                        JSONObject obj=new JSONObject(StudyStore.readText(in,20*1024*1024));
                        outcome=store.importPayload(obj);
                    }
                    runOnUiThread(()->{catalogueFilter="";dailyGoal=parseGoal(store.setting("daily_goal","25"));showAnswer="true".equals(store.setting("show_answer","false"));switchTab(1);inform("导入完成："+outcome);});
                }catch(Exception e){runOnUiThread(()->error("导入失败（未写入半份资料）："+e.getMessage()));}
            }).start();
        }else if(req==EXPORT_JSON||req==EXPORT_CSV){
            new Thread(()->{
                try(OutputStream out=getContentResolver().openOutputStream(uri,"wt")){
                    if(out==null)throw new IOException("无法写入所选文件");
                    String value=req==EXPORT_JSON?store.backup().toString(2):exportCsv();
                    out.write(value.getBytes(StandardCharsets.UTF_8));out.flush();
                    runOnUiThread(()->inform("导出成功，可通过USB复制到电脑"));
                }catch(Exception e){runOnUiThread(()->error("导出失败："+e.getMessage()));}
            }).start();
        }
    }
    private static String csvQuote(String v){return "\""+(v==null?"":v).replace("\"","\"\"")+"\"";}
    private String exportCsv(){
        StringBuilder sb=new StringBuilder("\uFEFFid,pack_id,subject,chapter,topic,title,question,answer,notes,source,score,level,mastered,review_count,last_rating,last_review_at,due_at,needs_review,wrong_question\n");
        for(StudyCard c:store.allCards()){
            sb.append(csvQuote(c.id)).append(',').append(csvQuote(c.packId)).append(',')
                    .append(csvQuote(c.subject)).append(',').append(csvQuote(c.chapter)).append(',')
                    .append(csvQuote(c.topic)).append(',').append(csvQuote(c.displayTitle())).append(',')
                    .append(csvQuote(c.question)).append(',').append(csvQuote(c.answer)).append(',')
                    .append(csvQuote(c.notes)).append(',').append(csvQuote(c.source)).append(',').append(c.score).append(',')
                    .append(csvQuote(c.level())).append(',').append(c.mastered()).append(',')
                    .append(c.reviewCount).append(',').append(csvQuote(c.lastRating)).append(',')
                    .append(c.lastReviewAt).append(',').append(c.dueAt).append(',').append(c.needsReview).append(',').append(c.wrongQuestion).append('\n');
        }
        return sb.toString();
    }
    private void inform(String msg){new AlertDialog.Builder(this).setMessage(msg).setPositiveButton("好的",null).show();}
    private void error(String msg){new AlertDialog.Builder(this).setTitle("操作未完成").setMessage(msg).setPositiveButton("知道了",null).show();}
}