"""Remediation Cost Model based on named configuration constants."""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple

from src.dd.config import get_settings


class ActionType(str, Enum):
    """Types of counterfactual remediation actions."""

    DELETE_POST = "delete_post"
    GENERALIZE_FIELD = "generalize_field"
    CHANGE_RECOVERY_ANSWER = "change_recovery_answer"
    REMOVE_DATA_SOURCE = "remove_data_source"


class ActionCost(NamedTuple):
    action_type: ActionType
    cost: int
    description: str


class RemediationCostModel:
    """Computes a priori effort costs for counterfactual remediation actions."""

    @classmethod
    def get_cost(cls, action_type: ActionType) -> int:
        settings = get_settings()
        if action_type == ActionType.DELETE_POST:
            return settings.cost_delete_post
        elif action_type == ActionType.GENERALIZE_FIELD:
            return settings.cost_generalize_field
        elif action_type == ActionType.CHANGE_RECOVERY_ANSWER:
            return settings.cost_change_recovery_answer
        elif action_type == ActionType.REMOVE_DATA_SOURCE:
            return settings.cost_remove_data_source
        return 1

    @classmethod
    def all_costs(cls) -> dict[ActionType, int]:
        return {action_type: cls.get_cost(action_type) for action_type in ActionType}
