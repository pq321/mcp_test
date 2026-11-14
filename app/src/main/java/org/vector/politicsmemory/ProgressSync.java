package org.vector.politicsmemory;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONObject;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

/** Explicit, paired phone-to-computer upload. Never substitutes a local export for success. */
final class ProgressSync {
    private static SharedPreferences prefs(Context ctx){return ctx.getSharedPreferences("progress_sync",Context.MODE_PRIVATE);}
    static String saved(Context ctx){return prefs(ctx).getString("connection","");}
    static final class Connection {
        final String base,token;
        Connection(String b,String t){base=b;token=t;}
    }
    static Connection parse(String code) throws Exception {
        URI uri=new URI(code.trim());String host=uri.getHost(),scheme=uri.getScheme(),token=uri.getFragment();
        if(host==null||token==null||!token.matches("[0-9a-f]{64}")||uri.getUserInfo()!=null||uri.getQuery()!=null
                ||(uri.getPath()!=null&&!uri.getPath().isEmpty()&&!uri.getPath().equals("/")))
            throw new IllegalArgumentException("请粘贴电脑同步窗口显示的完整连接码");
        boolean local="localhost".equals(host)||"127.0.0.1".equals(host);
        if(host.matches("[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+")){
            String[] parts=host.split("\\.");int[] n=new int[4];
            for(int i=0;i<4;i++){n[i]=Integer.parseInt(parts[i]);if(n[i]>255)throw new IllegalArgumentException("电脑地址无效");}
            local=n[0]==10||n[0]==127||(n[0]==192&&n[1]==168)||(n[0]==172&&n[1]>=16&&n[1]<=31);
        }
        if(!"https".equals(scheme)&&!("http".equals(scheme)&&local))
            throw new IllegalArgumentException("普通HTTP只允许连接可信局域网电脑；公网地址必须使用HTTPS");
        return new Connection(new URI(scheme,null,host,uri.getPort(),null,null,null).toString(),token);
    }
    static int upload(Context ctx,String connection) throws Exception {
        Connection target=parse(connection);SharedPreferences saved=prefs(ctx);
        String device=saved.getString("device_id","");
        if(device.isEmpty()){device=UUID.randomUUID().toString();if(!saved.edit().putString("device_id",device).commit())throw new Exception("无法保存设备编号");}
        JSONObject payload;StudyStore store=new StudyStore(ctx);
        try{payload=store.progress(device);}finally{store.close();}
        String request=payload.getString("request_id");byte[] bytes=payload.toString().getBytes(StandardCharsets.UTF_8);
        HttpURLConnection http=(HttpURLConnection)new URL(target.base+"/api/progress").openConnection();
        try{
            http.setInstanceFollowRedirects(false);http.setConnectTimeout(6000);http.setReadTimeout(12000);
            http.setRequestMethod("POST");http.setRequestProperty("Authorization","Bearer "+target.token);
            http.setRequestProperty("Content-Type","application/json; charset=utf-8");http.setDoOutput(true);http.setFixedLengthStreamingMode(bytes.length);
            try(java.io.OutputStream out=http.getOutputStream()){out.write(bytes);}
            int code=http.getResponseCode();
            if(code==401)throw new Exception("电脑连接码已失效，请重新连接");
            if(code!=200)throw new Exception("电脑未确认保存（HTTP "+code+"），手机进度仍保留");
            JSONObject ack;try(InputStream in=http.getInputStream()){ack=new JSONObject(StudyStore.readText(in,32768));}
            if(!ack.optBoolean("ok")||!request.equals(ack.optString("request_id"))||!AudioCatalog.digest(bytes).equals(ack.optString("received_sha256")))
                throw new Exception("电脑保存回执不匹配，未确认同步成功");
            if(!saved.edit().putString("connection",connection.trim()).putLong("last_sync",ack.getLong("saved_at")).commit())
                throw new Exception("电脑已收到进度，但手机未能保存连接设置");
            return ack.getInt("review_count");
        }finally{http.disconnect();}
    }
}
