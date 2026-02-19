from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import date
from django.conf import settings


# Пользователь
class User(AbstractUser):
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.username


# Склады
class Warehouse(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    has_free_delivery = models.BooleanField(default=False)
    price_per_cubic_meter = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Цена за 1 м³ хранения"
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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

    # Сколько месяцев хранения
    def storage_months(self):
        days = (self.due_date - self.created_at.date()).days
        months = max(days // 30, 1)
        return months

    # Расчёт полной стоимости
    def total_price(self):
        return self.volume * self.warehouse.price_per_cubic_meter * self.storage_months()

    # Просрочен ли заказ
    def is_overdue(self):
        return self.due_date < date.today()

    # Проверка занят бокс или нет
    def is_occupied(self):
        return self.status in ["pending", "stored"]
