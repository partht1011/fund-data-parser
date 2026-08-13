from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.repository import ConfigRepository
from app.config.schema import FundConfig
from app.storage.database import get_session
from app.storage.models import FundConfigRow

router = APIRouter(tags=["configs"])


@router.get("/configs", response_model=list[FundConfig])
def list_configs(session: Session = Depends(get_session)) -> list[FundConfig]:
    return ConfigRepository(session).list()


@router.post("/configs", response_model=FundConfig, status_code=status.HTTP_201_CREATED)
def create_config(config: FundConfig, session: Session = Depends(get_session)) -> FundConfig:
    repository = ConfigRepository(session)
    if session.get(FundConfigRow, config.fund_id):
        raise HTTPException(status_code=409, detail="Configuration already exists; use PUT")
    return repository.save(config)


@router.put("/configs/{fund_id}", response_model=FundConfig)
def update_config(
    fund_id: str, config: FundConfig, session: Session = Depends(get_session)
) -> FundConfig:
    if fund_id != config.fund_id:
        raise HTTPException(status_code=400, detail="Path fund_id must match configuration")
    return ConfigRepository(session).save(config)
