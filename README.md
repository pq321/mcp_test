# 政治背诵 | PoliticsMemory (offline Android)

A deliberately small **100% offline** Android app to memorize political-study material on a phone. No logins, WebView, ad SDKs, trackers, network permission or cloud backend. Modeled on the *interaction pattern* of a clean word-review app, without copying product branding or copyrighted graphical assets.

## What works in v0.3 source

- Full-screen swipe: **left = previous; right = next**, intentionally following the user's specified direction.
- Tap to reveal/hide answer; the answer visibility **persists across all swipes**.
- Three ratings: **不会 / 模糊 / 会了**. The phone immediately stores them in a local SQLite database.
- Familiarity 0–4: score ≥3 + latest `会了` on a **different calendar date** = mastered; repeated taps on one day cannot farm familiarity.
- Expandable three-level Su Yi-derived navigation: **科目 → 章节 → 考点 → 条目正文**. Each subject/chapter/topic has a play button, and each heading expands independently. The source pack keeps original item IDs so progress is preserved.
- **Bundled prerecorded Chinese MP3**: a build-time neural voice renders each question+answer, included in the APK. Tapping play starts the selected heading and continues; the foreground media notification supports screen-off playback and pause/resume/stop at the current position. No Android TTS voice installation is needed.
- Audio files are generated **once by GitHub Actions** using Piper 1.8 and the CC0-source Chinese `chaowen` model, then packaged into the APK. The phone never downloads a model, creates speech, or uses the network. Generated audio is MP3 rather than a copied course recording. Imported JSON with no corresponding audio remains usable for reading, not audio playback; a ZIP containing `pack.json` and matching `audio-index.json` + MP3 assets adds audio without reinstalling the app.
- Daily queue of due cards followed by new cards (default cap 25; configurable). Book/topic browsing is always available.
- Offline import from `.json`, transactional, duplicate-safe, stable card IDs. A content update retains review history; moving a card between headings does **not** flag it as forgotten, while changing the actual question or answer does require review.
- User-initiated export of full **JSON** backup + optional **CSV** report through Android's Documents picker. Codex reads the JSON directly.
- Built-in 93-card **思修重点K** starter pack reorganized into 36 nonempty Su Yi-style topics. Cards are concise paraphrased exam facts, not a copy of textbooks or proprietary courses. Missing topics are intentionally not inferred from a title.

## Build APK

Use GitHub Actions workflow **Build offline Android APK** and download artifact `politics-memory-debug-apk` → `app-debug.apk`.

With installed Android SDK 35, Java 17 and Gradle 8.9, first render MP3 audio using Piper and the `zh_CN-chaowen-medium` model (see workflow for download):

```bash
python scripts/generate_audio.py --pack app/src/main/assets/starter-sixiu-k.json --model .voice-cache/zh_CN-chaowen-medium.onnx --out app/src/main/assets
python scripts/validate_audio.py app/src/main/assets/starter-sixiu-k.json app/src/main/assets
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

## Prerecorded speech licensing and reproducibility

The build host downloads **Piper zh_CN-chaowen-medium** (source dataset license CC0 per its model card), generates 93 mono MP3 files and includes **only the MP3 clips** in the APK. The ~63 MB synthesis model does **not** ship. Audio generation needs network access on the build machine; **app runtime never does**. The generated files stay in the CI build artifact and are not committed as source. [Voice model card](https://huggingface.co/rhasspy/piper-voices/blob/main/zh/zh_CN/chaowen/medium/MODEL_CARD).

When updating an answer, rerun audio generation. The clip lookup verifies the exact question and answer SHA-256; an out-of-date clip is skipped rather than played incorrectly. For additional audio content import ZIP with `pack.json`, `audio-index.json` and the per-ID files under `audio/`, generated using `--zip`.
