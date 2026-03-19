#!/usr/bin/env python3
"""Migrate registry/storage from local models to hosted defaults.

What this script does:
1. Rewrites default text/image models to Hugging Face hosted providers.
2. Removes local-model registry rows (provider=local, local source, or local_path).
3. Deletes local model files/directories to reclaim disk space.
4. Clears 3D default unless an explicit hosted 3D default is requested.

Notes:
- Hosted 3D generation is currently not implemented by the backend adapter.
  If you set a hosted 3D default, requests may still fail at runtime.
- Run with --dry-run first.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy import delete, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm_api.config import get_settings
from llm_api.db.database import get_db_session, init_db
from llm_api.db.models import DefaultModelRecord, ModelRecord


@dataclass
class PlannedDelete:
    path: Path
    reason: str


@dataclass
class LocalModelSnapshot:
    id: str
    local_path: Optional[str]
    provider: Optional[str]
    source_type: Optional[str]


def _derive_name(model_id: str) -> str:
    tail = model_id.split("/")[-1]
    return tail.replace("-", " ").replace("_", " ").strip() or model_id


def _upsert_hosted_model(model_id: str, modality: str) -> None:
    with get_db_session() as db:
        row = db.get(ModelRecord, model_id)
        if row is None:
            row = ModelRecord(
                id=model_id,
                name=_derive_name(model_id),
                version="latest",
                modality=modality,
            )
        row.provider = "huggingface"
        row.status = "available"
        row.local_path = None
        row.size_bytes = None
        row.source_type = "huggingface"
        row.source_uri = model_id
        db.add(row)


def _set_default(modality: str, model_id: str) -> None:
    with get_db_session() as db:
        existing = db.get(DefaultModelRecord, modality)
        if existing:
            existing.model_id = model_id
            db.add(existing)
        else:
            db.add(DefaultModelRecord(modality=modality, model_id=model_id))


def _delete_default(modality: str) -> None:
    with get_db_session() as db:
        existing = db.get(DefaultModelRecord, modality)
        if existing:
            db.delete(existing)


def _collect_local_model_rows() -> list[LocalModelSnapshot]:
    with get_db_session() as db:
        rows = db.execute(select(ModelRecord)).scalars().all()
        local_rows: list[LocalModelSnapshot] = []
        for row in rows:
            is_local_provider = (row.provider or "").lower() == "local"
            is_local_source = (row.source_type or "").lower() == "local"
            has_local_path = bool(row.local_path)
            if is_local_provider or is_local_source or has_local_path:
                local_rows.append(
                    LocalModelSnapshot(
                        id=row.id,
                        local_path=row.local_path,
                        provider=row.provider,
                        source_type=row.source_type,
                    )
                )
        return local_rows


def _delete_local_model_rows(keep_ids: set[str]) -> int:
    with get_db_session() as db:
        rows = db.execute(select(ModelRecord)).scalars().all()
        to_delete_ids: list[str] = []
        for row in rows:
            if row.id in keep_ids:
                continue
            is_local_provider = (row.provider or "").lower() == "local"
            is_local_source = (row.source_type or "").lower() == "local"
            has_local_path = bool(row.local_path)
            if is_local_provider or is_local_source or has_local_path:
                to_delete_ids.append(row.id)

        if to_delete_ids:
            db.execute(delete(ModelRecord).where(ModelRecord.id.in_(to_delete_ids)))
        return len(to_delete_ids)


def _safe_path(base: Path, value: str) -> Optional[Path]:
    p = Path(value)
    if p.is_absolute():
        return p
    return (base / p).resolve()


def _planned_deletes(
    model_path: Path,
    workspace_root: Path,
    local_rows: Iterable[LocalModelSnapshot],
    include_shape_cache: bool,
) -> list[PlannedDelete]:
    planned: list[PlannedDelete] = []
    seen: set[Path] = set()

    def add(path: Path, reason: str) -> None:
        if path in seen:
            return
        seen.add(path)
        planned.append(PlannedDelete(path=path, reason=reason))

    for row in local_rows:
        if not row.local_path:
            continue
        resolved = _safe_path(model_path, row.local_path)
        if resolved is not None:
            add(resolved, f"local_path from model row {row.id}")

    for pattern in ("*.gguf", "*.safetensors"):
        for path in model_path.glob(pattern):
            add(path.resolve(), f"local model artifact ({pattern})")

    hf_dir = (model_path / "hf").resolve()
    if hf_dir.exists():
        add(hf_dir, "downloaded local Hugging Face cache")

    if include_shape_cache:
        shap_e_cache = (workspace_root / "shap_e_model_cache").resolve()
        if shap_e_cache.exists():
            add(shap_e_cache, "local Shap-E cache")

    return planned


def _delete_path(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate local registry/storage to hosted defaults")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes only")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    parser.add_argument("--text-model", default="Qwen/Qwen2.5-3B-Instruct", help="Hosted default text model ID")
    parser.add_argument("--image-model", default="stabilityai/sdxl-turbo", help="Hosted default image model ID")
    parser.add_argument(
        "--hf-3d-model",
        default=None,
        help="Optional hosted 3D model ID (warning: hosted 3D generation is not implemented)",
    )
    parser.add_argument(
        "--skip-shape-cache",
        action="store_true",
        help="Do not delete workspace shap_e_model_cache directory",
    )
    args = parser.parse_args()

    init_db()
    get_settings.cache_clear()
    settings = get_settings()

    model_path = Path(settings.model_path).resolve()
    workspace_root = Path(__file__).resolve().parents[1]

    print("=== Hosted Migration Plan ===")
    print(f"Database URL configured: {'yes' if settings.database_url else 'no (sqlite local)'}")
    print(f"Model path: {model_path}")
    print(f"Text default -> {args.text_model}")
    print(f"Image default -> {args.image_model}")

    hf_3d_supported = False
    if args.hf_3d_model:
        print(
            "3D default requested, but hosted 3D is currently unsupported by the adapter; "
            "the default will not be switched to hosted 3D."
        )

    local_rows = _collect_local_model_rows()
    plans = _planned_deletes(
        model_path=model_path,
        workspace_root=workspace_root,
        local_rows=local_rows,
        include_shape_cache=not args.skip_shape_cache,
    )

    print(f"Local model rows detected: {len(local_rows)}")
    print(f"Filesystem paths planned for cleanup: {len(plans)}")
    for item in plans:
        print(f" - {item.path} ({item.reason})")

    if args.dry_run and args.apply:
        parser.error("Use either --dry-run or --apply, not both.")

    if not args.apply:
        print("\nDry run complete. Re-run with --apply to execute.")
        return 0

    # 1) Ensure hosted defaults exist as hosted provider rows.
    _upsert_hosted_model(args.text_model, "text")
    _upsert_hosted_model(args.image_model, "image")

    # 2) Set default text/image to hosted.
    _set_default("text", args.text_model)
    _set_default("image", args.image_model)

    # 3) 3D default handling.
    if hf_3d_supported and args.hf_3d_model:
        _upsert_hosted_model(args.hf_3d_model, "3d")
        _set_default("3d", args.hf_3d_model)
    else:
        _delete_default("3d")

    # 4) Delete local model rows (preserve newly upserted hosted defaults).
    keep_ids = {args.text_model, args.image_model}
    deleted_rows = _delete_local_model_rows(keep_ids=keep_ids)

    # 5) Delete local files/directories.
    deleted_paths = 0
    for item in plans:
        try:
            if _delete_path(item.path):
                deleted_paths += 1
        except Exception as exc:
            print(f"WARN: failed to delete {item.path}: {exc}")

    print("\n=== Migration Applied ===")
    print(f"Deleted local model rows: {deleted_rows}")
    print(f"Deleted filesystem paths: {deleted_paths}")
    print("Set LLM_API_ENABLE_LOCAL_MODELS=false and restart backend to enforce hosted-only runtime.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
