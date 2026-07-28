"""Prove the complete local demo can be seeded three times without manual resets."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT))

from app import db, retrieval, services
from seed_demo import seed


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="curriculumos-demo-") as temporary:
        workspace = Path(temporary)
        db.DATABASE_PATH = workspace / "curriculumos.db"
        services.UPLOAD_DIR = workspace / "uploads"
        services.EXPORT_DIR = workspace / "exports"
        retrieval.INDEX_DIR = workspace / "retrieval"
        rehearsals = [seed(fresh=True) for _ in range(3)]
        for rehearsal in rehearsals:
            dashboard = services.dashboard(rehearsal["course_id"])
            assert dashboard["source_count"] >= 5
            assert len(dashboard["graph"]["concepts"]) >= 4
            assert dashboard["schedule"] and any(entry["locked"] for entry in dashboard["schedule"]["entries"])
            assert dashboard["lessons"] and dashboard["assessments"] and dashboard["mastery"]
            assert any(action["status"] == "approved" for action in dashboard["remediation"])
            assert Path(rehearsal["offline_export"]).is_file()
        print(json.dumps({"status": "passed", "rehearsals": len(rehearsals), "checks": ["source-to-export loop", "locked schedule", "approved remediation", "offline pack"]}, indent=2))


if __name__ == "__main__":
    main()
