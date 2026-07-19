"""
Points-per-condition criteria — static reference table (proposal option a).
Swap this function for a Category/Condition-aware DB-backed rules engine
(option b) later without touching services.py's call site.
"""
from apps.submissions.models import Item

POINTS_TABLE = {
    Item.Condition.LIKE_NEW: 100,
    Item.Condition.GOOD: 70,
    Item.Condition.WORN: 40,
    Item.Condition.DAMAGED: 15,
}


def suggested_points(condition: str) -> int:
    return POINTS_TABLE.get(condition, 0)
