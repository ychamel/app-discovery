"""Forms for the account surfaces (DESIGN.md §9).

Validation lives here so views stay thin and every surface validates input the same
way (one source of truth for "what is a valid email / display name").
"""

from django import forms


class RegisterForm(forms.Form):
    """Registration input: an email and a non-empty display name (AC1)."""

    email = forms.EmailField()
    display_name = forms.CharField(max_length=80, min_length=1, strip=True)


class EmailForm(forms.Form):
    """Sign-in / resend input: an email only (AC3, generic response — DESIGN.md §10)."""

    email = forms.EmailField()


class DisplayNameForm(forms.Form):
    """Profile edit input: a non-empty, bounded display name (AC7)."""

    display_name = forms.CharField(max_length=80, min_length=1, strip=True)
