package org.vector.politicsmemory;

import android.content.Context;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewConfiguration;
import android.view.ViewGroup;
import android.view.animation.DecelerateInterpolator;
import android.widget.FrameLayout;

/**
 * Full-width drag-follow pager without third-party UI dependencies.
 * User's exact mapping: swipe LEFT -> previous; swipe RIGHT -> next.
 * Y-direction scrolls go to the nested ScrollView.
 */
final class SwipePagerLayout extends FrameLayout {
    interface PageFactory { View build(int index); }
    interface PageListener { void onPage(int index); }
    private final int slop;
    private final PageFactory factory;
    private final PageListener listener;
    private int count,index,neighborIndex=-1;
    private View current,neighbor;
    private float downX,downY;
    private boolean dragging=false,animating=false;

    SwipePagerLayout(Context context,int count,int start,PageFactory factory,PageListener listener){
        super(context);
        this.count=count;this.index=start;this.factory=factory;this.listener=listener;
        slop=ViewConfiguration.get(context).getScaledTouchSlop();
        setClipChildren(true);
        current=factory.build(index);addView(current,new LayoutParams(-1,-1));
    }
    int index(){return index;}
    void refresh(){
        if(animating||dragging) return;
        if(neighbor!=null){removeView(neighbor);neighbor=null;neighborIndex=-1;}
        removeView(current);current=factory.build(index);addView(current,new LayoutParams(-1,-1));
    }
    @Override public boolean onInterceptTouchEvent(MotionEvent event) {
        if(animating) return true;
        switch(event.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
                downX=event.getX();downY=event.getY();dragging=false;return false;
            case MotionEvent.ACTION_MOVE:
                float dx=event.getX()-downX,dy=event.getY()-downY;
                if(Math.abs(dx)>slop && Math.abs(dx)>Math.abs(dy)*1.30f){
                    dragging=true;getParent().requestDisallowInterceptTouchEvent(true);return true;
                }
                break;
        }
        return false;
    }
    @Override public boolean onTouchEvent(MotionEvent event){
        if(animating) return true;
        switch(event.getActionMasked()){
            case MotionEvent.ACTION_DOWN:
                downX=event.getX();downY=event.getY();return true;
            case MotionEvent.ACTION_MOVE:
                float dx=event.getX()-downX,dy=event.getY()-downY;
                if(!dragging && Math.abs(dx)>slop && Math.abs(dx)>Math.abs(dy)*1.3f) dragging=true;
                if(dragging) move(dx);
                return true;
            case MotionEvent.ACTION_CANCEL:
            case MotionEvent.ACTION_UP:
                if(dragging) finishDrag(event.getX()-downX,event.getActionMasked()==MotionEvent.ACTION_CANCEL);
                dragging=false;
                return true;
        }
        return true;
    }
    private void ensureNeighbor(int target,int dir,int width){
        if(neighborIndex==target&&neighbor!=null)return;
        if(neighbor!=null){removeView(neighbor);neighbor=null;}
        neighborIndex=target;
        neighbor=factory.build(target);
        addView(neighbor,0,new LayoutParams(-1,-1));
        neighbor.setTranslationX(-dir*width);
    }
    private void move(float dx){
        int width=Math.max(1,getWidth());
        int dir=dx>=0?1:-1; // +1 right gesture -> next; -1 left gesture -> previous
        int target=index+dir;
        if(target<0||target>=count){
            if(neighbor!=null){removeView(neighbor);neighbor=null;neighborIndex=-1;}
            current.setTranslationX(dx*0.15f);return;
        }
        ensureNeighbor(target,dir,width);
        float clipped=Math.max(-width,Math.min(width,dx));
        current.setTranslationX(clipped);
        neighbor.setTranslationX(clipped-dir*width);
    }
    private void finishDrag(float dx,boolean cancelled){
        if(neighbor==null){current.animate().translationX(0).setDuration(160).setInterpolator(new DecelerateInterpolator()).start();return;}
        boolean commit=!cancelled&&Math.abs(dx)>=getWidth()*0.22f;
        if(!commit){
            View out=neighbor;int dir=dx>=0?1:-1;
            current.animate().translationX(0).setDuration(170).start();
            out.animate().translationX(-dir*getWidth()).setDuration(170).withEndAction(()->{
                if(out.getParent()==this)removeView(out);
                if(neighbor==out){neighbor=null;neighborIndex=-1;}
            }).start();
            return;
        }
        int dir=dx>=0?1:-1;
        completeSwipe(dir);
    }
    private void completeSwipe(int dir){
        if(neighbor==null||animating)return;
        animating=true;
        View old=current;View incoming=neighbor;int target=neighborIndex;
        current.animate().translationX(dir*getWidth()).setInterpolator(new DecelerateInterpolator()).setDuration(150).start();
        incoming.animate().translationX(0).setInterpolator(new DecelerateInterpolator()).setDuration(150).withEndAction(()->{
            if(old.getParent()==this)removeView(old);
            current=incoming;neighbor=null;neighborIndex=-1;index=target;animating=false;
            listener.onPage(index);
        }).start();
    }
    void advanceAfterRating(){
        if(animating||dragging)return;
        if(index+1>=count){listener.onPage(index);return;}
        ensureNeighbor(index+1,1,Math.max(1,getWidth()));
        completeSwipe(1);
    }
}
