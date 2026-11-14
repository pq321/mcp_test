# Codex handoff / PoliticsMemory v0.8

## Build environment

- Java 17, Android Gradle Plugin 8.7.3, Gradle 8.9, compile SDK 35, target SDK 34, minimum API 26.
- The canonical full pack is `data/suyi-full.json` (five subjects, 561 groups).
- `StudyStore.installStarterOnce()` expects the build pipeline to copy the canonical pack to `app/src/main/assets/suyi-full.json`.
- The offline audio manifest is `app/src/main/assets/audio-index.json`; MP3s live in `app/src/main/assets/audio/`.
- GitHub Actions `grouped-audio.yml` creates subject shards, merges them, validates text and MP3 hashes, builds the APK and deploys the web preview.

## Acceptance checklist

1. Install the debug APK offline. It must initialize all 561 groups and show only three bottom tabs: 复习、资料、统计.
2. Confirm the legacy 93 short-card pack is not mixed into the active catalogue. Its stored data must remain available in a full JSON backup.
3. Review page order: three-level location, group title, recall question, separator, full answer, optional tiny red note at the end.
4. LEFT swipe moves to previous group; RIGHT swipe moves to next group. Horizontal gestures animate and snap; vertical gestures scroll long answers without changing groups.
5. Reveal/hide persists across swipes. Rating uses 忘记／模糊／记住, saves immediately, and advances. Swipe/reveal alone never changes review score.
6. Select each speech rate 0.75×, 1.0×, 1.25×, 1.5×, 1.75× and 2.0×. Confirm rate changes current and subsequent playback and survives app restart.
7. Audio manifest covers exactly 561 IDs. Before playback, Android and web must verify the same canonical spoken text hash: path, title, question, answer and optional note. Any mismatch must be skipped/blocked.
8. Audio continues while screen is off; notification can pause, resume and stop. Test on a real Android device, not only emulator.
9. Mark a card as 做题错题. It must appear under 错题 without being conflated with 忘记／模糊. Removing the mark must remove it from that collection.
10. 时政 appears as an empty placeholder until user-provided material is imported. Never prefill current affairs from an unverified source.
11. Export/import full JSON. Preserve ratings, wrong IDs, review events, speed preference, group title and notes. Older restore data must not overwrite newer local review timestamps.
12. Web preview: all five subjects, 561 groups, localStorage persistence, backup export/import, swipe animation, speed selector and audio hash verification. Browser data must not be sent to any server.
13. Verify CI APK artifact and GitHub Pages deployment separately. CI compilation and emulator screenshots do not establish real-device fluidity or background audio reliability.

## Performance

Keep the interface compact and native. Avoid rebuilding the entire page during a drag; `SwipePagerLayout` should animate the current and incoming page. If 5,000+ groups are ever imported, optimize SQLite reads and visible-row rendering before adding features.

## Known scope boundaries

- No INTERNET permission, analytics SDK, ads, WebView, login or cloud progress sync.
- Web and Android progress are independent; transfer only through user-initiated JSON backup.
- Debug builds are not a production signing strategy. Any future stable release key must stay outside the repository and CI logs.
- OCR/course-derived content can still contain transcription errors. Do not claim full verbatim proofreading solely from 100% structural coverage.
