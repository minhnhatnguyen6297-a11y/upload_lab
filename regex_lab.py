from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import extract_contract


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "regex_review_samples" / "input"
DEFAULT_CACHE = ROOT / "regex_review_samples" / "cache"
DEFAULT_GOLDEN = ROOT / "regex_review_samples" / "golden"
DEFAULT_PACKETS = ROOT / "regex_review_samples" / "packets"
EXTRACTION_FIELDS = (
    "document_kind",
    "ten_hop_dong",
    "nguoi_yeu_cau",
    "duong_su",
    "tai_san",
    "missing_fields",
    "error",
)


def _fold(value: str) -> str:
    value = unicodedata.normalize("NFD", str(value or ""))
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", value).strip().upper().replace("Đ", "D")


def _line_label(line: str) -> str:
    folded = _fold(line)
    if re.search(r"CONG HOA XA HOI CHU NGHIA VIET NAM|DOC LAP\s*[-–]", folded):
        return "TIEU_NGU"
    if re.fullmatch(r"[-=*_.~•\s]{3,}", line.strip()) or re.fullmatch(r"[-=*_.~\s]{3,}", folded):
        return "HOA_VAN"
    if re.search(r"\b(?:MA|M[ÃA])\s*(?:BIEU MAU|BM)\b|\bBM[.\s_-]*\d", folded):
        return "MA_BIEU_MAU"
    if re.search(r"VAN PHONG CONG CHUNG|PHONG CONG CHUNG", folded):
        return "VP_HEADER"
    if re.search(r"\bLOI CHUNG\b", folded):
        return "LOI_CHUNG"
    if re.search(r"\bSO\s*(?:CONG CHUNG|CC)\s*[:.]", folded):
        return "SO_CC"
    if re.match(r"^KINH GUI\b", folded):
        return "KINH_GUI"
    if re.match(r"^(?:HOM NAY|HOM,? NGAY)\b", folded):
        return "HOM_NAY"
    if re.match(r"^(?:CHUNG NHAN|CONG CHUNG VIEN CHUNG NHAN)\b", folded):
        return "CHUNG_NHAN"
    if re.search(r"CHUNG TOI GOM|CAC BEN GOM|TOI LA\s*:", folded):
        return "INTRO"
    if re.search(r"\bBEN\s+[AB]\b|NGUOI (?:TU CHOI|HUONG DI SAN)|CAC BEN THAM GIA", folded):
        return "PARTY_HDR"
    if re.match(r"^(?:ONG|BA|ANH|CHI|HO VA TEN|HO TEN)\s*[:.]", folded):
        return "PERSON"
    if re.match(r"^(?:DIEU|CHUONG)\s+(?:[IVXLCDM]+|\d+)", folded):
        return "DIEU"
    return "TEXT"


def layout_signature(text: str) -> str:
    labels = [_line_label(line) for line in str(text or "").splitlines() if line.strip()][:10]
    collapsed: list[str] = []
    for label in labels:
        if not collapsed or collapsed[-1] != label:
            collapsed.append(label)
    return ">".join(collapsed) or "EMPTY"


def cluster_id_for(signature: str) -> str:
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()[:12]


def _extractor_fingerprint() -> str:
    digest = hashlib.sha256()
    digest.update(Path(extract_contract.__file__).read_bytes())
    digest.update(Path(__file__).read_bytes())
    return digest.hexdigest()


def _json_read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _snapshot(payload: dict[str, Any] | None, error: str = "") -> dict[str, Any]:
    payload = payload or {}
    web = payload.get("web_form") or {}
    raw = payload.get("raw") or {}
    return {
        "document_kind": str(raw.get("document_kind") or ""),
        "ten_hop_dong": str(web.get("ten_hop_dong") or ""),
        "nguoi_yeu_cau": str(web.get("nguoi_yeu_cau") or ""),
        "duong_su": str(web.get("duong_su") or ""),
        "tai_san": str(web.get("tai_san") or ""),
        "missing_fields": list(raw.get("missing_web_form_fields") or []),
        "error": error,
    }


KIND_TITLE_TERMS = {
    "transfer_contract": ("CHUYEN NHUONG",),
    "gift_contract": ("TANG CHO",),
    "mortgage_contract": ("THE CHAP",),
    "asset_commitment": ("CAM KET", "TAI SAN RIENG"),
    "inheritance_partition": ("PHAN CHIA DI SAN",),
    "inheritance_refusal": ("TU CHOI", "DI SAN"),
    "transfer_cancellation": ("HUY BO", "CHUYEN NHUONG"),
}


def suspicion_flags(extraction: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    title = str(extraction.get("ten_hop_dong") or "")
    kind = str(extraction.get("document_kind") or "")
    asset = str(extraction.get("tai_san") or "")
    if not title.strip():
        flags.append("TITLE_EMPTY")
    expected = KIND_TITLE_TERMS.get(kind)
    folded_title = _fold(title)
    if expected and not all(term in folded_title for term in expected):
        flags.append("KIND_KHONG_KHOP_TITLE")
    if len(asset) > 2500:
        flags.append("TAI_SAN_QUA_DAI")
    folded_asset = _fold(asset)
    if re.search(r"\b(?:LOI CHUNG|SO CONG CHUNG)\b|\bDIEU\s+(?:[2-9]|[1-9]\d+)\b", folded_asset):
        flags.append("TAI_SAN_AN_LAN")
    if extraction.get("missing_fields") or any(
        not str(extraction.get(field) or "").strip()
        for field in ("ten_hop_dong", "nguoi_yeu_cau", "duong_su", "tai_san")
    ):
        flags.append("FIELD_RONG")
    if extraction.get("error"):
        flags.append("EXTRACT_ERROR")
    return flags


def _scan_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        return []
    return sorted(
        (
            path
            for path in input_dir.rglob("*")
            if path.is_file()
            and path.suffix.lower() in {".doc", ".docx"}
            and not path.name.startswith("~$")
        ),
        key=lambda path: path.relative_to(input_dir).as_posix().casefold(),
    )


def ingest_corpus(input_dir: Path | str = DEFAULT_INPUT, cache_dir: Path | str = DEFAULT_CACHE) -> dict[str, Any]:
    input_dir, cache_dir = Path(input_dir), Path(cache_dir)
    records_dir = cache_dir / "records"
    fingerprint = _extractor_fingerprint()
    records: dict[str, dict[str, Any]] = {}
    paths: dict[str, str] = {}
    reused_count = 0
    extracted_count = 0

    for path in _scan_files(input_dir):
        relative = path.relative_to(input_dir).as_posix()
        content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        cache_path = records_dir / f"{content_hash}.json"
        cached = _json_read(cache_path, {})
        if cached.get("content_hash") == content_hash and cached.get("extractor_fingerprint") == fingerprint:
            record = dict(cached)
            record["relative_path"] = relative
            reused_count += 1
        else:
            error = ""
            text = ""
            payload = None
            try:
                text = extract_contract.read_docx(
                    path, use_ifilter_for_doc=path.suffix.lower() == ".doc"
                )
                payload = extract_contract.extract(path, preloaded_text=text)
            except Exception as exc:  # A broken sample must remain reviewable.
                error = f"{type(exc).__name__}: {exc}"
            extraction = _snapshot(payload, error)
            kind_label = str(extraction.get("document_kind") or "unknown").upper()
            signature = f"{layout_signature(text)}>KIND_{kind_label}"
            record = {
                "content_hash": content_hash,
                "extractor_fingerprint": fingerprint,
                "relative_path": relative,
                "layout_signature": signature,
                "cluster_id": cluster_id_for(signature),
                "extraction": extraction,
                "flags": suspicion_flags(extraction),
                "source_lines": str(text or "").splitlines(),
            }
            _json_write(cache_path, record)
            extracted_count += 1
        # A hash can be referenced by several paths; keep the first path in the record.
        records.setdefault(content_hash, record)
        paths[relative] = content_hash

    clusters: dict[str, dict[str, Any]] = {}
    for relative, content_hash in paths.items():
        record = records[content_hash]
        cluster = clusters.setdefault(
            record["cluster_id"],
            {"signature": record["layout_signature"], "hashes": [], "paths": []},
        )
        if content_hash not in cluster["hashes"]:
            cluster["hashes"].append(content_hash)
        cluster["paths"].append(relative)

    flag_counts = Counter(flag for record in records.values() for flag in record.get("flags", []))
    index = {
        "version": 1,
        "extractor_fingerprint": fingerprint,
        "paths": paths,
        "records": records,
        "clusters": clusters,
        "summary": {
            "file_count": len(paths),
            "record_count": len(records),
            "cluster_count": len(clusters),
            "reused_count": reused_count,
            "extracted_count": extracted_count,
            "flag_counts": dict(sorted(flag_counts.items())),
        },
    }
    _json_write(cache_dir / "index.json", index)
    return index


def _golden_records(golden_dir: Path) -> dict[str, Any]:
    return _json_read(golden_dir / "index.json", {}).get("records", {})


def _changed(record: dict[str, Any], golden: dict[str, Any]) -> bool:
    return record.get("extraction", {}) != golden.get("extraction", {})


def _short(value: Any, limit: int = 700) -> str:
    text = json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else str(value or "")
    if len(text) <= limit:
        return text
    side = (limit - 25) // 2
    return f"{text[:side]}\n... [rut gon] ...\n{text[-side:]}"


def _excerpt(lines: list[str], limit: int = 45) -> str:
    populated = [(number, line) for number, line in enumerate(lines, 1) if line.strip()]
    shown = populated[:limit]
    body = "\n".join(f"{number:04d}: {line}" for number, line in shown)
    if len(populated) > limit:
        body += f"\n... ({len(populated) - limit} dong co noi dung khac)"
    return body


def review_corpus(
    input_dir: Path | str = DEFAULT_INPUT,
    cache_dir: Path | str = DEFAULT_CACHE,
    golden_dir: Path | str = DEFAULT_GOLDEN,
    packets_dir: Path | str = DEFAULT_PACKETS,
) -> dict[str, Any]:
    index = ingest_corpus(input_dir, cache_dir)
    golden = _golden_records(Path(golden_dir))
    golden_signatures = {item.get("layout_signature") for item in golden.values()}
    selected: list[tuple[str, list[str]]] = []
    for cluster_id, cluster in index["clusters"].items():
        hashes = cluster["hashes"]
        reasons: list[str] = []
        if cluster["signature"] not in golden_signatures:
            reasons.append("NEW_CLUSTER")
        if len(cluster["paths"]) == 1:
            reasons.append("OUTLIER_SIZE_1")
        if any(index["records"][item].get("flags") for item in hashes):
            reasons.append("HAS_FLAGS")
        if any(item in golden and _changed(index["records"][item], golden[item]) for item in hashes):
            reasons.append("CHANGED_VS_GOLDEN")
        if reasons:
            selected.append((cluster_id, reasons))

    run_dir = Path(packets_dir) / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_dir.mkdir(parents=True, exist_ok=False)
    index_lines = ["# Regex review packets", "", f"Selected clusters: {len(selected)}", ""]
    packet_paths: list[str] = []
    for cluster_id, reasons in selected:
        cluster = index["clusters"][cluster_id]
        hashes = sorted(
            cluster["hashes"],
            key=lambda item: (not bool(index["records"][item].get("flags")), index["records"][item]["relative_path"]),
        )[:3]
        packet_name = f"cluster-{cluster_id}.md"
        packet_paths.append(packet_name)
        index_lines.append(f"- [{cluster_id}]({packet_name}): {', '.join(reasons)}")
        lines = [
            f"# Cluster {cluster_id}", "", f"Reasons: {', '.join(reasons)}", "",
            f"Signature: `{cluster['signature']}`", "", f"Files: {len(cluster['paths'])}; unique hashes: {len(cluster['hashes'])}", "",
        ]
        for content_hash in hashes:
            record = index["records"][content_hash]
            lines.extend([f"## {record['relative_path']}", "", f"Hash: `{content_hash}`", "", f"Flags: {', '.join(record.get('flags') or ['NONE'])}", "", "### Extraction", ""])
            for field in EXTRACTION_FIELDS:
                lines.extend([f"- `{field}`: {_short(record['extraction'].get(field))}", ""])
            lines.extend(["### Source excerpt", "", "```text", _excerpt(record.get("source_lines", [])), "```", ""])
        (run_dir / packet_name).write_text("\n".join(lines), encoding="utf-8")
    (run_dir / "index.md").write_text("\n".join(index_lines), encoding="utf-8")
    return {"packet_dir": str(run_dir), "selected_cluster_count": len(selected), "packets": packet_paths, "index": index}


def approve_corpus(
    input_dir: Path | str = DEFAULT_INPUT,
    cache_dir: Path | str = DEFAULT_CACHE,
    golden_dir: Path | str = DEFAULT_GOLDEN,
    *,
    approve_all: bool = False,
    cluster_id: str | None = None,
) -> dict[str, Any]:
    if approve_all == bool(cluster_id):
        raise ValueError("Require exactly one of approve_all or cluster_id")
    index = ingest_corpus(input_dir, cache_dir)
    if cluster_id and cluster_id not in index["clusters"]:
        raise ValueError(f"Unknown cluster: {cluster_id}")
    hashes = list(index["records"]) if approve_all else index["clusters"][cluster_id]["hashes"]
    golden_path = Path(golden_dir) / "index.json"
    payload = _json_read(golden_path, {"version": 1, "records": {}})
    records = payload.setdefault("records", {})
    for content_hash in hashes:
        current = index["records"][content_hash]
        records[content_hash] = {
            "relative_path": current["relative_path"],
            "layout_signature": current["layout_signature"],
            "cluster_id": current["cluster_id"],
            "extraction": current["extraction"],
        }
    payload["approved_at"] = datetime.now().isoformat(timespec="seconds")
    _json_write(golden_path, payload)
    return {"approved_count": len(hashes), "golden_path": str(golden_path)}


def verify_corpus(
    input_dir: Path | str = DEFAULT_INPUT,
    cache_dir: Path | str = DEFAULT_CACHE,
    golden_dir: Path | str = DEFAULT_GOLDEN,
) -> dict[str, Any]:
    index = ingest_corpus(input_dir, cache_dir)
    golden = _golden_records(Path(golden_dir))
    results: list[dict[str, Any]] = []
    counts = Counter()
    for content_hash, record in index["records"].items():
        if content_hash not in golden:
            status = "NEW"
        elif _changed(record, golden[content_hash]):
            status = "CHANGED"
        else:
            status = "UNCHANGED"
        counts[status] += 1
        results.append({"content_hash": content_hash, "relative_path": record["relative_path"], "status": status})
    for content_hash, record in golden.items():
        if content_hash in index["records"]:
            continue
        counts["REMOVED"] += 1
        results.append(
            {
                "content_hash": content_hash,
                "relative_path": record.get("relative_path", ""),
                "status": "REMOVED",
            }
        )
    report = {
        "summary": {name: counts[name] for name in ("NEW", "UNCHANGED", "CHANGED", "REMOVED")},
        "results": results,
        "exit_code": 1 if counts["CHANGED"] or counts["REMOVED"] else 0,
    }
    report_path = Path(cache_dir) / "verify-report.json"
    report["report_path"] = str(report_path)
    _json_write(report_path, report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agent-driven regex extraction review lab")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("ingest", "review", "verify", "approve"):
        command = subparsers.add_parser(name)
        command.add_argument("--input", type=Path, default=DEFAULT_INPUT)
        command.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
        if name in {"review", "verify", "approve"}:
            command.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
        if name == "review":
            command.add_argument("--packets", type=Path, default=DEFAULT_PACKETS)
        if name == "approve":
            group = command.add_mutually_exclusive_group(required=True)
            group.add_argument("--all", action="store_true", dest="approve_all")
            group.add_argument("--cluster")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "ingest":
        result = ingest_corpus(args.input, args.cache)
        output = result["summary"]
    elif args.command == "review":
        result = review_corpus(args.input, args.cache, args.golden, args.packets)
        output = {key: value for key, value in result.items() if key != "index"}
    elif args.command == "approve":
        output = approve_corpus(args.input, args.cache, args.golden, approve_all=args.approve_all, cluster_id=args.cluster)
    else:
        output = verify_corpus(args.input, args.cache, args.golden)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return int(output.get("exit_code", 0))


if __name__ == "__main__":
    sys.exit(main())
