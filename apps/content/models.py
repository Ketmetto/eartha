from django.db import models
from base.models import BaseModel


class SiteText(BaseModel):
    """Admin-editable copy on the public marketing pages (home/about/contact).
    Fixed set of keys — rows are seeded by a migration, never created via
    the API. Replacing the value is the only thing an admin can do here."""
    class Key(models.TextChoices):
        INDEX_HERO_TITLE = "index_hero_title", "Home — Hero headline"
        INDEX_HERO_SUB = "index_hero_sub", "Home — Hero subheading"
        ABOUT_HERO_TITLE = "about_hero_title", "About — Hero headline"
        ABOUT_MISSION_BODY = "about_mission_body", "About — Mission paragraph"
        CONTACT_HERO_TITLE = "contact_hero_title", "Contact — Hero headline"
        CONTACT_HERO_SUB = "contact_hero_sub", "Contact — Hero subheading"

    key = models.CharField(max_length=40, choices=Key.choices, unique=True)
    value = models.TextField()

    def __str__(self):
        return self.get_key_display()


class SiteImage(BaseModel):
    """Admin-editable images on the public marketing pages. Same fixed-set
    convention as SiteText. `image` blank means "not customized yet" — the
    template falls back to the original built-in asset in that case."""
    class Key(models.TextChoices):
        INDEX_SECOND_SHAPE_1 = "index_second_shape_1", "Home — Second shape image 1"
        INDEX_SECOND_SHAPE_2 = "index_second_shape_2", "Home — Second shape image 2"
        ABOUT_HERO_1 = "about_hero_1", "About — Hero image 1"
        ABOUT_HERO_2 = "about_hero_2", "About — Hero image 2"
        CONTACT_HERO_BG = "contact_hero_bg", "Contact — Hero background"
        ACCEPT_OUTERWEAR = "accept_outerwear", "Home — What we accept: Outerwear"
        ACCEPT_DENIM_COTTON = "accept_denim_cotton", "Home — What we accept: Denim & cotton"
        ACCEPT_KNITWEAR = "accept_knitwear", "Home — What we accept: Knitwear"
        ACCEPT_DRESSES = "accept_dresses", "Home — What we accept: Dresses"
        ACCEPT_ACCESSORIES = "accept_accessories", "Home — What we accept: Accessories"
        ACCEPT_SHOES_BAGS = "accept_shoes_bags", "Home — What we accept: Shoes & bags"

    key = models.CharField(max_length=40, choices=Key.choices, unique=True)
    image = models.ImageField(upload_to="site_content/", blank=True)

    def __str__(self):
        return self.get_key_display()
