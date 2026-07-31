from django.apps import AppConfig


class WebConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.web"
    label = "web"

    def ready(self):
        _patch_unfold_flatten_context()


def _patch_unfold_flatten_context():
    """django-unfold's admin templates flatten the template context via
    Context.flatten(), which crashes (ValueError: dictionary update sequence
    element #0 has length 8; 2 is required) whenever Context.new() has left a
    nested Context object inside context.dicts instead of a plain dict —
    Django bug #35417. Unfold's own _flatten_context() assumes this is fixed
    on Django >= 5.0, but it still reproduces on our pinned 5.0.14, taking
    down every single admin change-form page with a 500.

    Replace it with a version that recurses into nested Context objects
    instead of assuming they can't occur — strictly more correct than both
    Django's raw flatten() and Unfold's own version-gated fallback (which
    silently drops any keys that only exist inside the nested Context)."""
    from unfold.templatetags import unfold as unfold_tags

    def _recursive_flatten_context(context):
        flat = {}
        for d in context.dicts:
            if hasattr(d, "dicts"):
                flat.update(_recursive_flatten_context(d))
            else:
                flat.update(d)
        return flat

    unfold_tags._flatten_context = _recursive_flatten_context
