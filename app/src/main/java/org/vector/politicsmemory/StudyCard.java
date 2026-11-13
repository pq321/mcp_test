package org.vector.politicsmemory;

final class StudyCard {
    String id, packId, type, subject, chapter, topic, question, answer, source;
    int revision, order;
    int score, reviewCount;
    long dueAt, lastReviewAt;
    String lastRating = "", lastYesDay = "";
    boolean needsReview;

    boolean mastered() {
        return ReviewLogic.mastered(score, lastRating, needsReview);
    }
    String level() {
        return ReviewLogic.label(score, reviewCount, lastRating, needsReview);
    }
}
