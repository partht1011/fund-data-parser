from app.config.repository import ConfigRepository
from app.config.schema import FundConfig
from app.domain.models import ConfigSummary


class ConfigService:
    def __init__(self, repository: ConfigRepository) -> None:
        self.repository = repository

    def summaries(self) -> list[ConfigSummary]:
        return [
            ConfigSummary(fund_id=config.fund_id, version=config.version, display_name=config.display_name)
            for config in self.repository.list()
        ]

    def save(self, config: FundConfig) -> FundConfig:
        return self.repository.save(config)
