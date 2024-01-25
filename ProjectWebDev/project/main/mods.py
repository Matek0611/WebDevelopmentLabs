from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.db.models import Sum
from django.utils import timezone
from . import models

def get_all_logged_in_users():
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    uid_list = []

    for session in sessions:
        data = session.get_decoded()
        uid_list.append(data.get('_auth_user_id', None))

    return User.objects.filter(id__in=uid_list)

def get_normal_workers():
    return User.objects.filter(is_staff=False)

def get_staff_workers():
    return User.objects.filter(is_staff=True)

def get_warehouse_size():
    res = models.Product.objects.aggregate(sum_amount=Sum('amount'))["sum_amount"]

    if not res: return 0
    return res

def get_sold_size():
    res = models.Sale.objects.aggregate(sum_sold=Sum("amount"))["sum_sold"]

    if not res: return 0
    return res

def get_user_added_product_count(id):
    res = models.Product.objects.filter(user_added_id=id)
    resall = models.Product.objects

    if not res or not resall: return 0
    return res.count() / resall.count()

def get_user_sold_product_price(id):
    try:
        usales = models.Sale.objects.filter(user_sold_id=id)
        res = 0

        for s in usales:
            res += s.amount * s.product_id.price
    except:
        return 0
    
    return res

def get_product_sold_count(product):
    try:
        usales = models.Sale.objects.filter(product_id=product.id).aggregate(sold_count=Sum("amount"))
        res = usales["sold_count"]
    except:
        return 0
    
    return res if res else 0
