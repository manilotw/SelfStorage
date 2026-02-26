from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from stock_app.models import Order
from mailapp.tasks import send_notification_mail


class Command(BaseCommand):
    help = 'Отправляет напоминания об истечении аренды'

    def handle(self, *args, **options):
        # Получаем заказы, срок которых истекает в ближайшие дни
        days_to_check = settings.START_RENT_REMINDER_DAYS
        
        cutoff_date = timezone.now() + timezone.timedelta(days=days_to_check)
        cutoff_date_min = timezone.now()
        
        expiring_orders = Order.objects.filter(
            is_paid=True,
            status=Order.ACTIVE,
            paid_till__gte=cutoff_date_min,
            paid_till__lte=cutoff_date,
        )
        
        sent_count = 0
        for order in expiring_orders:
            try:
                days_left = (order.paid_till - timezone.now()).days
                send_notification_mail(
                    subject='Напоминание об истечении аренды',
                    recipients=[order.client.email],
                    template='rent_reminder.html',
                    context={
                        'box': order.box,
                        'order': order,
                        'days_left': days_left,
                        'paid_till': order.paid_till,
                    }
                )
                sent_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Письмо отправлено пользователю {order.client.email} '
                        f'для бокса {order.box.title}'
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Ошибка при отправке письма пользователю {order.client.email}: {str(e)}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Всего отправлено {sent_count} напоминаний об истечении аренды'
            )
        )
