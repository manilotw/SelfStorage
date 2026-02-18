from django.contrib import admin
from .models import (
    UserProfile,
    Warehouse,
    StorageRule,
    BoxOrder,
    AdCampaign,
)


admin.site.register(Warehouse)
admin.site.register(StorageRule)
admin.site.register(BoxOrder)
admin.site.register(AdCampaign)
admin.site.register(UserProfile)