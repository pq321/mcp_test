# 政治背诵 | PoliticsMemory (offline Android)

A deliberately small **100% offline** Android app to memorize political-study material on a phone. No logins, WebView, ad SDKs, trackers, network permission or cloud backend. Modeled on the *interaction pattern* of a clean word-review app, without copying product branding or copyrighted graphical assets.

## What works in v0.2 source

- Full-screen swipe: **left = previous; right = next**, intentionally following the user's specified direction.
- Tap to reveal/hide answer; the answer visibility **persists across all swipes**.
- Three ratings: **不会 / 模糊 / 会了**. The phone immediately stores them in a local SQLite database.
- Familiarity 0–4: score ≥3 + latest `会了` on a **different calendar date** = mastered; repeated taps on one day cannot farm familiarity.
- Expandable three-level Su Yi-derived navigation: **科目 → 章节 → 考点 → 条目正文**. Each subject/chapter/topic has a play button, and each heading expands independently. The source pack keeps original item IDs so progress is preserved.
- **Offline system Chinese TTS**: play the selected heading and keep reading subsequent items, or play the home review queue. A foreground media notification supports background/screen-off reading and pause/resume/stop (resume repeats the current item).
- The Android system must already have a **downloaded offline Chinese voice**. The app never fetches voice data. Emulator audio cannot substitute for real-phone audio verification.
- Daily queue of due cards followed by new cards (default cap 25; configurable). Book/topic browsing is always available.
- Offline import from `.json`, transactional, duplicate-safe, stable card IDs. A content update retains review history; moving a card between headings does **not** flag it as forgotten, while changing the actual question or answer does require review.
- User-initiated export of full **JSON** backup + optional **CSV** report through Android's Documents picker. Codex reads the JSON directly.
- Built-in 93-card **思修重点K** starter pack reorganized into 36 nonempty Su Yi-style topics. Cards are concise paraphrased exam facts, not a copy of textbooks or proprietary courses. Missing topics are intentionally not inferred from a title.

## Build APK

Use GitHub Actions workflow **Build offline Android APK** and download artifact `politics-memory-debug-apk` → `app-debug.apk`.

With installed Android SDK 35, Java 17 and Gradle 8.9:

```bash
gradle --no-daemon :app:assembleDebug
```

Output: `app/build/outputs/apk/debug/app-debug.apk`.

No Gradle wrapper binary is included; the GitHub workflow installs Gradle explicitly.

**A debug APK is suitable for trying the app, but not a release-signing strategy.** Keep one stable signing certificate for eventual long-term updates; do not store it in source control.

## Android phone / PC workflow

1. Install the APK; open with airplane mode enabled, no account needed.
2. Use **复习** or select a subject/chapter/topic in **资料**.
3. Tap to reveal answer, rate and swipe. Progress autosaves on device.
4. Choose **我的 → 导出完整备份（JSON）** → save into local `Documents/政治背诵-完整备份-....json`.
5. Connect USB → choose File Transfer → copy that file to computer. Codex can read it directly, or run `python3 scripts/inspect_backup.py <backup.json>`.
6. To add source material, write a JSON `cards` pack with three-part `path`; import via **我的 → 导入素材或备份**.

See [data format and exact scheduling](docs/data-format.md) and [Codex build/QA handoff](docs/CODEX_HANDOFF.md).

## Privacy

Source code contains only generic source facts and a sample pack. Real user progress remains in phone-local SQLite. App disables Android automatic backup and does not request Internet access.

## Caution

GitHub Actions builds the APK, and a separate emulator screenshot workflow is available. **Compilation and emulator screenshots do not establish real-device fluidity or background audio reliability**; confirm those on the target Android phone. Debug builds may use different signing certificates on separate runners. Back up progress before uninstalling an older debug APK, and use a stable private signing key for future long-term updates.
