from pydantic import BaseModel, ConfigDict


class RewardSummary(BaseModel):
    user_id: int
    points: int
    badge: str
    next_badge: str | None
    points_to_next_badge: int | None
    complaints_submitted: int
    complaints_closed: int


class LeaderboardEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    user_id: int
    name: str
    points: int
    badge: str
