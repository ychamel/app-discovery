"""Forms for the server-rendered developer flow (DESIGN.md §8).

The form renders the submission/edit fields and surfaces **per-field** errors, but it is
**not** the validator of record — ``apps.catalog.services`` is. The page view calls the
service and maps any loud service error back onto the matching form field, so the human
form and the API enforce exactly the same invariants (one source of truth).

Screenshots are multiple-file uploads, which Django forms do not model cleanly, so the
page view reads them from ``request.FILES`` and lets the service validate them (§9).
"""

from django import forms

from apps.taxonomy import selectors as taxonomy


class SubmissionForm(forms.Form):
    """Name, description, URL, and a tag picker fed by the active vocabulary (§8)."""

    name = forms.CharField(max_length=120)
    description = forms.CharField(widget=forms.Textarea)
    url = forms.URLField(max_length=2000, assume_scheme="https")
    tags = forms.MultipleChoiceField(choices=())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The picker only ever offers active tags, so the closed vocabulary (AC4) is
        # visible in the UI; the service re-checks every id at the write boundary.
        self.fields["tags"].choices = [
            (str(tag.id), tag.label) for tag in taxonomy.list_active_tags()
        ]
