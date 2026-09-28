"""Customer & professional dashboards.

Every professional view derives the profile from ``request.user`` — a professional
can never touch another professional's data by passing an id.
"""
from __future__ import annotations

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import RedirectView

from apps.accounts.forms import AccountSettingsForm, CustomerProfileForm
from apps.bookings.models import ACTIVE_STATUSES, Booking, BookingStatus
from apps.bookings.services import (
    BookingError,
    cancel_booking,
    complete_booking,
    confirm_booking,
    mark_no_show,
)
from apps.professionals.models import (
    BreakTime,
    DayOff,
    ProfessionalGallery,
    PortfolioImage,
    SalonMember,
    Weekday,
    WorkingHour,
)
from apps.professionals.services import compute_profile_completion, is_open_now
from apps.reviews.models import Review
from apps.reviews.services import rating_summary

from .forms import (
    BarberProfileForm,
    BreakTimeForm,
    DayOffForm,
    GalleryImageForm,
    PortfolioImageForm,
    ProductForm,
    ProfessionalProfileForm,
    SalonMemberForm,
    SalonProfileForm,
    ServiceForm,
)


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------
def professional_required(view):
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_professional and hasattr(request.user, "professional_profile")):
            messages.error(request, "You need a professional account to view that page.")
            return redirect("dashboard:index")
        return view(request, *args, **kwargs)

    return wrapper


def _salon_or_redirect(request):
    prof = request.user.professional_profile
    if not prof.is_salon or not hasattr(prof, "salon_profile"):
        messages.error(request, "That section is for salon accounts only.")
        return None
    return prof


# ---------------------------------------------------------------------------
# Index (role-aware)
# ---------------------------------------------------------------------------
@login_required
def index(request):
    user = request.user
    if user.is_professional and hasattr(user, "professional_profile"):
        return _professional_dashboard(request)
    if user.is_customer:
        return _customer_dashboard(request)
    return render(request, "dashboard/staff_home.html")


def _customer_dashboard(request):
    user = request.user
    bookings = Booking.objects.for_customer(user).select_related(
        "professional", "service", "barber__professional"
    )
    upcoming = [b for b in bookings if b.is_active and not b.is_past][:5]
    ctx = {
        "upcoming": upcoming,
        "recent": bookings[:5],
        "total_bookings": bookings.count(),
        "favorites_count": user.favorites.count(),
    }
    return render(request, "dashboard/customer/index.html", ctx)


def _professional_dashboard(request):
    prof = request.user.professional_profile
    today = timezone.localdate()
    bookings = Booking.objects.for_professional(prof)
    ctx = {
        "professional": prof,
        "today_count": bookings.filter(date=today, status__in=ACTIVE_STATUSES).count(),
        "upcoming_count": bookings.filter(date__gte=today, status__in=ACTIVE_STATUSES).count(),
        "completed_count": bookings.filter(status=BookingStatus.COMPLETED).count(),
        "total_count": bookings.count(),
        "rating": rating_summary(prof),
        "pending": bookings.filter(status=BookingStatus.PENDING).select_related(
            "customer", "service", "barber__professional"
        )[:6],
        "completion": compute_profile_completion(prof),
        "is_open": is_open_now(prof),
    }
    return render(request, "dashboard/professional/index.html", ctx)


# ---------------------------------------------------------------------------
# Profile + onboarding
# ---------------------------------------------------------------------------
def _profile_forms(prof, data=None, files=None):
    profile_form = ProfessionalProfileForm(data, files, instance=prof)
    if prof.is_barber:
        sub_form = BarberProfileForm(data, files, instance=prof.barber_profile, prefix="sub")
    else:
        sub_form = SalonProfileForm(data, files, instance=prof.salon_profile, prefix="sub")
    return profile_form, sub_form


@professional_required
def profile(request):
    prof = request.user.professional_profile
    if request.method == "POST":
        profile_form, sub_form = _profile_forms(prof, request.POST, request.FILES)
        if profile_form.is_valid() and sub_form.is_valid():
            profile_form.save()
            sub_form.save()
            messages.success(request, "Profile updated.")
            return redirect("dashboard:profile")
        messages.error(request, "Please fix the errors below.")
    else:
        profile_form, sub_form = _profile_forms(prof)
    return render(
        request,
        "dashboard/professional/profile.html",
        {"profile_form": profile_form, "sub_form": sub_form, "professional": prof},
    )


@professional_required
def profile_setup(request):
    prof = request.user.professional_profile
    if request.method == "POST":
        profile_form, sub_form = _profile_forms(prof, request.POST, request.FILES)
        if profile_form.is_valid() and sub_form.is_valid():
            profile_form.save()
            sub_form.save()
            messages.success(request, "Saved. Keep going!")
            return redirect("dashboard:profile_setup")
    else:
        profile_form, sub_form = _profile_forms(prof)
    return render(
        request,
        "dashboard/professional/profile_setup.html",
        {
            "profile_form": profile_form,
            "sub_form": sub_form,
            "professional": prof,
            "completion": compute_profile_completion(prof),
        },
    )


# ---------------------------------------------------------------------------
# Appointments + calendar
# ---------------------------------------------------------------------------
@professional_required
def appointments(request):
    prof = request.user.professional_profile
    if request.method == "POST":
        _handle_appointment_action(request, prof)
        return redirect("dashboard:appointments")

    bookings = Booking.objects.for_professional(prof).select_related(
        "customer", "service", "barber__professional"
    )
    status_filter = request.GET.get("status")
    if status_filter in BookingStatus.values:
        bookings = bookings.filter(status=status_filter)
    return render(
        request,
        "dashboard/professional/appointments.html",
        {
            "bookings": bookings,
            "statuses": BookingStatus.choices,
            "current_status": status_filter or "",
        },
    )


def _handle_appointment_action(request, prof):
    booking = get_object_or_404(Booking, pk=request.POST.get("booking"), professional=prof)
    action = request.POST.get("action")
    try:
        if action == "confirm":
            confirm_booking(booking)
        elif action == "complete":
            complete_booking(booking)
        elif action == "no_show":
            mark_no_show(booking)
        elif action == "cancel":
            cancel_booking(booking, by_customer=False)
        else:
            messages.error(request, "Unknown action.")
            return
        messages.success(request, f"Appointment {action.replace('_', ' ')}d.")
    except BookingError as exc:
        messages.error(request, str(exc))


@professional_required
def calendar(request):
    prof = request.user.professional_profile
    today = timezone.localdate()
    bookings = (
        Booking.objects.for_professional(prof)
        .filter(date__gte=today, status__in=ACTIVE_STATUSES)
        .select_related("customer", "service", "barber__professional")
        .order_by("date", "start_time")
    )
    by_date: dict = {}
    for booking in bookings:
        by_date.setdefault(booking.date, []).append(booking)
    return render(
        request,
        "dashboard/professional/calendar.html",
        {"agenda": sorted(by_date.items())},
    )


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
@professional_required
def services(request):
    prof = request.user.professional_profile
    if request.method == "POST":
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.professional = prof
            service.save()
            messages.success(request, "Service added.")
            return redirect("dashboard:services")
    else:
        form = ServiceForm()
    return render(
        request,
        "dashboard/professional/services.html",
        {"services": prof.services.select_related("category"), "form": form},
    )


@professional_required
def service_edit(request, pk):
    prof = request.user.professional_profile
    service = get_object_or_404(prof.services, pk=pk)
    if request.method == "POST":
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "Service updated.")
            return redirect("dashboard:services")
    else:
        form = ServiceForm(instance=service)
    return render(
        request,
        "dashboard/professional/service_form.html",
        {"form": form, "service": service},
    )


@professional_required
def service_delete(request, pk):
    prof = request.user.professional_profile
    service = get_object_or_404(prof.services, pk=pk)
    if request.method == "POST":
        service.delete()
        messages.success(request, "Service removed.")
    return redirect("dashboard:services")


# ---------------------------------------------------------------------------
# Working hours, breaks, days off
# ---------------------------------------------------------------------------
@professional_required
def hours(request):
    prof = request.user.professional_profile
    if request.method == "POST":
        action = request.POST.get("action", "hours")
        if action == "hours":
            _save_hours(request, prof)
            messages.success(request, "Working hours saved.")
        elif action == "add_break":
            form = BreakTimeForm(request.POST)
            if form.is_valid():
                brk = form.save(commit=False)
                brk.professional = prof
                brk.save()
                messages.success(request, "Break added.")
            else:
                messages.error(request, "Could not add break — check the times.")
        elif action == "delete_break":
            prof.break_times.filter(pk=request.POST.get("break_id")).delete()
            messages.success(request, "Break removed.")
        elif action == "add_dayoff":
            form = DayOffForm(request.POST)
            if form.is_valid():
                day = form.save(commit=False)
                day.professional = prof
                try:
                    day.save()
                    messages.success(request, "Day off added.")
                except Exception:
                    messages.error(request, "That date is already marked off.")
            else:
                messages.error(request, "Could not add day off.")
        elif action == "delete_dayoff":
            prof.days_off.filter(pk=request.POST.get("dayoff_id")).delete()
            messages.success(request, "Day off removed.")
        return redirect("dashboard:hours")

    hours_map = {wh.weekday: wh for wh in prof.working_hours.all()}
    week = [(value, label, hours_map.get(value)) for value, label in Weekday.choices]
    return render(
        request,
        "dashboard/professional/hours.html",
        {
            "week": week,
            "breaks": prof.break_times.all(),
            "days_off": prof.days_off.all(),
            "break_form": BreakTimeForm(),
            "dayoff_form": DayOffForm(),
            "weekdays": Weekday.choices,
        },
    )


def _save_hours(request, prof):
    for value, _label in Weekday.choices:
        is_open = request.POST.get(f"open_{value}") == "on"
        start = request.POST.get(f"start_{value}") or None
        end = request.POST.get(f"end_{value}") or None
        # Only keep times when the day is open and both are provided.
        if not is_open or not (start and end):
            start = end = None
            is_open = is_open and False
        WorkingHour.objects.update_or_create(
            professional=prof,
            weekday=value,
            defaults={"is_open": is_open, "start_time": start, "end_time": end},
        )


# ---------------------------------------------------------------------------
# Portfolio & gallery
# ---------------------------------------------------------------------------
@professional_required
def portfolio(request):
    prof = request.user.professional_profile
    if request.method == "POST":
        form = PortfolioImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.professional = prof
            image.save()
            messages.success(request, "Photo added to your portfolio.")
            return redirect("dashboard:portfolio")
        messages.error(request, "Please choose a valid image.")
    else:
        form = PortfolioImageForm()
    return render(
        request,
        "dashboard/professional/portfolio.html",
        {"images": prof.portfolio_images.all(), "form": form},
    )


@professional_required
def portfolio_delete(request, pk):
    prof = request.user.professional_profile
    if request.method == "POST":
        get_object_or_404(prof.portfolio_images, pk=pk).delete()
        messages.success(request, "Photo removed.")
    return redirect("dashboard:portfolio")


@professional_required
def gallery(request):
    prof = request.user.professional_profile
    if request.method == "POST":
        form = GalleryImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.professional = prof
            image.save()
            messages.success(request, "Photo added to your gallery.")
            return redirect("dashboard:gallery")
        messages.error(request, "Please choose a valid image.")
    else:
        form = GalleryImageForm()
    return render(
        request,
        "dashboard/professional/gallery.html",
        {"images": prof.gallery_images.all(), "form": form},
    )


@professional_required
def gallery_delete(request, pk):
    prof = request.user.professional_profile
    if request.method == "POST":
        get_object_or_404(prof.gallery_images, pk=pk).delete()
        messages.success(request, "Photo removed.")
    return redirect("dashboard:gallery")


# ---------------------------------------------------------------------------
# Products (salon only)
# ---------------------------------------------------------------------------
@professional_required
def products(request):
    prof = _salon_or_redirect(request)
    if prof is None:
        return redirect("dashboard:index")
    salon = prof.salon_profile
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.salon = salon
            product.save()
            messages.success(request, "Product added.")
            return redirect("dashboard:products")
    else:
        form = ProductForm()
    return render(
        request,
        "dashboard/professional/products.html",
        {"products": salon.products.select_related("category"), "form": form},
    )


@professional_required
def product_edit(request, pk):
    prof = _salon_or_redirect(request)
    if prof is None:
        return redirect("dashboard:index")
    product = get_object_or_404(prof.salon_profile.products, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated.")
            return redirect("dashboard:products")
    else:
        form = ProductForm(instance=product)
    return render(
        request,
        "dashboard/professional/product_form.html",
        {"form": form, "product": product},
    )


@professional_required
def product_delete(request, pk):
    prof = _salon_or_redirect(request)
    if prof is None:
        return redirect("dashboard:index")
    if request.method == "POST":
        get_object_or_404(prof.salon_profile.products, pk=pk).delete()
        messages.success(request, "Product removed.")
    return redirect("dashboard:products")


# ---------------------------------------------------------------------------
# Salon team
# ---------------------------------------------------------------------------
@professional_required
def team(request):
    prof = _salon_or_redirect(request)
    if prof is None:
        return redirect("dashboard:index")
    salon = prof.salon_profile
    if request.method == "POST":
        action = request.POST.get("action", "add")
        if action == "add":
            form = SalonMemberForm(request.POST)
            if form.is_valid():
                if SalonMember.objects.filter(salon=salon, barber=form.barber).exists():
                    messages.info(request, "That barber is already on your team.")
                elif form.barber.professional_id == prof.id:
                    messages.error(request, "You can't add yourself as a team member.")
                else:
                    SalonMember.objects.create(
                        salon=salon, barber=form.barber, position=form.cleaned_data["position"]
                    )
                    messages.success(request, "Barber added to your team.")
                return redirect("dashboard:team")
            messages.error(request, form.errors.get("barber_email", ["Could not add barber."])[0])
            return redirect("dashboard:team")
        member = get_object_or_404(SalonMember, pk=request.POST.get("member"), salon=salon)
        if action == "toggle":
            member.is_active = not member.is_active
            member.save(update_fields=["is_active"])
            messages.success(request, "Team member updated.")
        elif action == "remove":
            member.delete()
            messages.success(request, "Team member removed.")
        return redirect("dashboard:team")

    return render(
        request,
        "dashboard/professional/team.html",
        {
            "members": SalonMember.objects.filter(salon=salon).select_related("barber__professional__user"),
            "form": SalonMemberForm(),
        },
    )


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------
@professional_required
def reviews(request):
    prof = request.user.professional_profile
    return render(
        request,
        "dashboard/professional/reviews.html",
        {
            "reviews": Review.objects.filter(professional=prof).select_related(
                "customer", "booking__service"
            ),
            "summary": rating_summary(prof),
        },
    )


# ---------------------------------------------------------------------------
# Settings (all roles)
# ---------------------------------------------------------------------------
@login_required
def settings_view(request):
    user = request.user
    customer_form = None
    if request.method == "POST":
        account_form = AccountSettingsForm(request.POST, request.FILES, instance=user)
        forms_valid = account_form.is_valid()
        if user.is_customer and hasattr(user, "customer_profile"):
            customer_form = CustomerProfileForm(request.POST, instance=user.customer_profile)
            forms_valid = forms_valid and customer_form.is_valid()
        if forms_valid:
            account_form.save()
            if customer_form:
                customer_form.save()
            messages.success(request, "Settings saved.")
            return redirect("dashboard:settings")
    else:
        account_form = AccountSettingsForm(instance=user)
        if user.is_customer and hasattr(user, "customer_profile"):
            customer_form = CustomerProfileForm(instance=user.customer_profile)
    return render(
        request,
        "dashboard/settings.html",
        {"account_form": account_form, "customer_form": customer_form},
    )


# ---------------------------------------------------------------------------
# Convenience redirects for the /dashboard/... URL structure
# ---------------------------------------------------------------------------
class DashboardMessagesRedirect(RedirectView):
    pattern_name = "messaging:index"


class DashboardNotificationsRedirect(RedirectView):
    pattern_name = "notifications:index"
