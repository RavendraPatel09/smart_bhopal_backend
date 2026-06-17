from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.enums import Role
from app.models.user import User
from app.schemas.rewards import LeaderboardEntry, RewardSummary
from app.services import rewards_service

router = APIRouter(prefix="/rewards", tags=["Rewards & Badges"])


@router.get("/me", response_model=RewardSummary)
def my_rewards(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return rewards_service.reward_summary(db, user)


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
def leaderboard(
    role: Role = Query(default=Role.CITIZEN),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return rewards_service.leaderboard(db, role=role.value, limit=limit)
