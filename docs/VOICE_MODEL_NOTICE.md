# Mandarin voice model notice

The build pipeline uses the single-speaker `zh_CN-chaowen-medium` Piper voice.

- Upstream voice repository: https://huggingface.co/rhasspy/piper-voices
- Pinned revision: `a60bfb1358818a92675b3a2d9d48fb8ea47035c1`
- Model directory: `zh/zh_CN/chaowen/medium/`
- Model card: https://huggingface.co/rhasspy/piper-voices/blob/a60bfb1358818a92675b3a2d9d48fb8ea47035c1/zh/zh_CN/chaowen/medium/MODEL_CARD
- The upstream repository metadata declares MIT. The Chaowen model card identifies its training dataset as CC0. These statements concern different components; neither should be treated as a blanket legal conclusion about every downstream use.
- Model file SHA-256 verified by CI: `820d64ac16048fbcf38dd0823d37fab5f5e0c2bd71b01ca5a50f553fac19e746`.

The ONNX model is downloaded only in CI and is not bundled into the APK or website. The project distributes MP3s synthesized from its own study-group text. No source-book scans, course recordings or instructor recordings are bundled.
