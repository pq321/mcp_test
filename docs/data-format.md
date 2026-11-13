# Political study pack JSON v1

This schema is intentionally simple and does not depend on a server, Markdown renderer, or external accounts.

## Study materials

UTF-8 `.json` with top-level object:

```json
{
  "schema_version": 1,
  "pack_id": "politics-sixiu-k",
  "pack_revision": 2,
  "title": "思修重点K",
  "cards": [
    {
      "id": "sixiu-law-system-004",
      "revision": 2,
      "path": ["思修", "07 法律", "考点6 法治体系"],
      "type": "keypoint",
      "question": "建设中国特色社会主义法治体系的重点是什么？",
      "answer": "高效的法治实施体系。",
      "source": "苏一思维导图第132页",
      "order": 4
    }
  ]
}
```

- `path` **must** have exactly 3 nonempty strings: **subject, chapter, topic**. Each is a heading; the card is the question-answer item at the topic level.
- `type` is `keypoint` or `essay`. Essays use the same ID and fields; answers may have paragraphs separated by `\n`.
- `pack_id` identifies a package (letters, numbers, `_`, `-`, `.`, 1–80 chars).
- `pack_revision` is a monotonically nondecreasing package revision. Older packages are rejected.
- Each `id` is globally stable across all imports and packages (letters, numbers, `_`, `-`, `.`, max 128). **Never reuse an ID for a different fact**. It is the join key between content and study records.
- Each card `revision` starts from 1, increases when its factual text changes, and is never reduced by an import.
- `order` is an integer used to sort within a topic. All other ordering is fixed by the lexical chapter labels (`01 ...`, `02 ...`).
- Imports **never delete** existing cards. Reimporting the exact same file is idempotent.
- Material changes (question/answer/path/type/source/order) retain old review history, but require a new review (`needs_review=true`), so a changed answer cannot silently retain its old mastered status.
- All imports are parsed and validated before database modification and then applied in one SQLite transaction.
- Maximum file size is 20 MiB; split larger content by subject or chapter. Max 20,000 cards per pack.

## App-created backup

Export a single JSON file via the Android system document picker. The backup root is:

```json
{
  "kind": "politics-memory-backup",
  "schema_version": 1,
  "exported_at": 1794600000000,
  "packs": [ { "schema_version": 1, "pack_id": "...", "pack_revision": 1, "title": "...", "cards": [] } ],
  "reviews": [ {
    "card_id": "sixiu-law-system-004",
    "score": 3,
    "review_count": 2,
    "due_at": 1794859200000,
    "last_review_at": 1794600000000,
    "last_rating": "yes",
    "last_yes_day": "20261113",
    "needs_review": false
  } ],
  "events": [ { "id": "uuid", "card_id": "...", "rating": "yes", "score_before": 2, "score_after": 3, "at": 1794600000000 } ]
}
```

Time fields are Unix milliseconds. `last_yes_day` is the phone's **local calendar date** (`yyyyMMdd`). The whole backup is intentionally plain JSON so **Codex can read it with no special database driver**. You can also export a UTF-8-with-BOM CSV progress report, which is compatible with Excel/VS Code.

When restoring a backup, newer local rating timestamps win. The event log is deduplicated by event UUID. Restore is transactional; it never deletes cards. A content-change flag is preserved while restoring older practice records.

## Familiarity algorithm

- Unseen: `review_count=0` (score 0, *未学*).
- **不会 (`no`)**: score **0**; due in 10 minutes.
- **模糊 (`fuzzy`)**: score `max(1,score-1)`; due after one local day.
- **会了 (`yes`)**: score is at least 2 on the first successful review; another `yes` on a different calendar date raises score by 1 to a maximum of 4. Repeated `yes` on the same date does not increase the score.
- Score **2**: familiar, due next day; **3**: mastered, due in 3 days; **4**: stable, due in 7 days.
- *Mastered* means `score >= 3`, latest rating is `yes`, and `needs_review` is false. Merely opening an answer or swiping a page does **not** change familiarity.
- Chapter/topic/subject coverage = rated cards / total; mastered rate = mastered cards / total; average familiarity = sum(score)/total, on a 0–4 scale.
- `fuzzy` or `no` breaks the latest-mastered marker even if historical successes remain in `events`.

## Offline-only data policy

AndroidManifest intentionally does not request `android.permission.INTERNET` and disables system automatic backup. Data never leaves the phone until the user explicitly exports using Android's document picker. The app never uses a cloud account, advertising, analytics SDK or WebView.

## Usage examples

```bash
python3 scripts/validate_pack.py data/starter-sixiu-k.json
python3 scripts/inspect_backup.py '政治背诵-完整备份-20261114-0004.json'
```
