from django.utils import timezone
from django.conf import settings
from stock_app.models import Order


def send_notification_mail(subject, recipients, template, context):
    print(
        "Email skipped (stub): "
        f"subject={subject}, recipients={recipients}, template={template}"
    )
    return "Done"


def check_rent_remainder():
    """Проверяет заказы с истекающей аренд и отправляет напоминания"""
    rent_reminder_days = settings.START_RENT_REMINDER_DAYS
    orders = Order.objects.filter(
        paid_till__lte=timezone.now() + timezone.timedelta(days=rent_reminder_days),
        paid_till__gte=timezone.now(),
        is_paid=True,
        status=Order.ACTIVE
    )
    print(f"Orders to be notified: {len(orders)}")
    
    for order in orders:
        days_left = (order.paid_till - timezone.now()).days + 1
        rent_end_date = order.paid_till.strftime('%d.%m.%Y')
        print(f"{days_left=}, {rent_end_date=} {order.box.title=}, {order.box.storage.title=}, {order.client.email=}")
        
        try:
            send_notification_mail(
                subject=f'Напоминание об окончании аренды - Бокс {order.box.title}',
                recipients=[order.client.email],
                template='rent_reminder.html',
                context={
                    'days_left': days_left,
                    'rent_end_date': rent_end_date,
                    'box': order.box,
                    'order': order,
                }
            )
        except Exception as e:
            print(f"Ошибка при отправке email для заказа {order.id}: {e}")
    
    print('Rent check completed')
    return "Done"

