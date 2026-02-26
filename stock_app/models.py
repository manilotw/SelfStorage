from django.db import models
from django.db.models import F
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings
from phonenumber_field.modelfields import PhoneNumberField


class CustomUser(AbstractUser):
    username = models.CharField('Имя пользователя', max_length=200, unique=True)
    email = models.EmailField('Почта', unique=True)
    phone = PhoneNumberField('Телефон', null=True, blank=True, db_index=True)
    first_name = models.CharField('Имя', max_length=200, null=True, blank=True)
    last_name = models.CharField('Фамилия', max_length=200, null=True, blank=True)


class Tariff(models.Model):
    title = models.CharField('Название тарифа', max_length=50)
    price = models.IntegerField('Цена')
    days = models.IntegerField('Количество дней')

    class Meta:
        verbose_name = 'Тариф'

    def __str__(self):
        return self.title


class Storage(models.Model):
    title = models.CharField('Склад', max_length=100)
    address = models.CharField('Адрес', max_length=200)
    image = models.ImageField('Фото')
    slug = models.SlugField(default='', null=False)
    status = models.BooleanField('Статус')

    class Meta:
        verbose_name = 'Склад'
        verbose_name_plural = 'Склады'

    def __str__(self):
        return self.address


class BoxQuerySet(models.QuerySet):
    def calculate_box_square(self):
        return self.annotate(
            box_square=F("length") * F("width"),
        )

    def calculate_price_per_month(self):
        month_tariff = Tariff.objects.filter(days=30).order_by("id").first()
        if not month_tariff:
            return self.annotate(month_price=F("price"))
        return self.annotate(month_price=F("length") * F("width") * month_tariff.price)


class Box(models.Model):
    title = models.CharField('Бокс', max_length=100)
    status = models.BooleanField('Статус', default=True)
    storage = models.ForeignKey(Storage,
                                on_delete=models.CASCADE,
                                related_name='box_storages',
                                verbose_name='Склад',
                                null=True)
    price = models.IntegerField('Цена')
    length = models.FloatField('Длина')
    width = models.FloatField('Ширина')
    height = models.FloatField('Высота')

    objects = BoxQuerySet.as_manager()

    class Meta:
        verbose_name = 'Бокс'
        verbose_name_plural = 'Боксы'

    def __str__(self):
        return self.title

    def is_available(self):
        """Проверяет, доступен ли бокс для аренды"""
        # Бокс доступен если у него нет активных запланированных заказов
        # или они истекли
        active_order = self.boxes.filter(
            is_paid=True,
            paid_till__gt=timezone.now()
        ).exists()
        return not active_order

    @property
    def current_tenant(self):
        """Возвращает текущего арендатора в течение активного периода аренды"""
        order = self.boxes.filter(
            is_paid=True,
            paid_till__gt=timezone.now()
        ).first()
        return order.client if order else None


class Order(models.Model):
    PENDING = 'pending'
    ACTIVE = 'active'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (PENDING, 'Ожидание оплаты'),
        (ACTIVE, 'Активная аренда'),
        (EXPIRED, 'Аренда закончилась'),
        (CANCELLED, 'Отменена'),
    ]
    
    client = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name='clients',
        verbose_name='Клиент'
    )
    time = models.DateTimeField('Время создания заказа', auto_now=True)
    comment = models.TextField(
        'Комментарий',
        max_length=200,
        null=True,
        blank=True
    )
    tariff = models.ForeignKey(
        Tariff,
        null=True,
        on_delete=models.CASCADE,
        related_name='tariffs',
        verbose_name='Тариф'
    )
    box = models.ForeignKey(
        Box,
        on_delete=models.CASCADE,
        related_name='boxes',
        null=True,
        verbose_name='Ячейка хранения'
    )
    is_paid = models.BooleanField(default=False)
    payment_id = models.CharField(max_length=200, blank=True, null=True)
    paid_till = models.DateTimeField('Оплата до', null=True)
    paid_date = models.DateTimeField('Дата оплаты', null=True, default=timezone.now)
    status = models.CharField(
        'Статус заказа',
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING
    )

    def is_expired(self):
        """Проверяет, скоро ли истекает аренда"""
        if not self.paid_till:
            return False
        days_left = (self.paid_till - timezone.now()).days
        return days_left <= settings.START_RENT_REMINDER_DAYS
    
    def is_active(self):
        """Проверяет, активна ли аренда в данный момент"""
        return (self.is_paid and 
                self.paid_till and 
                self.paid_till > timezone.now())
    
    def mark_active(self):
        """Отмечает заказ как активный"""
        if self.is_paid and self.paid_till:
            self.status = self.ACTIVE
            self.save()
    
    def mark_expired(self):
        """Отмечает заказ как истекший"""
        if self.paid_till and self.paid_till <= timezone.now():
            self.status = self.EXPIRED
            self.save()

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def __str__(self) -> str:
        return f"{self.client} {self.time}"
