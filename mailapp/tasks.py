from django.utils import timezone
from stock_app.models import Order


def send_notification_mail(subject, recipients, template, context):
    print(
        "Email skipped (stub): "
        f"subject={subject}, recipients={recipients}, template={template}"
    )
    return "Done"


def check_rent_remainder():
    rent_reminder_days = settings.START_RENT_REMINDER_DAYS
    orders = Order.objects.filter(
        paid_till__lte=timezone.now() + timezone.timedelta(days=rent_reminder_days),
        paid_till__gte=timezone.now()
    )
    print(f"Orders to be notified: {len(orders)}")
    for order in orders:
        days_left = (order.paid_till - timezone.now()).days + 1
        rent_end_date = order.paid_till.strftime('%d.%m.%Y')
        print(f"{days_left=}, {rent_end_date=} {order.box.title=}, {order.box.storage.title=}, {order.client.email=}")
        send_notification_mail(
            subject=f'Reminder about rent end. Box {order.box.title}. Storage {order.box.storage.title}',
            recipients=[order.client.email],
            template='rent_reminder.html',
            context={
                'days_left': days_left,
                'rent_end_date': rent_end_date,
            }
        )
    print('Rent has been checked')

    return "Done"
