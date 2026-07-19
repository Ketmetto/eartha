from django.contrib import admin
from .models import PointsLedgerEntry, Benefit, Redemption

admin.site.register(PointsLedgerEntry)
admin.site.register(Benefit)
admin.site.register(Redemption)
