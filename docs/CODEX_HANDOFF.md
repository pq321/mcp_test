# Codex handoff / build & UX acceptance

This is a handoff note for an agent in a developer environment; do not add features to the MVP.

## Build

- Java 17, Android Gradle Plugin 8.7.3, Gradle 8.9, compile SDK 35, target SDK 34, minimum API 26.
- On GitHub Actions: run the provided `.github/workflows/build-apk.yml`; get `politics-memory-debug-apk` artifact.
- Local: Android SDK 35 and Gradle 8.9, `gradle --no-daemon :app:assembleDebug`.
- There is no Gradle wrapper in the source archive; GitHub Actions installs Gradle explicitly. Do not add internet permissions or analytics.

## Acceptance checklist (manual on Android 11 or later)

1. Launch offline. Starter contains exactly 93 cards, 7 chapters. All are immediately readable.
2. Review: LEFT swipe moves to previous card; RIGHT swipe moves to next card (note: intentionally reversed from conventional pagination). A vertical gesture scrolls an expanded long essay and must not flip cards.
3. Leave answers hidden, swipe three cards -> still hidden. Reveal, swipe three cards -> still revealed. Tap hide -> hidden across subsequent swipes.
4. Tap answer reveal, rate `不会`, `模糊`, `会了`. Confirm rating saves immediately and automatically advances. No rating occurs on swipe or reveal.
5. On the same date, repeatedly rate `会了` on the same card: familiarity must not progress beyond 2. On distinct dates, two successful reviews -> score 3, three -> score 4. `不会` resets to 0, `模糊` reduces 1 (min 1).
6. Force close/reopen: materials, ratings, familiarity, due dates remain intact. Airplane mode: all screens function.
7. Browse 3-level subject/chapter/topic progress. Coverage uses rated/total; mastery uses verified score >=3 and latest yes; average uses 0–4 score, not page position.
8. Export JSON via Android document picker to `Documents/`. Copy via USB. Use `scripts/inspect_backup.py`. CSV export opens in spreadsheet software.
9. Import the same sample JSON twice: no duplicates, no reset. Edit one card `answer` with incremented revision: review log preserved, changed card marked `待复核` until next rating. Restore an older backup: newer local reviews not overwritten.
10. Search a word/question/topic. Open the matching result and swipe within the results. Import 2nd subject package and verify independent progress.

## Perf acceptance

- A11 low/mid-range device: drag must follow touch with no full-screen refresh; keep scrolling fluid. If 5000+ cards make loading slow, optimize SQLite reads and visible-row rendering *before* adding any new feature.
- Recheck memory and size in actual compiled APK. Do not claim a measured APK size without the build artifact.

## Known scope boundaries

- Debug builds are not signed with an app-store production key. For long-term installation and updates, create and securely store one stable release keystore **outside** GitHub and outside this repository; use the same applicationId and signing key for upgrades. Never commit a private keystore.
- There is no automated PC-side synchronization. The phone exports a Codex-readable JSON/CSV file; copy via USB. No background network.
- Starter contains paraphrased compact K facts, not the user's F2 full mother templates. Import additional courses as separate packs and keep stable IDs.
- OCR/course-derived political materials may have transcription errors; verify fixed wordings against user-owned authoritative book. Do not infer exam frequency or automatically delete topics from absence in a course.
- Prioritize real-APK compilation and swipe behavior over new features. User requested a small, fast, minimal app.
