from urllib.parse import urlparse

def get_site_name(url: str) -> str:
    domain = urlparse(url).netloc.replace("www.", "")
    domain_parts = domain.split('.')
    if len(domain_parts) > 1:
        name = domain_parts[-2]  # e.g., "sefaria" from "sefaria.org"
    else:
        name = domain
    return name.capitalize()