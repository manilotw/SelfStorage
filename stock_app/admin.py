from django.contrib import admin
from .models import Tariff, Storage, Order, Box, CustomUser


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    pass


@admin.register(Storage)
class StorageAdmin(admin.ModelAdmin):
    pass


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'box', 'tariff', 'is_paid', 'status', 'paid_till', 'time']
    list_filter = ['is_paid', 'status', 'time', 'paid_till']
    search_fields = ['client__username', 'client__email', 'box__title']
    readonly_fields = ['time', 'payment_id']
    
    fieldsets = (
        ('Информация о заказе', {
            'fields': ('client', 'box', 'tariff', 'time', 'payment_id')
        }),
        ('Статус и оплата', {
            'fields': ('is_paid', 'status', 'paid_date', 'paid_till')
        }),
        ('Комментарии', {
            'fields': ('comment',),
            'classes': ('collapse',)
        }),
    )



@admin.register(Box)
class BoxAdmin(admin.ModelAdmin):
    list_display = ['title', 'storage', 'status', 'get_square', 'price', 'get_current_tenant', 'get_rental_status']
    list_filter = ['status', 'storage']
    search_fields = ['title', 'storage__title']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'storage', 'status', 'price')
        }),
        ('Размеры', {
            'fields': ('length', 'width', 'height')
        }),
    )
    
    def get_square(self, obj):
        return f"{obj.length * obj.width:.2f} м²"
    get_square.short_description = 'Площадь'
    
    def get_current_tenant(self, obj):
        tenant = obj.current_tenant
        return tenant.username if tenant else '—'
    get_current_tenant.short_description = 'Текущий арендатор'
    
    def get_rental_status(self, obj):
        if obj.is_available():
            return '✓ Свободен'
        else:
            return '✗ Занят'
    get_rental_status.short_description = 'Статус'



@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email',]
