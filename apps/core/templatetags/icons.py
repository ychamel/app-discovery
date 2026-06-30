from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def icon(name: str) -> str:
    """
    Renders an inline SVG icon from core/icons/{name}.svg.
    If the icon does not exist, raises TemplateDoesNotExist to fail loudly in dev.
    """
    template_name = f"core/icons/{name}.svg"
    # render_to_string will raise TemplateDoesNotExist if not found
    html = render_to_string(template_name)
    return mark_safe(html.strip())
