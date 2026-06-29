"""HTTP surfaces for the catalog (DESIGN.md §5c) — developer + review JSON API.

Two audiences, one logic core:
  * **Developer API** (T-09) — session + ``developer`` role; every app-scoped route is
    owner-scoped (``404`` on someone else's app, no enumeration).
  * **Review API** (T-10) — session + ``admin`` role; identical handling for every app (AC3).

Every view is a **thin projection** of ``apps.catalog.services`` (writes) and
``apps.catalog.selectors`` (reads): it parses input, calls the service/selector, and maps
the loud service errors to status codes. It contains **no ORM access or business logic**.
The server-rendered human pages live in ``pages.py`` (T-11/T-12) and post to the *same*
services, so there is no second source of truth.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import roles
from apps.accounts.permissions import HasRole, require_role
from apps.catalog import notifications, selectors, services
from apps.catalog.errors import (
    InvalidFacetError,
    InvalidTagError,
    InvalidTransitionError,
    MediaLimitError,
)
from apps.catalog.forms import FACET_VALUE_SEPARATOR, SubmissionForm
from apps.catalog.serializers import (
    AppSerializer,
    DecisionResultSerializer,
    ReviewQueueRowSerializer,
)
from apps.core import observability


# --- Shared helpers ----------------------------------------------------------
def _owned_or_404(request, app_id):
    """Fetch the caller's app or raise 404 — non-ownership is indistinguishable (AC8)."""
    app = selectors.get_owned_app(request.user, app_id)
    if app is None:
        raise NotFound("No such app.")
    return app


def _app_response(app, *, status_code=status.HTTP_200_OK) -> Response:
    return Response(AppSerializer(app).data, status=status_code)


def _service_call(func, *args, **kwargs) -> Response | None:
    """Run a write service, mapping its loud errors to status codes (DESIGN.md §5c/§10).

    Returns a ``Response`` when the call failed (so the caller returns it), or ``None`` on
    success (so the caller renders its own success shape).
    """
    try:
        func(*args, **kwargs)
        return None
    except DjangoValidationError as exc:
        return Response(_field_errors(exc), status=status.HTTP_400_BAD_REQUEST)
    except (InvalidTagError, InvalidFacetError, MediaLimitError) as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except InvalidTransitionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)


def _field_errors(exc: DjangoValidationError) -> dict:
    """Turn a Django ValidationError into a per-field JSON body (falls back to detail)."""
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return {"detail": exc.messages}


# --- Developer API (endpoints 1–8; AC1/AC2/AC4/AC7/AC8) ----------------------
class _DeveloperView(APIView):
    """Base: session + developer role (AC2). Unauthenticated → 403 (matches ITX-9)."""

    permission_classes = [HasRole(roles.DEVELOPER)]


class AppCreateView(_DeveloperView):
    """POST /api/apps — submit a new app, multipart (endpoint 1, AC1)."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        observability.increment(observability.SUBMISSION_STARTED)
        try:
            app = services.submit_app(
                request.user,
                name=request.data.get("name"),
                description=request.data.get("description"),
                url=request.data.get("url"),
                tag_ids=request.data.getlist("tag_ids"),
                media=request.FILES.getlist("media"),
                tagline=request.data.get("tagline", ""),
                deep_dive=request.data.get("deep_dive", ""),
                facet_values=_facet_pairs(request.data),
                demo_clip=request.FILES.get("demo_clip"),
                demo_clip_alt=request.data.get("demo_clip_alt", ""),
            )
        except DjangoValidationError as exc:
            return Response(_field_errors(exc), status=status.HTTP_400_BAD_REQUEST)
        except (InvalidTagError, InvalidFacetError, MediaLimitError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        observability.increment(observability.SUBMISSION_COMPLETED)
        return _app_response(app, status_code=status.HTTP_201_CREATED)


class MyAppsView(_DeveloperView):
    """GET /api/apps/mine — the caller's apps, any status (endpoint 2)."""

    def get(self, request):
        apps = selectors.list_owned_apps(request.user)
        return Response(AppSerializer(apps, many=True).data)


class AppDetailView(_DeveloperView):
    """GET/PATCH /api/apps/{id} — read or edit one owned app (endpoints 3, 4)."""

    def get(self, request, app_id):
        return _app_response(_owned_or_404(request, app_id))

    def patch(self, request, app_id):
        app = _owned_or_404(request, app_id)
        edits = _supplied_edits(request.data)
        # A replacement clip rides multipart FILES, not the JSON/form body — wire it in so the
        # API can set/replace the clip too (the create path already reads request.FILES).
        if "demo_clip" in request.FILES:
            edits["demo_clip"] = request.FILES["demo_clip"]
        failure = _service_call(services.edit_app, app, **edits)
        if failure is not None:
            return failure
        app.refresh_from_db()
        return _app_response(app)


class AppMediaView(_DeveloperView):
    """POST /api/apps/{id}/media — add one screenshot (endpoint 5)."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, app_id):
        app = _owned_or_404(request, app_id)
        image = request.FILES.get("image")
        if image is None:
            return Response(
                {"image": "An image file is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            media = services.add_media(app, image, alt_text=request.data.get("alt_text", ""))
        except MediaLimitError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        from apps.catalog.serializers import MediaSerializer

        return Response(MediaSerializer(media).data, status=status.HTTP_201_CREATED)


class AppMediaItemView(_DeveloperView):
    """DELETE /api/apps/{id}/media/{mid} — remove one screenshot (endpoint 6)."""

    def delete(self, request, app_id, media_id):
        app = _owned_or_404(request, app_id)
        media = app.media.filter(pk=media_id).first()
        if media is None:
            raise NotFound("No such media.")
        try:
            services.remove_media(media)
        except MediaLimitError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AppWithdrawView(_DeveloperView):
    """POST /api/apps/{id}/withdraw — leave the catalog/queue (endpoint 7, AC8)."""

    def post(self, request, app_id):
        app = _owned_or_404(request, app_id)
        failure = _service_call(services.withdraw_app, app)
        if failure is not None:
            return failure
        app.refresh_from_db()
        return _app_response(app)


class AppResubmitView(_DeveloperView):
    """POST /api/apps/{id}/resubmit — re-offer a rejected/withdrawn app (endpoint 8, AC7)."""

    def post(self, request, app_id):
        app = _owned_or_404(request, app_id)
        failure = _service_call(services.resubmit_app, app)
        if failure is not None:
            return failure
        app.refresh_from_db()
        return _app_response(app)


def _supplied_edits(data) -> dict:
    """Extract only the edit fields actually present in the request body.

    Absent keys are left out so ``edit_app`` leaves them unchanged (the ``_UNSET`` contract);
    a present ``facet_values`` (even empty) means "replace the set", including clearing it.
    """
    edits: dict = {}
    if "name" in data:
        edits["name"] = data.get("name")
    if "description" in data:
        edits["description"] = data.get("description")
    if "url" in data:
        edits["url"] = data.get("url")
    if "tag_ids" in data:
        edits["tag_ids"] = (
            data.getlist("tag_ids") if hasattr(data, "getlist") else data.get("tag_ids")
        )
    if "tagline" in data:
        edits["tagline"] = data.get("tagline")
    if "deep_dive" in data:
        edits["deep_dive"] = data.get("deep_dive")
    if "facet_values" in data:
        edits["facet_values"] = _facet_pairs(data)
    if "demo_clip_alt" in data:
        edits["demo_clip_alt"] = data.get("demo_clip_alt")
    return edits


def _facet_pairs(data) -> list[tuple[str, str]]:
    """Parse the request's ``facet_values`` into the service's ``(facet, value)`` pairs.

    Accepts the form/HTML encoding (a list of ``"<facet>:<value>"`` strings) **and** an
    already-split ``[facet, value]`` pair list (JSON). The service validates each pair against
    the registry, so a malformed value here simply surfaces as a loud ``InvalidFacetError``.
    """
    raw = data.getlist("facet_values") if hasattr(data, "getlist") else data.get("facet_values")
    return _pairs_from_encoded(raw)


def _pairs_from_encoded(values) -> list[tuple[str, str]]:
    """Turn ``"<facet>:<value>"`` strings (or ``[facet, value]`` pairs) into service pairs."""
    pairs: list[tuple[str, str]] = []
    for item in values or []:
        if isinstance(item, str):
            facet, _, value = item.partition(FACET_VALUE_SEPARATOR)
            pairs.append((facet, value))
        else:
            facet, value = item
            pairs.append((str(facet), str(value)))
    return pairs


# --- Review API (endpoints 9–10; AC3/AC5/AC6/AC7) ----------------------------
class _AdminView(APIView):
    """Base: session + admin role (AC5). Identical handling for every app (AC3)."""

    permission_classes = [HasRole(roles.ADMIN)]


class ReviewQueueView(_AdminView):
    """GET /api/review/queue — pending apps FIFO with the duplicate hint (endpoint 9)."""

    def get(self, request):
        rows = selectors.list_review_queue()
        return Response(ReviewQueueRowSerializer(rows, many=True).data)


class ReviewDecisionView(_AdminView):
    """POST /api/apps/{id}/decision — accept or reject a pending app (endpoint 10).

    Routes to ``accept_app``/``reject_app`` by ``outcome``; a reject with 0 or an unknown
    criterion is a ``400`` (the closed enum makes a taste rejection a 400, AC6). After the
    decision commits, the developer is notified (T-08) — outside the decision transaction.
    """

    def post(self, request, app_id):
        app = selectors.get_app_for_review(app_id)
        if app is None:
            raise NotFound("No such app.")

        outcome = request.data.get("outcome")
        if outcome == "accepted":
            decision_or_error = self._accept(app, request.user)
        elif outcome == "rejected":
            decision_or_error = self._reject(app, request.user, request.data)
        else:
            return Response(
                {"outcome": "Must be 'accepted' or 'rejected'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if isinstance(decision_or_error, Response):
            return decision_or_error
        notifications.notify_decision(decision_or_error)
        return Response(DecisionResultSerializer(decision_or_error).data)

    def _accept(self, app, reviewer):
        try:
            return services.accept_app(app, reviewer)
        except InvalidTransitionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    def _reject(self, app, reviewer, data):
        try:
            return services.reject_app(
                app,
                reviewer,
                failed_criteria=data.get("failed_criteria") or [],
                note=data.get("note", ""),
            )
        except DjangoValidationError as exc:
            return Response(_field_errors(exc), status=status.HTTP_400_BAD_REQUEST)
        except InvalidTransitionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)


# --- Server-rendered developer pages (DESIGN.md §8; AC1/AC7/AC8) -------------
# These post to the *same* services/selectors as the API above — no second source of
# truth. They are developer-role-gated and owner-scoped exactly like the API.
@require_role(roles.DEVELOPER)
@require_http_methods(["GET", "POST"])
def submit_page(request):
    """GET/POST /submit — the submission form (AC1).

    On an invalid submission the page re-renders with per-field errors and **no row is
    created**; on success it redirects to the new app's detail showing ``pending``.
    """
    if request.method == "GET":
        observability.increment(observability.SUBMISSION_STARTED)
        return render(request, "catalog/submit.html", {"form": SubmissionForm()})

    form = SubmissionForm(request.POST)
    media = request.FILES.getlist("media")
    if form.is_valid():
        try:
            app = services.submit_app(
                request.user,
                name=form.cleaned_data["name"],
                description=form.cleaned_data["description"],
                url=form.cleaned_data["url"],
                tag_ids=form.cleaned_data["tags"],
                media=media,
                tagline=form.cleaned_data["tagline"],
                deep_dive=form.cleaned_data["deep_dive"],
                facet_values=_pairs_from_encoded(form.cleaned_data["facets"]),
                demo_clip=request.FILES.get("demo_clip"),
                demo_clip_alt=form.cleaned_data["demo_clip_alt"],
            )
        except (DjangoValidationError, InvalidTagError, InvalidFacetError, MediaLimitError) as exc:
            _attach_service_errors(form, exc)
        else:
            observability.increment(observability.SUBMISSION_COMPLETED)
            return redirect("catalog:app-detail", app_id=app.id)
    return render(request, "catalog/submit.html", {"form": form}, status=400)


@require_role(roles.DEVELOPER)
@require_http_methods(["GET"])
def my_apps_page(request):
    """GET /apps — the developer's apps with status badges; rejected apps show reasons (AC7)."""
    apps = selectors.list_owned_apps(request.user)
    decorated = sorted(
        _decorate_apps(apps), key=lambda a: _MY_APPS_STATUS_ORDER.get(a["status"], 99)
    )
    return render(request, "catalog/my_apps.html", {"apps": decorated})


@require_role(roles.DEVELOPER)
@require_http_methods(["GET", "POST"])
def app_detail_page(request, app_id):
    """GET/POST /apps/{id} — view/edit/withdraw/resubmit one owned app (AC7/AC8).

    POST dispatches on an ``action`` field to the matching service. A non-owner gets the
    same 404 as the API (no enumeration).
    """
    app = selectors.get_owned_app(request.user, app_id)
    if app is None:
        raise Http404("No such app.")

    if request.method == "POST":
        return _handle_detail_action(request, app)
    return _render_detail(request, app, SubmissionForm(initial=_form_initial(app)))


def _handle_detail_action(request, app):
    action = request.POST.get("action")
    if action == "withdraw":
        return _run_lifecycle(request, app, services.withdraw_app)
    if action == "resubmit":
        return _run_lifecycle(request, app, services.resubmit_app)
    if action == "remove_media":
        return _remove_media_action(request, app)
    if action == "add_media":
        return _add_media_action(request, app)
    return _edit_action(request, app)


def _edit_action(request, app):
    form = SubmissionForm(request.POST)
    if form.is_valid():
        edits = {
            "name": form.cleaned_data["name"],
            "description": form.cleaned_data["description"],
            "url": form.cleaned_data["url"],
            "tag_ids": form.cleaned_data["tags"],
            "tagline": form.cleaned_data["tagline"],
            "deep_dive": form.cleaned_data["deep_dive"],
            "facet_values": _pairs_from_encoded(form.cleaned_data["facets"]),
            "demo_clip_alt": form.cleaned_data["demo_clip_alt"],
        }
        # Only touch the clip when the developer actually uploads one — a metadata edit must
        # never wipe an existing clip (a missing file is "unchanged", not "remove").
        uploaded_clip = request.FILES.get("demo_clip")
        if uploaded_clip is not None:
            edits["demo_clip"] = uploaded_clip
        try:
            services.edit_app(app, **edits)
        except (DjangoValidationError, InvalidTagError, InvalidFacetError, MediaLimitError) as exc:
            _attach_service_errors(form, exc)
        else:
            return redirect("catalog:app-detail", app_id=app.id)
    return _render_detail(request, app, form, status_code=400)


def _add_media_action(request, app):
    image = request.FILES.get("image")
    form = SubmissionForm(initial=_form_initial(app))
    if image is None:
        return _render_detail(
            request, app, form, error="Choose an image to upload.", status_code=400
        )
    try:
        services.add_media(app, image, alt_text=request.POST.get("alt_text", ""))
    except MediaLimitError as exc:
        return _render_detail(request, app, form, error=str(exc), status_code=400)
    return redirect("catalog:app-detail", app_id=app.id)


def _remove_media_action(request, app):
    media = app.media.filter(pk=request.POST.get("media_id")).first()
    form = SubmissionForm(initial=_form_initial(app))
    if media is None:
        raise Http404("No such media.")
    try:
        services.remove_media(media)
    except MediaLimitError as exc:
        return _render_detail(request, app, form, error=str(exc), status_code=400)
    return redirect("catalog:app-detail", app_id=app.id)


def _run_lifecycle(request, app, func):
    form = SubmissionForm(initial=_form_initial(app))
    try:
        func(app)
    except InvalidTransitionError as exc:
        return _render_detail(request, app, form, error=str(exc), status_code=409)
    return redirect("catalog:app-detail", app_id=app.id)


def _render_detail(request, app, form, *, error=None, status_code=200):
    app.refresh_from_db()
    context = {
        "app": _decorate_apps([app])[0],
        "form": form,
        "error": error,
    }
    return render(request, "catalog/app_detail.html", context, status=status_code)


def _decorate_apps(apps):
    """Attach the resolved tags + latest decision each template needs (read-shaping only)."""
    return [AppSerializer(app).data for app in apps]


# Presentation priority for My Apps page grouping: live apps first, then in-review, then withdrawn.
_MY_APPS_STATUS_ORDER = {"accepted": 0, "pending": 1, "rejected": 2, "withdrawn": 3}


def _form_initial(app) -> dict:
    return {
        "name": app.name,
        "description": app.description,
        "url": app.url,
        "tags": [str(app_tag.tag_id) for app_tag in app.app_tags.all()],
        "tagline": app.tagline,
        "deep_dive": app.deep_dive,
        "facets": [
            f"{facet.facet}{FACET_VALUE_SEPARATOR}{facet.value}"
            for facet in app.app_facets.all()
        ],
        "demo_clip_alt": app.demo_clip_alt,
    }


def _attach_service_errors(form, exc) -> None:
    """Map a loud service error back onto the matching form field (one source of truth)."""
    if isinstance(exc, DjangoValidationError) and hasattr(exc, "message_dict"):
        for field, messages in exc.message_dict.items():
            target = field if field in form.fields else None
            for message in messages:
                form.add_error(target, message)
        return
    # Tag/media errors are not field-keyed — surface them as a non-field error.
    form.add_error(None, str(exc))


# --- Server-rendered admin review page (DESIGN.md §8; AC3/AC5/AC6) -----------
@require_role(roles.ADMIN)
@require_http_methods(["GET"])
def review_queue_page(request):
    """GET /review — the FIFO queue of pending apps with the duplicate hint (AC3)."""
    rows = selectors.list_review_queue()
    return render(request, "catalog/review_queue.html", {"rows": rows})


@require_role(roles.ADMIN)
@require_http_methods(["GET", "POST"])
def review_detail_page(request, app_id):
    """GET/POST /review/{id} — inspect one app and accept/reject it (AC5/AC6).

    The reject form can only submit the five fixed floors; a reject with no floor selected
    is refused with a per-field error — the UI cannot express a taste rejection (AC6).
    """
    app = selectors.get_app_for_review(app_id)
    if app is None:
        raise Http404("No such app.")
    if request.method == "POST":
        return _handle_review_decision(request, app)
    return _render_review_detail(request, app)


def _handle_review_decision(request, app):
    action = request.POST.get("action")
    try:
        if action == "accept":
            decision = services.accept_app(app, request.user)
        elif action == "reject":
            decision = services.reject_app(
                app,
                request.user,
                failed_criteria=request.POST.getlist("failed_criteria"),
                note=request.POST.get("note", ""),
            )
        else:
            return _render_review_detail(
                request, app, error="Choose accept or reject.", status_code=400
            )
    except DjangoValidationError:
        # A reject with no floor selected (AC6) — re-render asking for ≥1 criterion.
        return _render_review_detail(
            request, app, error="Select at least one failed criterion to reject.", status_code=400
        )
    except InvalidTransitionError as exc:
        return _render_review_detail(request, app, error=str(exc), status_code=409)

    notifications.notify_decision(decision)
    return redirect("catalog:review")


def _render_review_detail(request, app, *, error=None, status_code=200):
    from apps.catalog import gate

    app.refresh_from_db()
    checklist = [
        {"value": criterion.value, "label": criterion.label, "hint": gate.CHECKLIST[criterion]}
        for criterion in gate.Criterion
    ]
    duplicate_hint = len(selectors.apps_sharing_url(app.normalized_url, exclude=app.pk))
    context = {
        "app": AppSerializer(app).data,
        "owner_email": app.owner.email,
        "checklist": checklist,
        "duplicate_hint": duplicate_hint,
        "error": error,
    }
    return render(request, "catalog/review_detail.html", context, status=status_code)
