---
name: regex-review
description: Use when reviewing extract_contract.py regex output, regex review samples, layout clusters, or generated regex_lab.py packets for extraction regressions.
---

# Regex Review

Review is agent-driven and local. Do not use an API client, API key, or upload sample content.

1. Run `./.venv/Scripts/python.exe ./regex_lab.py ingest`, then `./.venv/Scripts/python.exe ./regex_lab.py review`.
2. Read the newest `regex_review_samples/packets/<timestamp>/index.md` first. Open only the selected packet files needed for the review; never load the full corpus into context.
3. Compare extraction values with the numbered source excerpt. Cite the file, source line number, extracted field, and exact evidence.
4. Classify each finding as `SAI_LOAI`, `CAT_THUA`, `CAT_THIEU`, `THEM_TU`, or `SAI_NGUOI`.
5. Preserve source wording. Never invent absent facts, normalize names/addresses/identifiers, or silently correct the document.
6. Propose or implement the smallest regex fix and run relevant tests plus `./.venv/Scripts/python.exe ./regex_lab.py verify` after edits.
7. Never run `approve` automatically. A human must inspect evidence and explicitly choose `approve --cluster <id>` or `approve --all`.

Packets may contain PII. Quote only the minimum evidence and do not send it to external services.

After creating or changing this skill, restart OpenCode so it is discovered.
