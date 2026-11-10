"""Reply approval state machine. Pure logic, no I/O, so it is easy to test.

    DRAFT --submit--> IN_REVIEW --approve--> APPROVED --post--> POSTED
      ^                   |
      +----edit---- REJECTED <--reject--+

Rules:
- Only an approver can approve or reject.
- Separation of duties: nobody can approve or reject a reply they wrote.
- Text can only change while the reply is DRAFT or REJECTED.
"""
from dataclasses import dataclass
from typing import Optional


class WorkflowError(Exception):
    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class Actor:
    id: str
    role: str  # agent | approver


TRANSITIONS = {
    "submit": ({"DRAFT", "REJECTED"}, "IN_REVIEW"),
    "approve": ({"IN_REVIEW"}, "APPROVED"),
    "reject": ({"IN_REVIEW"}, "REJECTED"),
    "post": ({"APPROVED"}, "POSTED"),
}
EDITABLE = {"DRAFT", "REJECTED"}


def next_status(action: str, current: str, actor: Actor, author_id: str, reason: Optional[str] = None) -> str:
    if action not in TRANSITIONS:
        raise WorkflowError(f"Unknown action '{action}'.", 400)
    allowed_from, target = TRANSITIONS[action]
    if current not in allowed_from:
        raise WorkflowError(f"Can't {action} a reply that is {current.replace('_', ' ').lower()}.")
    if action in ("approve", "reject"):
        if actor.role != "approver":
            raise WorkflowError("Only an approver can approve or reject replies.", 403)
        if actor.id == author_id:
            raise WorkflowError("Separation of duties: you can't review a reply you wrote.", 403)
    if action == "reject" and not (reason or "").strip():
        raise WorkflowError("Add a short reason so the agent knows what to change.", 400)
    return target


def check_editable(current: str) -> None:
    if current not in EDITABLE:
        raise WorkflowError(f"This reply is {current.replace('_', ' ').lower()} and can no longer be edited.")


SENTIMENT_VALUE = {"NEGATIVE": -1, "NEUTRAL": 0, "MIXED": 0, "POSITIVE": 1}


def outcome_from(initial: str, follow_up: str) -> str:
    delta = SENTIMENT_VALUE.get(follow_up, 0) - SENTIMENT_VALUE.get(initial, 0)
    if delta > 0:
        return "IMPROVED"
    if delta < 0:
        return "WORSENED"
    return "NEUTRAL"
