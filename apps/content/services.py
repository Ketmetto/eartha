from .models import SiteText, SiteImage


def get_site_texts():
    """key -> current value, for every SiteText row. A migration seeds one
    row per Key.choices entry, but falling back to '' (via dict.get in the
    template) rather than raising keeps a template from ever 500ing on a
    key that hasn't been seeded yet."""
    return dict(SiteText.objects.values_list("key", "value"))


def get_site_image_urls():
    """key -> uploaded image URL, or None if the admin hasn't replaced it
    yet — templates fall back to the original built-in asset in that case."""
    return {img.key: (img.image.url if img.image else None) for img in SiteImage.objects.all()}
