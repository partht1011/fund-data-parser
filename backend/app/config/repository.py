from pathlib import Path

import yaml  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.schema import FundConfig
from app.storage.models import ConfigVersionRow, FundConfigRow


class ConfigRepository:
    def __init__(self, session: Session, defaults_dir: Path | None = None) -> None:
        self.session = session
        self.defaults_dir = defaults_dir or Path(__file__).parent / "defaults"

    def list(self) -> list[FundConfig]:
        configured = {
            row.fund_id: self._load_yaml(row.yaml_content)
            for row in self.session.scalars(select(FundConfigRow)).all()
        }
        for path in sorted(self.defaults_dir.glob("*.yaml")):
            config = self._load_yaml(path.read_text(encoding="utf-8"))
            configured.setdefault(config.fund_id, config)
        return sorted(configured.values(), key=lambda config: config.display_name)

    def get(self, fund_id: str) -> FundConfig | None:
        row = self.session.get(FundConfigRow, fund_id)
        if row:
            return self._load_yaml(row.yaml_content)
        for config in self.list():
            if config.fund_id == fund_id:
                return config
        return None

    def save(self, config: FundConfig) -> FundConfig:
        content = yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False, allow_unicode=True)
        existing = self.session.get(FundConfigRow, config.fund_id)
        if existing:
            existing.current_version = config.version
            existing.yaml_content = content
        else:
            self.session.add(
                FundConfigRow(
                    fund_id=config.fund_id,
                    current_version=config.version,
                    yaml_content=content,
                )
            )
        self.session.add(
            ConfigVersionRow(fund_id=config.fund_id, version=config.version, yaml_content=content)
        )
        self.session.commit()
        return config

    @staticmethod
    def _load_yaml(content: str) -> FundConfig:
        return FundConfig.model_validate(yaml.safe_load(content))
