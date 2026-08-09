"""
Points-per-(category, condition) criteria — admin-configurable via
PointsRule (see apps.points.models and the queue page's AWARD RULES tab).
Only a suggested default: the admin can always type a different amount
when actually awarding (apps.points.services.set_item_award).
"""


def suggested_points(category: str, condition: str) -> int:
    from .models import PointsRule

    rule = PointsRule.objects.filter(category=category, condition=condition).first()
    return rule.points if rule else 0
