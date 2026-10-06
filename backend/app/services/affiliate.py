"""Unico punto in cui vengono costruiti i link affiliati Amazon.

Regole:
- il frontend NON costruisce mai URL Amazon da solo;
- il link porta DIRETTAMENTE ad Amazon (nessun redirect intermedio /go/... che
  nasconda la provenienza del click);
- il click viene tracciato in parallelo (sendBeacon), senza intercettare il link.
"""

from __future__ import annotations

import re
from urllib.parse import quote

MARKETPLACE_DOMAINS = {
    "it": "www.amazon.it",
    "de": "www.amazon.de",
    "fr": "www.amazon.fr",
    "es": "www.amazon.es",
    "uk": "www.amazon.co.uk",
    "com": "www.amazon.com",
}

ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")
TAG_RE = re.compile(r"^[A-Za-z0-9\-_]{3,64}$")


class AffiliateLinkError(ValueError):
    pass


class AffiliateLinkService:
    def __init__(self, partner_tag: str | None, default_marketplace: str = "it"):
        if partner_tag and not TAG_RE.match(partner_tag):
            raise AffiliateLinkError(f"Partner tag non valido: {partner_tag!r}")
        self.partner_tag = partner_tag
        self.default_marketplace = default_marketplace

    def build(self, asin: str, marketplace: str | None = None) -> str:
        asin = (asin or "").strip().upper()
        if not ASIN_RE.match(asin):
            raise AffiliateLinkError(f"ASIN non valido: {asin!r}")
        mk = marketplace or self.default_marketplace
        domain = MARKETPLACE_DOMAINS.get(mk)
        if not domain:
            raise AffiliateLinkError(f"Marketplace non supportato: {mk!r}")
        url = f"https://{domain}/dp/{asin}"
        if self.partner_tag:
            url += f"?tag={quote(self.partner_tag)}"
        return url
