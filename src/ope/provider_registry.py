from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping


@dataclass(frozen=True)
class ProviderSpec:
    """Declarative external provider contract.

    OPE never treats a provider as a source of truth. Providers supply evidence
    to deterministic checks; credentials are resolved only at runtime.
    """

    name: str
    capabilities: tuple[str, ...]
    credential_env: tuple[str, ...] = ()
    optional: bool = True

    def configured(self, environ: Mapping[str, str] | None = None) -> bool:
        env = os.environ if environ is None else environ
        return bool(self.credential_env) and all(env.get(key, "").strip() for key in self.credential_env)


PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec("openrouter", ("reasoning", "evidence-synthesis"), ("OPENROUTER_API_KEY",)),
    ProviderSpec("parallel", ("research", "web-discovery"), ("PARALLEL_API_KEY",)),
    ProviderSpec("openseo", ("seo", "ai-visibility", "site-audit"), ("OPENSEO_API_KEY",)),
    ProviderSpec("dataforseo", ("keywords", "serp", "backlinks", "competitors"), ("DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD")),
    ProviderSpec("google-search-console", ("search-performance", "indexing"), ("GOOGLE_SEARCH_CONSOLE_CREDENTIALS",)),
    ProviderSpec("bing-webmaster", ("search-performance", "indexing"), ("BING_WEBMASTER_API_KEY",)),
)


def providers_for(capability: str) -> tuple[ProviderSpec, ...]:
    """Return providers capable of supplying a named evidence capability."""
    wanted = capability.strip().lower()
    return tuple(provider for provider in PROVIDERS if wanted in provider.capabilities)


def configured_providers(environ: Mapping[str, str] | None = None) -> tuple[ProviderSpec, ...]:
    return tuple(provider for provider in PROVIDERS if provider.configured(environ))


def integration_inventory(environ: Mapping[str, str] | None = None) -> dict[str, object]:
    """Expose provider availability without exposing secrets or secret values."""
    env = os.environ if environ is None else environ
    return {
        "providers": {
            provider.name: {
                "capabilities": list(provider.capabilities),
                "configured": provider.configured(env),
                "optional": provider.optional,
            }
            for provider in PROVIDERS
        }
    }
