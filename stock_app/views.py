import uuid
import qrcode
import datetime

from django.shortcuts import render
from stock_app.models import Storage, Box, Order, Tariff
from mailapp.tasks import send_notification_mail
from django.shortcuts import redirect
from yookassa import Configuration, Payment
from django.conf import settings
from stock_app.forms import CreateUserForm, ChangeUserForm, UserForm
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.urls import reverse


def logout_user(request):
    logout(request)
    return redirect('/')


def login_user(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            print('user is not None')
            login(request, user)
            return redirect('my-rent')
        else:
            messages.info(request, 'Email or password is incorrect')

    context = {}
    return render(request, 'login.html', context)


def register_user(request):
    form = CreateUserForm()

    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            update_session_auth_hash(request, user)
            return redirect('my-rent')

    context = {'form': form}
    return render(request, 'registration.html', context)


def index(request):
    context = {}
    if request.user.is_authenticated:
        context = {
            'user': request.user
        }
    if request.method == 'POST' and 'EMAIL' in request.POST:
        process_welcome_email(request)
    return render(request, 'index.html', context)


def storage_view(request, storage):
    try:
        storages = Storage.objects.all()
        boxes = Box.objects.calculate_box_square().calculate_price_per_month().filter(
            storage__id=storage,
            status=True
        )
        
        # Фильтруем только доступные боксы
        available_boxes = [box for box in boxes if box.is_available()]
        
        # Разделяем по площади
        boxes_lower_3_square = [b for b in available_boxes if b.box_square < 3]
        boxes_lower_10_square = [b for b in available_boxes if 3 <= b.box_square < 10]
        boxes_upper_10_square = [b for b in available_boxes if b.box_square >= 10]
        
        context = {
            'storages': storages,
            'boxes': available_boxes,
            'boxes_lower_3_square': boxes_lower_3_square,
            'boxes_lower_10_square': boxes_lower_10_square,
            'boxes_upper_10_square': boxes_upper_10_square,
        }
        return render(request, 'boxes.html', context=context)
    except Storage.DoesNotExist:
        messages.error(request, 'Склад не найден')
        return redirect('index')

'''
@login_required(login_url='login')
def payment_view(request, boxnumber):
    box = Box.objects.calculate_price_per_month().get(id=boxnumber)
    month_tariff = Tariff.objects.filter(days=30).order_by("id").first()
    if not month_tariff:
        messages.error(request, "Tariff for 30 days is missing. Contact support.")
        return redirect("paid-not-success")
    order = Order.objects.get_or_create(
        client=request.user,
        tariff=month_tariff,
        box=box,
    )[0]
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_API_KEY
    allowed_host = settings.ALLOWED_HOSTS

    payment = Payment.create({
        "amount": {
            "value": box.month_price,
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": f"http://{allowed_host[0]}:8000/order_status/{order.id}"
        },
        "capture": True,
        "description": f"Бокс №{box.title} - "
                       f"Цена {box.month_price} - "
                       f"Длина {box.length} - "
                       f"Ширина {box.width} - "
                       f"Высота {box.height}"
    }, uuid.uuid4())
    redirect_url = payment.confirmation.confirmation_url
    order.comment = box.title
    order.payment_id = payment.id
    if order.paid_till:
        order.paid_till = order.paid_till + datetime.timedelta(days=30)
    else:
        order.paid_till = datetime.datetime.today() + datetime.timedelta(days=30)
    order.save()
    return redirect(redirect_url)
'''

@login_required(login_url='login')
def payment_view(request, boxnumber):
    try:
        box = Box.objects.get(id=boxnumber)
    except Box.DoesNotExist:
        messages.error(request, 'Бокс не найден')
        return redirect('storage')
    
    # Проверяем доступность бокса
    if not box.is_available():
        messages.error(request, 'Этот бокс уже занят. Выберите другой.')
        return redirect('storage', storage=box.storage.id)

    if request.method == "POST":
        tariff_id = request.POST.get("tariff_id")
        
        try:
            tariff = Tariff.objects.get(id=tariff_id)
        except Tariff.DoesNotExist:
            messages.error(request, 'Тариф не найден')
            return render(request, "payment.html", {
                "box": box,
                "tariffs": Tariff.objects.all()
            })

        # Проверяем повторно доступность перед созданием заказа
        if not box.is_available():
            messages.error(
                request,
                'Извините, бокс был зарезервирован другим пользователем. '
                'Пожалуйста, выберите другой бокс.'
            )
            return redirect('storage', storage=box.storage.id)

        # Получаем или создаем заказ
        order = Order.objects.filter(
            client=request.user,
            box=box,
            is_paid=False
        ).first()

        if not order:
            order = Order.objects.create(
                client=request.user,
                box=box,
                tariff=tariff,
                is_paid=False,
                status=Order.PENDING
            )
        else:
            order.tariff = tariff
            order.is_paid = False
            order.status = Order.PENDING

        # Инициализируем платеж через Yookassa
        Configuration.account_id = settings.YOOKASSA_SHOP_ID
        Configuration.secret_key = settings.YOOKASSA_API_KEY

        try:
            payment = Payment.create({
                "amount": {
                    "value": tariff.price,
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": request.build_absolute_uri(
                        reverse("order_status", args=[order.id])
                    )
                },
                "capture": True,
                "description": f"Аренда бокса {box.title} ({box.storage.title}) "
                               f"на {tariff.days} дней - {tariff.title}"
            }, uuid.uuid4())

            order.payment_id = payment.id
            order.save()

            return redirect(payment.confirmation.confirmation_url)
        except Exception as e:
            messages.error(request, f'Ошибка при создании платежа: {str(e)}')
            return render(request, "payment.html", {
                "box": box,
                "tariffs": Tariff.objects.all()
            })

    tariffs = Tariff.objects.all()
    return render(request, "payment.html", {
        "box": box,
        "tariffs": tariffs
    })

'''
def order_status_view(request, order_id: int):
    order = Order.objects.get(id=order_id)
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_API_KEY
    allowed_host = settings.ALLOWED_HOSTS
    payment = Payment.find_one(order.payment_id)
    if payment.paid:
        order.is_paid = True
        order.save()
        return redirect(f"http://{allowed_host[0]}:8000/my-rent/")
    return render(request, 'paid-not-success.html')
'''

def order_status_view(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        messages.error(request, 'Заказ не найден')
        return render(request, 'paid-not-success.html')

    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_API_KEY

    try:
        payment = Payment.find_one(order.payment_id)
    except Exception as e:
        messages.error(request, f'Ошибка при проверке платежа: {str(e)}')
        return render(request, 'paid-not-success.html')

    if payment.paid:
        # Платеж успешно произведен
        order.is_paid = True
        order.paid_date = timezone.now()
        order.status = Order.ACTIVE

        # Устанавливаем дату истечения аренды
        if order.tariff:
            if order.paid_till and order.paid_till > timezone.now():
                # Продление существующей аренды
                order.paid_till += datetime.timedelta(days=order.tariff.days)
            else:
                # Новая аренда
                order.paid_till = timezone.now() + datetime.timedelta(days=order.tariff.days)
        
        order.save()
        messages.success(
            request,
            f'Платеж успешен! Аренда активна до {order.paid_till.strftime("%d.%m.%Y")}'
        )
        
        # Отправляем email с подтверждением
        try:
            send_notification_mail(
                subject='Подтверждение аренды',
                recipients=[order.client.email],
                template='rent_reminder.html',
                context={
                    'box': order.box,
                    'order': order,
                    'paid_till': order.paid_till,
                }
            )
        except Exception as e:
            print(f'Ошибка при отправке email: {e}')
        
        return redirect('my-rent')
    else:
        # Платеж не прошел
        messages.error(request, 'Платеж не был произведен. Пожалуйста, попробуйте еще раз.')
        return render(request, 'paid-not-success.html')


def show_faq(request):
    return render(request, 'faq.html')


def not_paid_view(request):
    return render(request, 'paid-not-success.html')


@login_required(login_url='login')
def show_user_rent(request):
    # Получаем активные заказы пользователя
    active_orders = Order.objects.filter(
        client=request.user,
        paid_till__gte=timezone.now(),
        is_paid=True,
    ).order_by('paid_till')
    
    # Обновляем статусы заказов
    for order in active_orders:
        order.mark_active()
    
    # Проверяем истекающие сроки и отправляем напоминания
    expiring_orders = [o for o in active_orders if o.is_expired()]
    
    context = {
        'client': request.user,
        'active_orders': active_orders,
        'expiring_count': len(expiring_orders),
    }

    if request.method == 'POST' and 'box_id' in request.POST:
        process_open_box(request)
    
    if request.method == 'POST' and 'EMAIL_EDIT' in request.POST:
        email = request.POST.get('EMAIL_EDIT')
        phone = request.POST.get('PHONE_EDIT')
        
        # Валидация email
        if email and '@' in email:
            request.user.email = email
            if phone:
                request.user.phone = phone
            request.user.save()
            messages.success(request, 'Профиль обновлен')
        else:
            messages.error(request, 'Пожалуйста, введите корректный email')

    return render(request, 'my-rent.html', context)


def process_welcome_email(request):
    user_mail = request.POST.get('EMAIL')
    if not user_mail:
        return "Error"
    send_notification_mail(
        subject='Welcome to our storage',
        recipients=[user_mail],
        template='welcome.html',
        context={
            'user_mail': user_mail,
            'inline_images': ['img1.png'],
        }
    )
    return "Done"


def process_open_box(request):

    user_mail = request.user.email

    box_id = request.POST.get('box_id')
    if not box_id:
        return "Error"
    qr_code_uuid = uuid.uuid4()
    qr_data = {
        'box_id': box_id,
        'user_id': 1,
        'uuid': qr_code_uuid,
        'timestamp': '2021-01-01 00:00:00',
    }
    qr_image = qrcode.make(qr_data)
    qr_image_name = f'qr_code_{qr_code_uuid}.png'
    qr_image.save(f'{settings.MEDIA_ROOT}/{qr_image_name}')
    send_notification_mail(
        subject='Your box is ready',
        recipients=[user_mail],
        template='open_box.html',
        context={
            'box_id': box_id,
            'qr_code_uuid': qr_code_uuid,
            'inline_images': ['img1.png', qr_image_name],
        }
    )
    return "Done"


@login_required(login_url='login')
def rental_history_view(request):
    """Показывает историю всех аренд пользователя"""
    all_orders = Order.objects.filter(client=request.user).order_by('-time')
    
    context = {
        'orders': all_orders,
        'user': request.user,
    }
    return render(request, 'rental-history.html', context)


@login_required(login_url='login')
def cancel_rental_view(request, order_id):
    """Отменяет аренду"""
    try:
        order = Order.objects.get(id=order_id, client=request.user)
        
        if order.status == Order.CANCELLED:
            messages.warning(request, 'Эта аренда уже была отменена')
        elif order.status == Order.EXPIRED:
            messages.warning(request, 'Эта аренда уже истекла')
        elif order.status == Order.ACTIVE:
            order.status = Order.CANCELLED
            order.save()
            messages.success(request, 'Аренда отменена')
        
        return redirect('my-rent')
    except Order.DoesNotExist:
        messages.error(request, 'Заказ не найден')
        return redirect('my-rent')

