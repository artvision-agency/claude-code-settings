---
name: find-client-files
description: Find local and Google Drive files belonging to a client without loading large file contents into context. Use automatically when the user asks in Russian or English to find, show, locate, or recover a client's latest files, commercial proposals or КП, audits, reports, presentations, HTML mockups, statistics, contracts, or related deliverables; also use for phrases such as "что делали для клиента", "где аудит", "покажи последние файлы", and "смотри на компе/диске".
---

# Find client files

## Workflow

1. Derive a compact case-insensitive regex containing likely spelling variants of the client name. Keep the query broad enough for transliteration and spacing differences.
2. Run `scripts/find-client-files '<regex>'`. This returns only metadata and paths; do not print matching file contents.
3. Classify likely deliverables from filenames: КП/proposal, audit/analysis, report/statistics, mockup/landing, spreadsheet, or source data.
4. If the user mentions Drive, cloud, presentations, documents, or a file is not found locally, search Google Drive using short client-name queries. Do not enable best-effort content fetch during initial discovery.
5. Inspect content only for a few grounded candidates and only as much as needed to identify them.
6. Return clickable local paths and observed Drive URLs, sorted newest first. State clearly when a local result is only an `.icloud` placeholder.

## Context discipline

- Never send full HTML, CSV, JSON, base64, or spreadsheet dumps to the model during discovery.
- Cap terminal results with `head` when the match set is large.
- Prefer filename, modification time, size, title, and URL.
- Do not claim that a file is the requested artifact until its name or a bounded content check supports that conclusion.
