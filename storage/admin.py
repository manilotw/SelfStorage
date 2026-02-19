from django.contrib import admin
from .models import (
    User,
    Warehouse,
    StorageRule,
    BoxOrder,
)


admin.site.register(Warehouse)
admin.site.register(StorageRule)
admin.site.register(BoxOrder)
admin.site.register(User)
