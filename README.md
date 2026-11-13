# 政治背诵 | PoliticsMemory (offline Android)

A deliberately small **100% offline** Android app to memorize political-study material on a phone. No logins, WebView, ad SDKs, trackers, network permission or cloud backend. Modeled on the *interaction pattern* of a clean word-review app, without copying product branding or copyrighted graphical assets.

## What works in v0.1 source

- Full-screen swipe: **left = previous; right = next**, intentionally following the user's specified direction.
- Tap to reveal/hide answer; the answer visibility **persists across all swipes**.
- Three ratings: **不会 / 模糊 / 会了**. The phone immediately stores them in a local SQLite database.
- Familiarity 0–4: score ≥3 + latest `会了` on a **different calendar date** = mastered; repeated taps on one day cannot farm familiarity.
- Three-level navigation: **科目 → 章节 → 考点**, with coverage, mastery and familiarity.
- Daily queue of due cards followed by new cards (default cap 25; configurable). Book/topic browsing is always available.
- Offline import from `.json`, transactional, duplicate-safe, stable card IDs. A content update retains review history but flags material changes for review.
- User-initiated export of full **JSON** backup + optional **CSV** report through Android's Documents picker. Codex reads the JSON directly.
- Built-in 93-card **思修重点K** starter pack. Cards are concise paraphrased exam facts, not a copy of textbooks or proprietary courses.

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

Source created in a limited environment without a preinstalled Android SDK; GitHub Actions compilation and real-device touch tests must complete before this is called a verified working APK. See Codex handoff for acceptance criteria.
