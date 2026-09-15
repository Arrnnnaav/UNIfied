"""Publish the reviewed fixed catalog under an existing operator account.

This command refuses to create an operator. It is safe to run after operator
provisioning and is idempotent by slug/version.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import make_engine
from app.core.models import LearningPackage, User


def main() -> None:
    engine = make_engine(get_settings().database_url)
    catalog = Path(__file__).resolve().parents[1] / "packages" / "catalog"
    with Session(engine) as db:
        operator = db.query(User).filter(User.role == "operator").order_by(User.created_at).first()
        if not operator:
            raise SystemExit("No operator exists; provision one before publishing the catalog.")
        count = 0
        for path in sorted(catalog.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if db.query(LearningPackage).filter(LearningPackage.slug == data["slug"], LearningPackage.version == data["version"]).first():
                continue
            db.add(LearningPackage(slug=data["slug"], title=data["title"], description=data.get("description", ""), version=data["version"], status="published", manifest_json=json.dumps(data.get("manifest", {}), ensure_ascii=False), created_by=operator.id, updated_at=__import__("datetime").datetime.utcnow()))
            count += 1
        db.commit()
        print(f"published={count} operator={operator.student_id}")


if __name__ == "__main__":
    main()
