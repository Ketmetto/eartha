from django.db import migrations

# Current copy from apps/web/templates/web/{index,about,contact}.html at
# the time this app was added — the starting value for each editable slot,
# not a hardcoded fallback (SiteText rows always exist after this migration).
TEXT_DEFAULTS = {
    "index_hero_title": "THE HOME OF CIRCULAR FASHION.",
    "index_hero_sub": "Where brands, creators, and communities make sustainability part of everyday fashion.",
    "about_hero_title": "WE IMAGINE A WORLD WHERE NOTHING VALUABLE IS LEFT BEHIND.",
    "about_mission_body": (
        "The future of fashion isn't about making more — it's about making what already exists "
        "last longer. Eartha brings together people, brands, and circular solutions to extend the "
        "life of clothing, reduce waste, and reward the choices that create lasting impact."
    ),
    "contact_hero_title": "EVERY GREAT IDEA STARTS WITH A CONVERSATION.",
    "contact_hero_sub": (
        "Whether you have a question, a partnership, or an idea for a more circular future, "
        "we'd love to hear from you."
    ),
}

IMAGE_KEYS = [
    "index_second_shape_1",
    "index_second_shape_2",
    "about_hero_1",
    "about_hero_2",
    "contact_hero_bg",
]


def seed(apps, schema_editor):
    SiteText = apps.get_model("content", "SiteText")
    SiteImage = apps.get_model("content", "SiteImage")
    for key, value in TEXT_DEFAULTS.items():
        SiteText.objects.update_or_create(key=key, defaults={"value": value})
    for key in IMAGE_KEYS:
        SiteImage.objects.get_or_create(key=key)


def unseed(apps, schema_editor):
    SiteText = apps.get_model("content", "SiteText")
    SiteImage = apps.get_model("content", "SiteImage")
    SiteText.objects.filter(key__in=TEXT_DEFAULTS.keys()).delete()
    SiteImage.objects.filter(key__in=IMAGE_KEYS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
