"""Forms for the server-rendered developer flow (DESIGN.md §8).

The form renders the submission/edit fields and surfaces **per-field** errors, but it is
**not** the validator of record — ``apps.catalog.services`` is. The page view calls the
service and maps any loud service error back onto the matching form field, so the human
form and the API enforce exactly the same invariants (one source of truth).

Screenshots are multiple-file uploads, which Django forms do not model cleanly, so the
page view reads them from ``request.FILES`` and lets the service validate them (§9).
"""

from django import forms

from apps.catalog import facets
from apps.taxonomy import selectors as taxonomy

# The form value that encodes one chosen facet value (app-page-redesign DESIGN.md §8): the
# service speaks ``(facet, value)`` pairs, the HTML control speaks one string per checkbox, so
# we join them with this separator and split on it. Kept here as the one place the encoding lives.
FACET_VALUE_SEPARATOR = ":"


def facet_choice_groups() -> list[tuple[str, list[tuple[str, str]]]]:
    """Grouped ``facets`` choices fed straight from the registry (one source of truth, G6).

    Each facet is an optgroup; each value is ``"<facet>:<value>"`` → its label. Changing the
    registry changes the choices, so the UI vocabulary can never drift from ``facets.FACETS``.
    """
    return [
        (
            facet_def.label,
            [
                (f"{facet_def.key}{FACET_VALUE_SEPARATOR}{value.key}", value.label)
                for value in facet_def.values
            ],
        )
        for facet_def in facets.FACETS.values()
    ]


class SubmissionForm(forms.Form):
    """Name, description, URL, tag picker, and the optional marketing fields (§8).

    The marketing fields (``tagline``/``deep_dive``/``facets``/``demo_clip_alt``) are all
    optional — the required submission floor is unchanged. The demo-clip **file** is read from
    ``request.FILES`` by the view (like screenshots), not modelled here; ``demo_clip_alt`` is.
    """

    name = forms.CharField(max_length=120)
    description = forms.CharField(widget=forms.Textarea)
    url = forms.URLField(max_length=2000, assume_scheme="https")
    tags = forms.MultipleChoiceField(choices=())
    tagline = forms.CharField(max_length=300, required=False)
    deep_dive = forms.CharField(widget=forms.Textarea, required=False)
    facets = forms.MultipleChoiceField(choices=(), required=False)
    demo_clip_alt = forms.CharField(max_length=200, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The picker only ever offers active tags, so the closed vocabulary (AC4) is
        # visible in the UI; the service re-checks every id at the write boundary.
        self.fields["tags"].choices = [
            (str(tag.id), tag.label) for tag in taxonomy.list_active_tags()
        ]
        # Facet choices come from the code-fixed registry, not a hardcoded list (G6).
        self.fields["facets"].choices = facet_choice_groups()
