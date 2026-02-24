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
    storages = Storage.objects.all()
    boxes = Box.objects.calculate_box_square().calculate_price_per_month().filter(storage__id=storage)
    boxes_lower_3_square = boxes.filter(box_square__lt=3).filter(storage__id=storage)
    boxes_lower_10_square = boxes.filter(box_square__lt=10).filter(storage__id=storage)
    boxes_upper_10_square = boxes.filter(box_square__gte=10).filter(storage__id=storage)
    context = {
        'storages': storages,
        'boxes': boxes,
        'boxes_lower_3_square': boxes_lower_3_square,
        'boxes_lower_10_square': boxes_lower_10_square,
        'boxes_upper_10_square': boxes_upper_10_square,
    }
    return render(request, 'boxes.html', context=context)

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
    box = Box.objects.get(id=boxnumber)

    if request.method == "POST":
        tariff_id = request.POST.get("tariff_id")
        tariff = Tariff.objects.get(id=tariff_id)

        order = Order.objects.filter(
            client=request.user,
            box=box
        ).order_by('-paid_till').first()

        if not order:
            order = Order.objects.create(
                client=request.user,
                box=box,
                tariff=tariff,
                is_paid=False
            )
        else:
            order.tariff = tariff
            order.is_paid = False

        Configuration.account_id = settings.YOOKASSA_SHOP_ID
        Configuration.secret_key = settings.YOOKASSA_API_KEY

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
            "description": f"Продление бокса {box.title} на {tariff.days} дней"
        }, uuid.uuid4())

        order.payment_id = payment.id
        order.save()

        return redirect(payment.confirmation.confirmation_url)

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
    order = Order.objects.get(id=order_id)

    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_API_KEY

    payment = Payment.find_one(order.payment_id)

    if payment.paid:
        order.is_paid = True
        order.paid_date = timezone.now()

        if order.paid_till and order.paid_till > timezone.now():
            order.paid_till += datetime.timedelta(days=order.tariff.days)
        else:
            order.paid_till = timezone.now() + datetime.timedelta(days=order.tariff.days)

        order.save()

        return redirect("my-rent")

    return render(request, "paid-not-success.html")


def show_faq(request):
    return render(request, 'faq.html')


def not_paid_view(request):
    return render(request, 'paid-not-success.html')


@login_required(login_url='login')
def show_user_rent(request):
    active_orders = Order.objects.filter(client=request.user,
                                         paid_till__gte=timezone.now(),
                                         is_paid=True,
                                         ).order_by('paid_till')
    context = {
        'client': request.user,
        'active_orders': active_orders,
    }

    if request.method == 'POST' and 'box_id' in request.POST:
        process_open_box(request)
    if request.method == 'POST' and 'PASSWORD_EDIT' in request.POST:
        messages.info(request, 'Not implemented yet')
    form = CreateUserForm()

    if request.method == 'POST':
        email = request.POST.get('EMAIL_EDIT')
        phone = request.POST.get('PHONE_EDIT')
        password = request.POST.get('PASSWORD_EDIT')
        request.user.email = email
        request.user.phone = phone
        request.user.save()

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
