# Political study pack JSON v1

The pack is UTF-8 JSON and does not depend on a server, Markdown renderer or external account.

## Study materials

```json
{
  "schema_version": 1,
  "pack_id": "politics-suyi-full",
  "pack_revision": 7,
  "title": "苏一全科成组背诵",
  "cards": [
    {
      "id": "suyi-001-example",
      "revision": 1,
      "path": ["马原", "第一章", "考点一"],
      "type": "group",
      "title": "知识点名称",
      "question": "需要回忆的问题？",
      "answer": "完整成组答案。",
      "notes": "腿姐背诵技巧",
      "source": "苏一正文印刷第1页",
      "content_status": "STRUCTURED_TEXT_REORGANIZED",
      "order": 1
    }
  ]
}
```

- `path` has exactly three nonempty strings: subject, chapter and topic.
- `title` is the display name of the whole group. If omitted, the app falls back to `path[2]`.
- `question` is the recall prompt shown between the title and separator.
- `answer` is the complete grouped knowledge content; preserve internal line breaks.
- `notes` is optional, rendered in tiny red text at the end. Only include attributed teacher tips when the source supports the attribution.
- `type` accepts `group`, `keypoint` or `essay`. The Su Yi full pack uses `group`.
- `source` and `content_status` describe provenance and processing state. Do not interpret a status of `STRUCTURED_TEXT_REORGANIZED` as verbatim proofreading.
- `pack_id` identifies a package. `pack_revision` is monotonically nondecreasing.
- Each `id` is globally stable across imports. Never reuse an ID for a different fact. Each card `revision` increases when factual text changes.
- `order` sorts cards within their topic. Imports never delete existing cards; reimport is idempotent.
- Changes to question or answer preserve review history but mark the card for review. Changes to title, path, note or source are metadata-only.

## Audio contract

Each card receives one generated MP3. The audio says, in order: knowledge-point location, group title, recall question, full answer and optional note. The text checksum is SHA-256 of the exact canonical text joined with newline characters:

```text
知识点位置。科目，章节，考点
知识点名称。标题
问题。问题正文
答案。完整答案
备注。可选备注
```

The `audio-index.json` item stores `file`, `text_sha256`, `audio_sha256` and `size_bytes`. Android and web verify the text hash before playback. A changed title, question, answer or note invalidates the old recording; mismatched audio is never played.

## Backup and progress

Android JSON backup contains all packs, review records, event history, `wrong_ids` and local settings. The old 93-card starter pack remains in backups but is hidden from the active 561-group catalogue. Web progress is browser-local and exported as JSON; it is not automatically synchronized with Android.

Familiarity remains 0–4. 忘记 resets to 0; 模糊 reduces one level (minimum 1); 记住 progresses across different calendar dates. Merely opening an answer or swiping does not affect score. 做题错题 is an independent manual mark, not inferred from a poor recall rating.
