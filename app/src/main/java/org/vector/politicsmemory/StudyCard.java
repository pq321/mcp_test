package org.vector.politicsmemory;

final class StudyCard {
    String id, packId, type, subject, chapter, topic, title, question, answer, notes, source, contentStatus;
    int revision, order;
    int score, reviewCount;
    long dueAt, lastReviewAt;
    String lastRating = "", lastYesDay = "";
    boolean needsReview, wrongQuestion;

    String displayTitle() {
        return title == null || title.trim().isEmpty() ? topic : title;
    }
    boolean mastered() {
        return ReviewLogic.mastered(score, lastRating, needsReview);
    }
    String level() {
        return ReviewLogic.label(score, reviewCount, lastRating, needsReview);
    }
}
