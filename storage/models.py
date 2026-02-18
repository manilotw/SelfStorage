from django.db import models
from django.db import models
from django.contrib.auth.models import User


# Пользователь
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.username


# Рекламная кампания
class AdCampaign(models.Model):
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    clicks = models.PositiveIntegerField(default=0)
    orders = models.PositiveIntegerField(default=0)


# Склады
class Warehouse(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    has_free_delivery = models.BooleanField(default=False)
    price_per_cubic_meter = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Цена за 0.5 м³ хранения"
    )

    def __str__(self):
        return self.name


# Правила хранения
class StorageRule(models.Model):
    allowed_items = models.TextField()  # список разрешённых вещей
    prohibited_items = models.TextField()  # список запрещённых вещей
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)


# Заказ бокса
class BoxOrder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    pickup_address = models.TextField()  # адрес, откуда заберут вещи
    volume = models.FloatField(help_text="Объём вещей в м³")
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField()  # дата окончания аренды
    returned = models.BooleanField(default=False)  # если пользователь вернул часть вещей
    qr_code = models.CharField(max_length=200, blank=True, null=True)
    delivery_requested = models.BooleanField(default=False)
    status = models.CharField(
        max_length=50,
        choices=[
            ("pending", "В обработке"),
            ("stored", "На складе"),
            ("delivered", "Доставлено"),
            ("overdue", "Просрочено"),
        ],
        default="pending"
    )

    # Проверка занят бокс или нет
    def is_occupied(self):
        return self.status in ["pending", "stored"]
