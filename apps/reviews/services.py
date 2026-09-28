"""Review creation rules + rating summaries."""
from __future__ import annotations

from django.db.models import Avg, Count

from apps.bookings.models import Booking, BookingStatus

from .models import Review


class ReviewError(Exception):
    pass


def create_review(*, customer, booking: Booking, rating: int, comment: str = "") -> Review:
    if booking.customer_id != customer.id:
        raise ReviewError("You can only review your own bookings.")
    if booking.status != BookingStatus.COMPLETED:
        raise ReviewError("You can review only completed appointments.")
    if hasattr(booking, "review"):
        raise ReviewError("You've already reviewed this appointment.")
    if not (1 <= int(rating) <= 5):
        raise ReviewError("Rating must be between 1 and 5.")

    review = Review.objects.create(
        customer=customer,
        professional=booking.professional,
        booking=booking,
        rating=rating,
        comment=comment.strip(),
    )
    from apps.notifications.services import notify_new_review

    notify_new_review(review)
    return review


def rating_summary(professional) -> dict:
    """Average, count and 1–5 distribution for a professional's reviews."""
    qs = Review.objects.filter(professional=professional)
    agg = qs.aggregate(avg=Avg("rating"), count=Count("id"))
    distribution = {star: 0 for star in range(5, 0, -1)}
    for row in qs.values("rating").annotate(n=Count("id")):
        distribution[row["rating"]] = row["n"]
    return {
        "average": round(agg["avg"], 1) if agg["avg"] is not None else None,
        "count": agg["count"],
        "distribution": distribution,
    }
