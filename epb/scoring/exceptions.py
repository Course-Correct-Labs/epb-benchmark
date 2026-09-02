"""Exceptions for EPB battery scoring."""

from typing import Any, Dict, List


class UnscoreableEvidenceError(Exception):
    """Raised when a battery cannot be scored because at least one task's
    evidence is not fully genuine, valid model text.

    Governing rule (this phase's Sec 0.3): an unusable observation is
    neither positive nor negative evidence for the target pathology. This
    phase is explicitly not authorized to decide whether such a task
    counts toward, is excluded from, or otherwise affects any battery
    numerator, denominator, or coverage calculation (Sec 5.1/5.2/5.4).

    Silently feeding the observation's text into the ordinary metric,
    silently skipping the task, or substituting a default verdict would
    each settle that question through control flow rather than through an
    explicit decision. Instead, the battery's score computation is blocked
    in full whenever any task's evidence is not fully valid text, and this
    exception carries complete diagnostic detail (which tasks, which
    observation kinds, why) for a later phase to resolve. See
    EPB_PHASE1_FOUNDATIONAL_REPAIR.md for the corrected Phase 1 boundary
    this class exists to enforce.

    IMPORTANT: blocking the *whole battery* on a single unusable task is
    temporary Phase 1 scaffolding, not a canonical EPB missingness rule.
    It exists only because computing a score from just the remaining valid
    tasks would itself have silently decided a denominator question this
    phase does not own. It is not a discovered scientific fact that one
    bad task should always invalidate an entire battery's score -- a later,
    semantic phase decides that, potentially very differently.
    """

    def __init__(self, battery: str, blocked: List[Dict[str, Any]]):
        self.battery = battery
        self.blocked = blocked
        detail = "; ".join(
            f"{b['task_id']} ({b['reason']}: "
            f"{','.join(b.get('observation_kinds') or []) or b.get('task_status', 'unknown')})"
            for b in blocked
        )
        super().__init__(
            f"{battery} scoring blocked: {len(blocked)} task(s) include evidence "
            f"that is not fully valid model text. Deciding how such evidence "
            f"should affect a numerator, denominator, or coverage calculation is "
            f"out of scope for this phase. Blocked tasks: {detail}"
        )
