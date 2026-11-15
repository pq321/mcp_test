package org.vector.politicsmemory;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/** Single-file SQLite database; imports/backup use platform JSON, no network dependency. */
final class StudyStore extends SQLiteOpenHelper {
    static final String DB = "politics-memory.db";
    static final int SCHEMA = 3;
    final Context context;

    StudyStore(Context ctx) { super(ctx, DB, null, SCHEMA); context = ctx.getApplicationContext(); }

    @Override public void onConfigure(SQLiteDatabase db) {
        super.onConfigure(db);
        db.enableWriteAheadLogging();
    }
    @Override public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE packs (id TEXT PRIMARY KEY, title TEXT NOT NULL, rev INTEGER NOT NULL, imported_at INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE cards (id TEXT PRIMARY KEY, pack_id TEXT NOT NULL, rev INTEGER NOT NULL, subject TEXT NOT NULL, chapter TEXT NOT NULL, topic TEXT NOT NULL, type TEXT NOT NULL, question TEXT NOT NULL, answer TEXT NOT NULL, source TEXT NOT NULL, pos INTEGER NOT NULL, title TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', content_status TEXT NOT NULL DEFAULT '', retired INTEGER NOT NULL DEFAULT 0)");
        db.execSQL("CREATE INDEX cards_path ON cards(subject,chapter,topic,pos,id)");
        db.execSQL("CREATE TABLE reviews (card_id TEXT PRIMARY KEY, score INTEGER NOT NULL DEFAULT 0, review_count INTEGER NOT NULL DEFAULT 0, due_at INTEGER NOT NULL DEFAULT 0, last_review_at INTEGER NOT NULL DEFAULT 0, last_rating TEXT NOT NULL DEFAULT '', last_yes_day TEXT NOT NULL DEFAULT '', needs_review INTEGER NOT NULL DEFAULT 0)");
        db.execSQL("CREATE INDEX reviews_due ON reviews(due_at)");
        db.execSQL("CREATE TABLE events (id TEXT PRIMARY KEY, card_id TEXT NOT NULL, rating TEXT NOT NULL, score_before INTEGER NOT NULL, score_after INTEGER NOT NULL, at INTEGER NOT NULL)");
        db.execSQL("CREATE INDEX events_by_card ON events(card_id,at)");
        db.execSQL("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)");
        db.execSQL("CREATE TABLE wrong_cards (card_id TEXT PRIMARY KEY, marked_at INTEGER NOT NULL)");
    }
    @Override public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        // Additive migration only: keep every existing rating, event and setting.
        if (oldVersion < 2) {
            db.execSQL("ALTER TABLE cards ADD COLUMN title TEXT NOT NULL DEFAULT ''");
            db.execSQL("ALTER TABLE cards ADD COLUMN notes TEXT NOT NULL DEFAULT ''");
            db.execSQL("ALTER TABLE cards ADD COLUMN content_status TEXT NOT NULL DEFAULT ''");
            db.execSQL("CREATE TABLE IF NOT EXISTS wrong_cards (card_id TEXT PRIMARY KEY, marked_at INTEGER NOT NULL)");
        }
        if(oldVersion<3)db.execSQL("ALTER TABLE cards ADD COLUMN retired INTEGER NOT NULL DEFAULT 0");
    }

    static String readText(InputStream in, int maxBytes) throws IOException {
        try (InputStream stream = in; ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192]; int n; int total=0;
            while ((n = stream.read(buffer)) != -1) {
                total += n;
                if (total > maxBytes) throw new IOException("文件超过限制，请分包导入（上限 " + (maxBytes/1024/1024) + "MB）");
                out.write(buffer,0,n);
            }
            return out.toString(StandardCharsets.UTF_8.name());
        }
    }
    /** Install the complete five-subject Su Yi pack; never delete ratings from older packs. */
    void installStarterOnce() throws IOException, JSONException {
        try (InputStream in = context.getAssets().open("suyi-full.json")) {
            JSONObject pack=new JSONObject(readText(in,20*1024*1024));
            String id=pack.getString("pack_id");int incoming=pack.getInt("pack_revision");
            int existing=0;
            try(Cursor cur=getReadableDatabase().rawQuery("SELECT rev FROM packs WHERE id=?",new String[]{id})){
                if(cur.moveToFirst())existing=cur.getInt(0);
            }
            if(incoming>existing)importPayload(pack);
        }
    }
    int countCards() {
        try(Cursor c=getReadableDatabase().rawQuery("SELECT COUNT(*) FROM cards",null)) { c.moveToFirst(); return c.getInt(0); }
    }

    static final class ImportResult {
        int added, updated, unchanged, skipped, restored, removed;
        @Override public String toString() {
            return "新增 " + added + "，更新 " + updated + "，未变 " + unchanged + "，跳过旧版 " + skipped + (restored>0?"，恢复进度 "+restored:"") + (removed>0?"，停用 "+removed:"");
        }
    }
    ImportResult importPayload(JSONObject root) throws JSONException {
        if ("politics-memory-backup".equals(root.optString("kind"))) return restore(root);
        Pack pack = validatePack(root);
        SQLiteDatabase db=getWritableDatabase();
        ImportResult result=new ImportResult();
        db.beginTransaction();
        try { mergePack(db,pack,result); db.setTransactionSuccessful(); }
        finally { db.endTransaction(); }
        return result;
    }

    private static final class Pack {
        String id, title;
        int revision;
        ArrayList<StudyCard> cards = new ArrayList<>();
    }
    private static String required(JSONObject o,String key,int maxLen) throws JSONException {
        if (!o.has(key) || o.isNull(key)) throw new JSONException("缺少字段 " + key);
        String v=o.getString(key).trim();
        if(v.isEmpty() || v.length()>maxLen) throw new JSONException("字段 " + key + " 不能为空或超出长度 " + maxLen);
        return v;
    }
    private static Pack validatePack(JSONObject obj) throws JSONException {
        if(obj.optInt("schema_version",-1)!=1) throw new JSONException("不支持的数据格式版本（需要 schema_version:1）");
        Pack pack=new Pack();
        pack.id=required(obj,"pack_id",80);
        if(!pack.id.matches("[A-Za-z0-9._-]+")) throw new JSONException("pack_id 仅允许字母、数字、点、下划线、横线");
        pack.title=obj.optString("title",pack.id).trim();
        if(pack.title.isEmpty()) pack.title=pack.id;
        pack.revision=obj.optInt("pack_revision",1);
        if(pack.revision<1) throw new JSONException("pack_revision 应大于零");
        JSONArray array=obj.getJSONArray("cards");
        if(array.length()==0||array.length()>20000) throw new JSONException("单包条目数应在1至20000之间");
        Set<String> unique=new HashSet<>();
        for(int i=0;i<array.length();i++) {
            JSONObject item=array.getJSONObject(i); StudyCard c=new StudyCard();
            c.id=required(item,"id",128);
            if(!c.id.matches("[A-Za-z0-9._-]+")) throw new JSONException("卡片ID格式错误: "+c.id);
            if(!unique.add(c.id)) throw new JSONException("重复卡片ID："+c.id);
            c.packId=pack.id; c.revision=item.optInt("revision",1);
            if(c.revision<1) throw new JSONException("revision 必须为正数: "+c.id);
            JSONArray path=item.getJSONArray("path");
            if(path.length()!=3) throw new JSONException("path必须刚好包含三级：科目、章节、考点: "+c.id);
            c.subject=path.getString(0).trim(); c.chapter=path.getString(1).trim(); c.topic=path.getString(2).trim();
            if(c.subject.isEmpty()||c.chapter.isEmpty()||c.topic.isEmpty()) throw new JSONException("三级标题不能为空: "+c.id);
            if(c.subject.length()>60||c.chapter.length()>80||c.topic.length()>100) throw new JSONException("标题过长: "+c.id);
            c.type=item.optString("type","keypoint");
            if(!"keypoint".equals(c.type)&&!"essay".equals(c.type)&&!"group".equals(c.type)) throw new JSONException("未知卡片类型: "+c.type);
            c.title=item.optString("title",c.topic).trim();
            if(c.title.isEmpty()) c.title=c.topic;
            c.question=required(item,"question",1500);
            c.answer=required(item,"answer",25000);
            c.notes=item.optString("notes","").trim();
            c.source=item.optString("source","").trim();
            c.contentStatus=item.optString("content_status","").trim();
            if(c.source.length()>500||c.notes.length()>1000||c.contentStatus.length()>100) throw new JSONException("备注或来源字段过长: "+c.id);
            c.order=item.optInt("order",i+1);
            pack.cards.add(c);
        }
        return pack;
    }
    private static ContentValues cardValues(StudyCard c) {
        ContentValues v=new ContentValues();
        v.put("id",c.id);v.put("pack_id",c.packId);v.put("rev",c.revision);
        v.put("subject",c.subject);v.put("chapter",c.chapter);v.put("topic",c.topic);
        v.put("type",c.type);v.put("question",c.question);v.put("answer",c.answer);
        v.put("source",c.source);v.put("pos",c.order);v.put("title",c.title==null?"":c.title);
        v.put("notes",c.notes==null?"":c.notes);v.put("content_status",c.contentStatus==null?"":c.contentStatus);v.put("retired",0);
        return v;
    }
    private static void mergePack(SQLiteDatabase db,Pack pack,ImportResult out) throws JSONException {
        int latest=0;
        try(Cursor pc=db.rawQuery("SELECT rev FROM packs WHERE id=?",new String[]{pack.id})){
            if(pc.moveToFirst()) latest=pc.getInt(0);
        }
        if(pack.revision<latest) throw new JSONException("这是旧版素材包；现有包版本"+latest+"，导入版本"+pack.revision);
        // New revision is authoritative. A removed card is archived, NOT deleted:
        // historical ratings/events remain intact, and a later release can restore it.
        if(latest>0 && pack.revision>latest){
            try(Cursor existing=db.rawQuery("SELECT COUNT(*) FROM cards WHERE pack_id=? AND retired=0",new String[]{pack.id})){
                if(existing.moveToFirst())out.removed=existing.getInt(0);
            }
            ContentValues retired=new ContentValues();retired.put("retired",1);
            db.update("cards",retired,"pack_id=?",new String[]{pack.id});
        }
        int remainingAfterRetire=0;
        for(StudyCard card:pack.cards){
            try(Cursor c=db.rawQuery("SELECT pack_id,rev,subject,chapter,topic,type,question,answer,source,pos,title,notes,content_status FROM cards WHERE id=?",new String[]{card.id})){
                if(!c.moveToFirst()) {
                    db.insertOrThrow("cards",null,cardValues(card)); out.added++;
                    continue;
                }
                if(!pack.id.equals(c.getString(0))) throw new JSONException("卡片ID与其他素材包冲突："+card.id);
                int existingRev=c.getInt(1);
                if(card.revision<existingRev){
                    // Do not archive a newer existing card due to stale per-card metadata.
                    ContentValues active=new ContentValues();active.put("retired",0);
                    db.update("cards",active,"id=?",new String[]{card.id});
                    remainingAfterRetire++;out.skipped++;continue;
                }
                boolean semanticChanged=!card.type.equals(c.getString(5))||!card.question.equals(c.getString(6))||!card.answer.equals(c.getString(7));
                boolean metadataChanged=!card.subject.equals(c.getString(2))||!card.chapter.equals(c.getString(3))
                        ||!card.topic.equals(c.getString(4))||!card.source.equals(c.getString(8))||card.order!=c.getInt(9)
                        ||!safe(card.title).equals(c.getString(10))||!safe(card.notes).equals(c.getString(11))
                        ||!safe(card.contentStatus).equals(c.getString(12));
                if(!semanticChanged && !metadataChanged && card.revision==existingRev){
                    ContentValues active=new ContentValues();active.put("retired",0);
                    db.update("cards",active,"id=?",new String[]{card.id});
                    remainingAfterRetire++;out.unchanged++;continue;
                }
                db.update("cards",cardValues(card),"id=?",new String[]{card.id});
                if(semanticChanged){
                    ContentValues rv=new ContentValues();rv.put("needs_review",1);rv.put("due_at",System.currentTimeMillis());
                    db.update("reviews",rv,"card_id=?",new String[]{card.id});
                }
                remainingAfterRetire++;out.updated++;
            }
        }
        // Count only cards actually hidden after this revision, not temporarily retired.
        if(pack.revision>latest && latest>0){
            try(Cursor archived=db.rawQuery("SELECT COUNT(*) FROM cards WHERE pack_id=? AND retired=1",new String[]{pack.id})){
                if(archived.moveToFirst())out.removed=archived.getInt(0);
            }
        }
        ContentValues pv=new ContentValues();pv.put("id",pack.id);pv.put("title",pack.title);pv.put("rev",pack.revision);pv.put("imported_at",System.currentTimeMillis());
        db.insertWithOnConflict("packs",null,pv,SQLiteDatabase.CONFLICT_REPLACE);
    }

    private static String safe(String s){return s==null?"":s;}
    ArrayList<StudyCard> allCards() {
        ArrayList<StudyCard> list=new ArrayList<>();
        // The retired 93 short-card starter pack stays in backups but is not mixed into the 561 grouped cards.
        String sql="SELECT c.id,c.pack_id,c.rev,c.subject,c.chapter,c.topic,c.type,c.question,c.answer,c.source,c.pos,c.title,c.notes,c.content_status,"+
                "COALESCE(r.score,0),COALESCE(r.review_count,0),COALESCE(r.due_at,0),COALESCE(r.last_review_at,0),"+
                "COALESCE(r.last_rating,''),COALESCE(r.last_yes_day,''),COALESCE(r.needs_review,0),CASE WHEN w.card_id IS NULL THEN 0 ELSE 1 END "+
                "FROM cards c LEFT JOIN reviews r ON r.card_id=c.id LEFT JOIN wrong_cards w ON w.card_id=c.id "+
                "WHERE c.retired=0 AND c.pack_id!='politics-sixiu-k' ORDER BY CASE WHEN c.pack_id='politics-suyi-full' THEN 0 ELSE 1 END,c.pack_id,c.pos,c.id";
        try(Cursor c=getReadableDatabase().rawQuery(sql,null)){
            while(c.moveToNext()) {
                StudyCard a=new StudyCard();
                a.id=c.getString(0);a.packId=c.getString(1);a.revision=c.getInt(2);
                a.subject=c.getString(3);a.chapter=c.getString(4);a.topic=c.getString(5);
                a.type=c.getString(6);a.question=c.getString(7);a.answer=c.getString(8);
                a.source=c.getString(9);a.order=c.getInt(10);a.title=c.getString(11);a.notes=c.getString(12);a.contentStatus=c.getString(13);
                a.score=c.getInt(14);a.reviewCount=c.getInt(15);a.dueAt=c.getLong(16);a.lastReviewAt=c.getLong(17);
                a.lastRating=c.getString(18);a.lastYesDay=c.getString(19);a.needsReview=c.getInt(20)!=0;a.wrongQuestion=c.getInt(21)!=0;
                list.add(a);
            }
        }
        return list;
    }
    StudyCard findCard(List<StudyCard> all,String id) {
        for(StudyCard c:all) if(c.id.equals(id)) return c;
        return null;
    }
    boolean isWrong(String id) {
        try(Cursor c=getReadableDatabase().rawQuery("SELECT 1 FROM wrong_cards WHERE card_id=?",new String[]{id})) { return c.moveToFirst(); }
    }
    void setWrong(String id,boolean marked) {
        SQLiteDatabase db=getWritableDatabase();
        if(marked){ContentValues v=new ContentValues();v.put("card_id",id);v.put("marked_at",System.currentTimeMillis());db.insertWithOnConflict("wrong_cards",null,v,SQLiteDatabase.CONFLICT_REPLACE);}
        else db.delete("wrong_cards","card_id=?",new String[]{id});
        try{
            JSONObject changes=new JSONObject(setting("wrong_sync_changes","{}"));
            changes.put(id,new JSONObject().put("marked",marked).put("at",System.currentTimeMillis()));
            saveSetting("wrong_sync_changes",changes.toString());
        }catch(JSONException e){throw new IllegalStateException(e);}
    }
    ArrayList<StudyCard> wrongCards() {
        ArrayList<StudyCard> out=new ArrayList<>();for(StudyCard c:allCards())if(c.wrongQuestion)out.add(c);return out;
    }
    ArrayList<StudyCard> weakCards() {
        ArrayList<StudyCard> out=new ArrayList<>();for(StudyCard c:allCards())if("no".equals(c.lastRating)||"fuzzy".equals(c.lastRating))out.add(c);return out;
    }

    void rate(String id,String rating) {
        if(!"yes".equals(rating)&&!"no".equals(rating)&&!"fuzzy".equals(rating)) throw new IllegalArgumentException("rating");
        SQLiteDatabase db=getWritableDatabase();long now=System.currentTimeMillis();
        db.beginTransaction();
        try {
            int score=0,reviewCount=0;String lastYesDay="";
            try(Cursor c=db.rawQuery("SELECT score,review_count,last_yes_day FROM reviews WHERE card_id=?",new String[]{id})){
                if(c.moveToFirst()) {score=c.getInt(0);reviewCount=c.getInt(1);lastYesDay=c.getString(2);}
            }
            try(Cursor exists=db.rawQuery("SELECT 1 FROM cards WHERE id=?",new String[]{id})){
                if(!exists.moveToFirst()) throw new IllegalArgumentException("不存在的卡片："+id);
            }
            ReviewLogic.Result calc=ReviewLogic.rate(score,lastYesDay,rating,now);
            ContentValues r=new ContentValues();r.put("card_id",id);r.put("score",calc.score);
            r.put("review_count",reviewCount+1);r.put("due_at",calc.dueAt);r.put("last_review_at",now);
            r.put("last_rating",rating);r.put("last_yes_day",calc.lastYesDay);r.put("needs_review",0);
            db.insertWithOnConflict("reviews",null,r,SQLiteDatabase.CONFLICT_REPLACE);
            ContentValues event=new ContentValues();event.put("id",UUID.randomUUID().toString());
            event.put("card_id",id);event.put("rating",rating);event.put("score_before",score);
            event.put("score_after",calc.score);event.put("at",now);
            db.insertOrThrow("events",null,event);
            db.setTransactionSuccessful();
        }finally{db.endTransaction();}
    }
    void saveSetting(String key,String value) {
        ContentValues v=new ContentValues();v.put("key",key);v.put("value",value);
        getWritableDatabase().insertWithOnConflict("settings",null,v,SQLiteDatabase.CONFLICT_REPLACE);
    }
    String setting(String key,String fallback) {
        try(Cursor c=getReadableDatabase().rawQuery("SELECT value FROM settings WHERE key=?",new String[]{key})) {
            return c.moveToFirst()?c.getString(0):fallback;
        }
    }

    /** Progress only: no materials, audio, connection credentials, or unrelated settings. */
    JSONObject progress(String deviceId) throws JSONException {
        JSONObject source=backup();JSONObject out=new JSONObject();
        out.put("schema_version",1);out.put("kind","politics-memory-progress");
        out.put("request_id",UUID.randomUUID().toString());out.put("device_id",deviceId);out.put("sent_at",System.currentTimeMillis());
        out.put("reviews",source.getJSONArray("reviews"));out.put("events",source.getJSONArray("events"));
        JSONObject changes=new JSONObject(setting("wrong_sync_changes","{}"));
        try(Cursor c=getReadableDatabase().rawQuery("SELECT card_id,marked_at FROM wrong_cards",null)){
            while(c.moveToNext())if(!changes.has(c.getString(0)))changes.put(c.getString(0),new JSONObject().put("marked",true).put("at",c.getLong(1)));
        }
        out.put("wrong_changes",changes);
        String id=setting("last_card_id","");
        if(!id.isEmpty())out.put("cursor",new JSONObject().put("card_id",id).put("updated_at",Long.parseLong(setting("last_card_at","0"))));
        return out;
    }

    /** Import only progress; do not delete local ratings or alter materials.
     *  The union is verified by the provider before this transaction starts.
     */
    void mergeRemoteProgress(JSONObject state) throws JSONException {
        if(!"politics-memory-progress".equals(state.optString("kind"))||state.optInt("schema_version")!=1)
            throw new JSONException("云端进度格式不兼容");
        JSONArray reviews=state.optJSONArray("reviews"),events=state.optJSONArray("events");
        if(reviews==null||events==null||reviews.length()>10000||events.length()>100000)
            throw new JSONException("同步记录数量或结构异常");
        SQLiteDatabase db=getWritableDatabase();db.beginTransaction();
        try {
            for(int i=0;i<reviews.length();i++){
                JSONObject src=reviews.getJSONObject(i);String id=required(src,"card_id",128);
                try(Cursor exists=db.rawQuery("SELECT 1 FROM cards WHERE id=?",new String[]{id})){
                    if(!exists.moveToFirst())continue;
                }
                long timestamp=src.optLong("last_review_at");
                long local=-1;boolean needs=false;
                try(Cursor r=db.rawQuery("SELECT last_review_at,needs_review FROM reviews WHERE card_id=?",new String[]{id})){
                    if(r.moveToFirst()){local=r.getLong(0);needs=r.getInt(1)!=0;}
                }
                if(timestamp<0||timestamp<local)continue;
                ContentValues v=new ContentValues();v.put("card_id",id);v.put("score",Math.max(0,Math.min(4,src.optInt("score"))));
                v.put("review_count",Math.max(0,src.optInt("review_count")));v.put("due_at",Math.max(0,src.optLong("due_at")));
                v.put("last_review_at",timestamp);String rating=src.optString("last_rating","");
                if(!rating.isEmpty()&&!"yes".equals(rating)&&!"no".equals(rating)&&!"fuzzy".equals(rating))throw new JSONException("评级不合法");
                v.put("last_rating",rating);v.put("last_yes_day",src.optString("last_yes_day",""));
                v.put("needs_review",(needs||src.optBoolean("needs_review",false))?1:0);
                db.insertWithOnConflict("reviews",null,v,SQLiteDatabase.CONFLICT_REPLACE);
            }
            for(int i=0;i<events.length();i++){
                JSONObject e=events.getJSONObject(i);ContentValues v=new ContentValues();
                v.put("id",required(e,"id",128));v.put("card_id",required(e,"card_id",128));
                String rating=required(e,"rating",8);
                if(!"yes".equals(rating)&&!"no".equals(rating)&&!"fuzzy".equals(rating))throw new JSONException("事件评级非法");
                v.put("rating",rating);v.put("score_before",e.optInt("score_before"));
                v.put("score_after",e.optInt("score_after"));v.put("at",e.optLong("at"));
                db.insertWithOnConflict("events",null,v,SQLiteDatabase.CONFLICT_IGNORE);
            }
            JSONObject incoming=state.optJSONObject("wrong_changes");
            JSONObject changes=new JSONObject(setting("wrong_sync_changes","{}"));
            if(incoming!=null)for(java.util.Iterator<String> keys=incoming.keys();keys.hasNext();){
                String id=keys.next();JSONObject mark=incoming.getJSONObject(id);
                if(!changes.has(id)||mark.optLong("at")>changes.getJSONObject(id).optLong("at")){
                    changes.put(id,mark);
                    if(mark.optBoolean("marked")){
                        ContentValues v=new ContentValues();v.put("card_id",id);v.put("marked_at",mark.optLong("at"));
                        db.insertWithOnConflict("wrong_cards",null,v,SQLiteDatabase.CONFLICT_REPLACE);
                    }else db.delete("wrong_cards","card_id=?",new String[]{id});
                }
            }
            ContentValues flags=new ContentValues();flags.put("key","wrong_sync_changes");flags.put("value",changes.toString());
            db.insertWithOnConflict("settings",null,flags,SQLiteDatabase.CONFLICT_REPLACE);
            JSONObject cursor=state.optJSONObject("cursor");
            if(cursor!=null && cursor.has("card_id") && cursor.optLong("updated_at")>Long.parseLong(setting("last_card_at","0"))){
                ContentValues id=new ContentValues();id.put("key","last_card_id");id.put("value",cursor.getString("card_id"));
                db.insertWithOnConflict("settings",null,id,SQLiteDatabase.CONFLICT_REPLACE);
                ContentValues at=new ContentValues();at.put("key","last_card_at");at.put("value",Long.toString(cursor.optLong("updated_at")));
                db.insertWithOnConflict("settings",null,at,SQLiteDatabase.CONFLICT_REPLACE);
            }
            db.setTransactionSuccessful();
        }finally{db.endTransaction();}
    }

    /** Codex-friendly backup: a single UTF-8 JSON containing full materials and rating log. */
    JSONObject backup() throws JSONException {
        SQLiteDatabase db=getReadableDatabase();
        JSONObject out=new JSONObject();out.put("schema_version",1);out.put("kind","politics-memory-backup");
        out.put("exported_at",System.currentTimeMillis());
        JSONArray packages=new JSONArray();
        try(Cursor p=db.rawQuery("SELECT id,title,rev FROM packs ORDER BY id",null)){
            while(p.moveToNext()){
                JSONObject pack=new JSONObject();pack.put("schema_version",1);pack.put("pack_id",p.getString(0));
                pack.put("title",p.getString(1));pack.put("pack_revision",p.getInt(2));
                JSONArray cards=new JSONArray();
                try(Cursor c=db.rawQuery("SELECT id,rev,subject,chapter,topic,type,question,answer,source,pos,title,notes,content_status FROM cards WHERE pack_id=? ORDER BY pos,id",new String[]{p.getString(0)})){
                    while(c.moveToNext()){
                        JSONObject x=new JSONObject();x.put("id",c.getString(0));x.put("revision",c.getInt(1));
                        x.put("path",new JSONArray().put(c.getString(2)).put(c.getString(3)).put(c.getString(4)));
                        x.put("type",c.getString(5));x.put("question",c.getString(6));x.put("answer",c.getString(7));
                        x.put("source",c.getString(8));x.put("order",c.getInt(9));x.put("title",c.getString(10));
                        x.put("notes",c.getString(11));x.put("content_status",c.getString(12));cards.put(x);
                    }
                }
                pack.put("cards",cards);packages.put(pack);
            }
        }
        out.put("packs",packages);
        JSONArray reviews=new JSONArray();
        try(Cursor c=db.rawQuery("SELECT card_id,score,review_count,due_at,last_review_at,last_rating,last_yes_day,needs_review FROM reviews ORDER BY card_id",null)) {
            while(c.moveToNext()) {
                JSONObject x=new JSONObject();x.put("card_id",c.getString(0));x.put("score",c.getInt(1));
                x.put("review_count",c.getInt(2));x.put("due_at",c.getLong(3));x.put("last_review_at",c.getLong(4));
                x.put("last_rating",c.getString(5));x.put("last_yes_day",c.getString(6));x.put("needs_review",c.getInt(7)!=0);
                reviews.put(x);
            }
        }
        out.put("reviews",reviews);
        JSONArray wrongIds=new JSONArray();
        try(Cursor c=db.rawQuery("SELECT card_id FROM wrong_cards ORDER BY card_id",null)){while(c.moveToNext())wrongIds.put(c.getString(0));}
        out.put("wrong_ids",wrongIds);
        JSONArray events=new JSONArray();
        try(Cursor c=db.rawQuery("SELECT id,card_id,rating,score_before,score_after,at FROM events ORDER BY at,id",null)) {
            while(c.moveToNext()) {
                JSONObject x=new JSONObject();x.put("id",c.getString(0));x.put("card_id",c.getString(1));x.put("rating",c.getString(2));
                x.put("score_before",c.getInt(3));x.put("score_after",c.getInt(4));x.put("at",c.getLong(5));events.put(x);
            }
        }
        out.put("events",events);
        JSONObject settings=new JSONObject();
        try(Cursor c=db.rawQuery("SELECT key,value FROM settings ORDER BY key",null)) {
            while(c.moveToNext()) settings.put(c.getString(0),c.getString(1));
        }
        out.put("settings",settings);
        return out;
    }
    private ImportResult restore(JSONObject backup) throws JSONException {
        if(backup.optInt("schema_version",-1)!=1) throw new JSONException("备份版本不兼容");
        JSONArray packs=backup.getJSONArray("packs");
        if(packs.length()>1000) throw new JSONException("备份素材包数量异常");
        ArrayList<Pack> parsed=new ArrayList<>();
        for(int i=0;i<packs.length();i++) parsed.add(validatePack(packs.getJSONObject(i)));
        JSONArray reviews=backup.optJSONArray("reviews");JSONArray events=backup.optJSONArray("events");
        JSONArray wrongIds=backup.optJSONArray("wrong_ids");JSONObject settings=backup.optJSONObject("settings");
        SQLiteDatabase db=getWritableDatabase();ImportResult result=new ImportResult();
        db.beginTransaction();
        try {
            for(Pack pack:parsed) mergePack(db,pack,result);
            if(reviews!=null) for(int i=0;i<reviews.length();i++) {
                JSONObject src=reviews.getJSONObject(i);
                String id=required(src,"card_id",128);
                long timestamp=src.optLong("last_review_at",0);
                if(timestamp<0) throw new JSONException("时间错误："+id);
                try(Cursor exists=db.rawQuery("SELECT 1 FROM cards WHERE id=?",new String[]{id})){
                    if(!exists.moveToFirst()) continue;
                }
                long current=-1;boolean localNeedsReview=false;
                try(Cursor cur=db.rawQuery("SELECT last_review_at,needs_review FROM reviews WHERE card_id=?",new String[]{id})){
                    if(cur.moveToFirst()) {current=cur.getLong(0);localNeedsReview=cur.getInt(1)!=0;}
                }
                // Keep the newer rating. Restoring stale files will not erase recent practice.
                if(current>timestamp) continue;
                ContentValues rv=new ContentValues();rv.put("card_id",id);
                rv.put("score",Math.min(4,Math.max(0,src.optInt("score",0))));
                rv.put("review_count",Math.max(0,src.optInt("review_count",0)));
                rv.put("due_at",Math.max(0,src.optLong("due_at",0)));
                rv.put("last_review_at",timestamp);
                String lastRating=src.optString("last_rating","");
                if(!lastRating.isEmpty()&&!"yes".equals(lastRating)&&!"no".equals(lastRating)&&!"fuzzy".equals(lastRating)) throw new JSONException("备份评级错误");
                rv.put("last_rating",lastRating);rv.put("last_yes_day",src.optString("last_yes_day",""));
                // Respect the local modified-content flag; backup progress must not silently clear it.
                rv.put("needs_review",(localNeedsReview||src.optBoolean("needs_review",false))?1:0);
                db.insertWithOnConflict("reviews",null,rv,SQLiteDatabase.CONFLICT_REPLACE);
                result.restored++;
            }
            if(wrongIds!=null) for(int i=0;i<wrongIds.length();i++){
                String id=wrongIds.getString(i);
                try(Cursor exists=db.rawQuery("SELECT 1 FROM cards WHERE id=?",new String[]{id})){
                    if(exists.moveToFirst()){ContentValues w=new ContentValues();w.put("card_id",id);w.put("marked_at",System.currentTimeMillis());db.insertWithOnConflict("wrong_cards",null,w,SQLiteDatabase.CONFLICT_IGNORE);}
                }
            }
            if(events!=null) for(int i=0;i<events.length();i++){
                JSONObject src=events.getJSONObject(i);ContentValues ev=new ContentValues();
                ev.put("id",required(src,"id",128));ev.put("card_id",required(src,"card_id",128));
                String rt=required(src,"rating",8);
                if(!"yes".equals(rt)&&!"no".equals(rt)&&!"fuzzy".equals(rt)) throw new JSONException("事件评级错误");
                ev.put("rating",rt);ev.put("score_before",src.optInt("score_before",0));
                ev.put("score_after",src.optInt("score_after",0));ev.put("at",src.optLong("at",0));
                db.insertWithOnConflict("events",null,ev,SQLiteDatabase.CONFLICT_IGNORE);
            }
            if(settings!=null) {
                java.util.Iterator<String> keys=settings.keys();
                while(keys.hasNext()) {
                    String key=keys.next();
                    // Settings with UX scope only; unknown keys are skipped.
                    if(!"daily_goal".equals(key)&&!"show_answer".equals(key)&&!"speech_speed".equals(key)) continue;
                    ContentValues sv=new ContentValues();sv.put("key",key);sv.put("value",settings.optString(key,""));
                    db.insertWithOnConflict("settings",null,sv,SQLiteDatabase.CONFLICT_REPLACE);
                }
            }
            db.setTransactionSuccessful();
        }finally{db.endTransaction();}
        return result;
    }
}