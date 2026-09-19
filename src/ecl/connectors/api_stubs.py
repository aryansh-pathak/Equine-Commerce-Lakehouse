"""Live marketplace API connectors -- interface + wiring.

These are intentionally thin: they show exactly where real API calls plug in
and how credentials flow, without shipping secrets or brittle vendor SDKs in a
portfolio repo. Each reads credentials from environment variables and raises a
clear message until they are provided.

To go live: implement `fetch_all` against the vendor SDK (e.g. Amazon SP-API
via `python-amazon-sp-api`, eBay via the Sell APIs, Etsy Open API v3), map the
vendor payload to the canonical schema in `connectors.base`, and register the
class in `connectors.get_connector`.
"""
from __future__ import annotations

import os

import pandas as pd

from ecl.connectors.base import MarketplaceConnector


class _CredentialedApiConnector(MarketplaceConnector):
    #: environment variables required before this connector can run
    required_env: tuple[str, ...] = ()

    def _require_creds(self) -> dict[str, str]:
        missing = [k for k in self.required_env if not os.getenv(k)]
        if missing:
            raise RuntimeError(
                f"{self.name}: set {', '.join(missing)} to enable the live "
                f"{self.name} connector (see README > Going live)."
            )
        return {k: os.environ[k] for k in self.required_env}

    def fetch_all(self) -> dict[str, pd.DataFrame]:  # pragma: no cover - live path
        self._require_creds()
        raise NotImplementedError(
            f"{self.name} live extraction not implemented in the portfolio build; "
            "map the vendor payload to connectors.base.ENTITIES here."
        )


class AmazonSpApiConnector(_CredentialedApiConnector):
    name = "amazon"
    required_env = ("AMZN_LWA_CLIENT_ID", "AMZN_LWA_CLIENT_SECRET", "AMZN_REFRESH_TOKEN")


class EbayConnector(_CredentialedApiConnector):
    name = "ebay"
    required_env = ("EBAY_APP_ID", "EBAY_CERT_ID", "EBAY_OAUTH_TOKEN")


class EtsyConnector(_CredentialedApiConnector):
    name = "etsy"
    required_env = ("ETSY_API_KEY", "ETSY_OAUTH_TOKEN", "ETSY_SHOP_ID")


class WalmartConnector(_CredentialedApiConnector):
    name = "walmart"
    required_env = ("WALMART_CLIENT_ID", "WALMART_CLIENT_SECRET")


class FaireConnector(_CredentialedApiConnector):
    name = "faire"
    required_env = ("FAIRE_ACCESS_TOKEN",)
