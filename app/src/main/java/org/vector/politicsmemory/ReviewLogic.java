package org.vector.politicsmemory;

import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.Locale;

/** Simple, inspectable familiarity rule. No black-box predicted memory percentages. */
public final class ReviewLogic {
    private ReviewLogic() {}
    public static final class Result {
        public final int score;
        public final long dueAt;
        public final String lastYesDay;
        Result(int score, long dueAt, String lastYesDay) {
            this.score = score;
            this.dueAt = dueAt;
            this.lastYesDay = lastYesDay;
        }
    }
    public static String localDay(long epochMillis) {
        return new SimpleDateFormat("yyyyMMdd", Locale.US).format(new Date(epochMillis));
    }
    public static Result rate(int score, String lastYesDay, String rating, long nowMillis) {
        score = Math.max(0, Math.min(4, score));
        if (lastYesDay == null) lastYesDay = "";
        switch (rating) {
            case "no":
                return new Result(0, nowMillis + 10L * 60L * 1000L, lastYesDay);
            case "fuzzy":
                return new Result(Math.max(1, score - 1), plusDays(nowMillis, 1), lastYesDay);
            case "yes": {
                String day = localDay(nowMillis);
                // Repeat taps on the same calendar date cannot farm mastery levels.
                int newScore = day.equals(lastYesDay) ? Math.max(2, score)
                        : Math.min(4, Math.max(2, score + 1));
                int days = newScore == 2 ? 1 : newScore == 3 ? 3 : 7;
                return new Result(newScore, plusDays(nowMillis, days), day);
            }
            default:
                throw new IllegalArgumentException("Unknown rating: " + rating);
        }
    }
    public static long plusDays(long epochMillis, int days) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(epochMillis);
        c.add(Calendar.DATE, days);
        return c.getTimeInMillis();
    }
    public static boolean mastered(int score, String lastRating, boolean needsReview) {
        return score >= 3 && "yes".equals(lastRating) && !needsReview;
    }
    public static String label(int score, int reviewCount, String lastRating, boolean needsReview) {
        if (reviewCount == 0) return "未学";
        if (needsReview) return "待复核";
        if ("no".equals(lastRating)) return "不会";
        if ("fuzzy".equals(lastRating)) return "模糊";
        if (score >= 4) return "牢固";
        if (score == 3) return "掌握";
        return "熟悉";
    }
}
