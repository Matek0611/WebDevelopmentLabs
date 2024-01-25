from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout, get_user_model, password_validation
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone
from . import mods, models
import hashlib
import random
import string
import wikipedia
import io
import textwrap
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('Segoe UI', 'segoeui.ttf'))

def home_page(request):
    if not request.user.is_authenticated:
        return render(request, 'main/home.html', {})
    
    return redirect(dashboard_page)

def login_page(request):
    if not request.user.is_authenticated:
        if request.method == "POST":
            username = request.POST.get("username")
            password = request.POST.get("password")

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect(dashboard_page)
            else:
                messages.info(request, "Niepoprawna nazwa użytkownika lub hasło.")

        return render(request, 'main/login.html', {})
    else:
        return redirect(dashboard_page)
    
def logout_page(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect(home_page)

def dashboard_page(request):
    if not request.user.is_authenticated:
        return redirect(login_page)
    
    return render(request, "main/dashboard.html", {"page_id": 0, "active_users": mods.get_all_logged_in_users().count(), 
                                                   "normal_users": mods.get_normal_workers().count(),
                                                   "staff_users": mods.get_staff_workers().count(),
                                                   "products_amount": mods.get_warehouse_size(),
                                                   "sold_amount": mods.get_sold_size(),
                                                   "user_added_count": mods.get_user_added_product_count(request.user.id) * 100,
                                                   "user_sold_price": mods.get_user_sold_product_price(request.user.id)})
    
def products_page(request):
    if not request.user.is_authenticated:
        return redirect(login_page)
    
    if request.method == "POST" and request.POST.get("submit") == "Cofnij":
        try:
            sale_id = request.POST.get("sale_id").strip()
            sale = models.Sale.objects.get(id=sale_id)
            
            sale.product_id.amount += sale.amount
            sale.product_id.save()

            sale.delete()

            return redirect(products_page)
        except Exception as ex:
            messages.error(request, "Błąd: " + str(ex))
    
    return render(request, "main/products.html", {"page_id": 1, "products": models.Product.objects.all(),
                                                  "sales": models.Sale.objects.all()})

def manage_product_page(request):
    if not request.user.is_authenticated:
        return redirect(login_page)
    
    product, can_delete = None, False
    
    try:
        if request.method == "POST":
            product_name = request.POST.get("product_name")
            product_desc = request.POST.get("product_desc")
            product_price = request.POST.get("product_price")
            product_amount = request.POST.get("product_amount")
            product_set_id = request.POST.get("product_id")

            if product_set_id:
                    product_id = product_set_id.strip()

            if product_name: 
                product_name = product_name.strip()

            if request.POST.get("submit") == "Zatwierdź":
                if not product_name or len(product_name) < 3:                
                    raise Exception("Nieprawidłowa nazwa produktu.")
                
                if product_desc:
                    product_desc = product_desc.strip()

                product_price = float(product_price.strip())
                product_amount = int(product_amount.strip())

                if product_price < 0 or product_amount < 0:
                    raise Exception("Nieprawidłowa wartość produktu.")
                    
                if not product_set_id:
                    product_id_rand = list(product_name)
                    random.shuffle(product_id_rand)
                    product_id_rand = ''.join(product_id_rand)
                    product_id = hashlib.shake_128(product_id_rand.encode('utf-8')).hexdigest(length=32)

                    try:
                        models.Product.objects.get(id=product_id)
                    except:
                        pass
                    else:
                        raise Exception("Podany produkt już istnieje.")
                    
                    nprod = models.Product.objects.create(id=product_id, name=product_name, description=product_desc, price=product_price, amount=product_amount, user_added_id_id=request.user.id)
                else:
                    nprod = models.Product.objects.get(id=product_set_id)
                    nprod.name = product_name
                    nprod.description = product_desc
                    nprod.price = product_price
                    nprod.amount = product_amount

                nprod.save()

                return redirect(products_page)
            elif request.POST.get("submit") in ["Usuń", "Sprzedaj"]:
                nprod = models.Product.objects.get(id=product_set_id)

                if request.POST.get("submit") == "Usuń":
                    nprod.delete()
                else:
                    product_amount = int(product_amount)
                    if product_amount > nprod.amount or product_amount < 1:
                        raise Exception("Nieprawidłowa ilość produktu.")
                    
                    nprod.amount -= product_amount

                    nsale_id = ''.join(random.SystemRandom().choice(string.ascii_uppercase + product_set_id + string.digits) for _ in range(64))
                    nsale = models.Sale.objects.create(id=nsale_id, amount=product_amount, date=timezone.now(), product_id=nprod, user_sold_id=request.user)

                    nsale.save()
                    nprod.save()

                return redirect(products_page)
    except Exception as ex:
        messages.error(request, "Błąd: " + str(ex))

    try:
        product = models.Product.objects.filter(id=request.GET.get("id")).first()
        can_delete = product.user_added_id.username == request.user.username or request.user.is_staff
    except:
        product = None
    
    return render(request, "main/manageproduct.html", {"page_id": 1, "productvar": product, "can_delete": can_delete})

def reports_page(request):
    if not request.user.is_authenticated:
        return redirect(login_page)
    
    if request.method == "POST":
        try:
            try:
                product = models.Product.objects.get(id=request.POST.get("product_id").strip())
            except:
                raise Exception("Nie znaleziono produktu.")

            buffer = io.BytesIO()
            p = canvas.Canvas(buffer)

            p.setTitle("Raport produktu")
            p.setAuthor(request.user.username)
            p.setProducer("Florex Magazyn")
            p.setSubject("Produkt")

            p.setFont("Segoe UI", 15)
            p.setFillColorRGB(0.1, 0.6, 0.1)
            p.drawCentredString(300, 800, product.name)

            p.setFontSize(10)

            p.setFillColorRGB(0.4, 0.4, 0.4)
            p.drawString(50, 750, 'Stworzony przez: ')
            p.setFillColorRGB(0, 0, 0)
            p.drawString(200, 750, product.user_added_id.username)

            p.setFillColorRGB(0.4, 0.4, 0.4)
            p.drawString(50, 725, 'Ilość w magazynie: ')
            p.setFillColorRGB(0, 0, 0)
            p.drawString(200, 725, str(product.amount))

            p.setFillColorRGB(0.4, 0.4, 0.4)
            p.drawString(50, 700, 'Cena za sztukę: ')
            p.setFillColorRGB(0, 0, 0)
            p.drawString(200, 700, ("%.2f" % (product.price)) + " zł")

            sold_count = mods.get_product_sold_count(product)

            p.setFillColorRGB(0.4, 0.4, 0.4)
            p.drawString(50, 675, 'Sprzedano: ')
            p.setFillColorRGB(0, 0, 0)
            p.drawString(200, 675, str(sold_count))

            p.setFillColorRGB(0.4, 0.4, 0.4)
            p.drawString(50, 650, 'Łączny zysk: ')
            p.setFillColorRGB(0, 0, 0)
            p.drawString(200, 650, ("%.2f" % (product.price * sold_count)) + " zł")

            ytop = 625

            if product.description and len(product.description) > 0:
                p.setFillColorRGB(0.4, 0.4, 0.4)
                p.drawString(50, 625, 'Opis: ')
                p.setFillColorRGB(0, 0, 0)
                txt = textwrap.fill(product.description, 80)
                textobject = p.beginText(200, 625)
                for line in txt.splitlines(False):
                    textobject.textLine(line)
                    ytop -= 25
                p.drawText(textobject)

            try:
                wikipedia.set_lang("pl")
                wikitext = wikipedia.summary(product.name, sentences=2)
            except:
                wikitext = None

            if request.POST.get("wiki") and wikitext and len(wikitext) > 0:
                p.setFillColorRGB(0.4, 0.4, 0.4)
                p.drawString(50, ytop, 'Strzeszczenie z Wikipedii: ')
                p.setFillColorRGB(0, 0, 0)
                txt = textwrap.fill(wikitext, 80)
                textobject = p.beginText(200, ytop)
                for line in txt.splitlines(False):
                    textobject.textLine(line)
                    ytop -= 25
                p.drawText(textobject)

            comment_text = request.POST.get("comment")
            if comment_text and len(comment_text.strip()) > 0:
                comment_text = comment_text.strip()
                p.setFillColorRGB(0.4, 0.4, 0.4)
                p.drawString(50, ytop, 'Komentarz: ')
                p.setFillColorRGB(0, 0, 0)
                txt = textwrap.fill(comment_text, 80)
                textobject = p.beginText(200, ytop)
                for line in txt.splitlines(False):
                    textobject.textLine(line)
                    ytop -= 25
                p.drawText(textobject)

            p.setFillColorRGB(0.4, 0.4, 0.4)
            p.drawString(50, 50, "System Florex Magazyn | " + timezone.now().strftime("%d.%m.%Y %H:%M:%S"))

            p.showPage()
            p.save()
            buffer.seek(0)

            return FileResponse(buffer, as_attachment=True, filename='produkt-'+product.id[-10:]+'.pdf')
        except Exception as ex:
            messages.error(request, "Błąd: " + str(ex))
    
    return render(request, "main/reports.html", {"page_id": 2})

def accounts_page(request):
    if not request.user.is_authenticated:
        return redirect(login_page)
    
    if request.method == "POST":
        password1 = request.POST.get("password1").strip()
        password2 = request.POST.get("password2").strip()
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")

        if first_name: first_name = first_name.strip()
        if last_name: last_name = last_name.strip()

        if password1 != password2:
            messages.error(request, "Hasła są różne.")
            valid_all = False
        else:
            valid_all = True

        if len(password1) > 0:
            try:
                password_validation.validate_password(password=password1)
            except:
                messages.error(request, "Niepoprawne hasło.")
                valid_all = False

        if valid_all:
            try:
                existing_user = get_user_model().objects.get(username=request.user.username)
                existing_user.first_name = first_name
                existing_user.last_name = last_name
                if len(password1) > 0:
                    existing_user.set_password(password1)
                existing_user.save()

                return redirect(accounts_page)
            except Exception as ex:
                messages.error(request, "Błąd: " + ex)
    
    if request.user.is_staff:
        users = get_user_model().objects.all()
        activeusers = mods.get_all_logged_in_users()
    else:
        users, activeusers = [], []
    
    return render(request, "main/accounts.html", {"page_id": 3, "users": users, "activeusers": activeusers})

def manage_user_page(request):
    if not request.user.is_authenticated:
        return redirect(login_page)
    
    if not request.user.is_staff:
        return redirect(accounts_page)
    
    if request.method == "POST":
        password1 = request.POST.get("password1").strip()
        password2 = request.POST.get("password2").strip()

        username = request.POST.get("username")
        if username: 
            username = username.strip()
        else:
            messages.error(request, "Niepoprawna nazwa użytkownika.")
            valid_all = False

        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        is_staff = True if request.POST.get("user_staff") else False

        if first_name: first_name = first_name.strip()
        if last_name: last_name = last_name.strip()

        try:
            existing_user = get_user_model().objects.get(username=username)
        except Exception:
            existing_user = None

        if password1 != password2:
            messages.error(request, "Hasła są różne.")
            valid_all = False
        else:
            valid_all = True

        if not existing_user or len(password1) > 0:
            try:
                password_validation.validate_password(password=password1)
            except:
                messages.error(request, "Niepoprawne hasło.")
                valid_all = False

        if valid_all:
            if request.POST.get("submit") == "Usuń":
                if not existing_user:
                    messages.error(request, "Użytkownik " + username + " nie istnieje.")
                else:
                    try:
                        existing_user.delete()
                        return redirect(accounts_page)
                    except Exception as ex:
                        messages.error(request, "Błąd: " + str(ex))
            elif request.POST.get("submit") == "Zatwierdź":
                if not existing_user:
                    try:
                        existing_user = User.objects.create_user(username=username, password=password1, first_name=first_name, last_name=last_name, is_staff=is_staff)
                        existing_user.save()

                        return redirect(accounts_page)
                    except Exception as ex:
                        messages.info(request, "Błąd: " + str(ex))
                else:
                    try:
                        existing_user.first_name = first_name
                        existing_user.last_name = last_name
                        existing_user.is_staff = is_staff
                        if len(password1) > 0:
                            existing_user.set_password(password1)
                        existing_user.save()

                        return redirect(accounts_page)
                    except Exception as ex:
                        messages.error(request, "Błąd: " + str(ex))
    
    try:
        uservar = get_user_model().objects.get(username=request.GET.get("name"))
    except Exception:
        uservar = None
    
    if uservar and uservar in mods.get_all_logged_in_users() and request.GET.get("name"):
        return redirect(accounts_page)
    
    return render(request, "main/manageuser.html", {"page_id": 3, "uservar": uservar})