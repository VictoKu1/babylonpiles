"""
Catalog and validation helpers for mirrored EmergencyStorage providers.
"""

from typing import Any, Dict, List


MIRROR_PROVIDER_CATALOG: Dict[str, Dict[str, Any]] = {
    "openstreetmap": {
        "display_name": "OpenStreetMap",
        "description": "Mirror the OpenStreetMap planet PBF snapshot through the vendored EmergencyStorage toolkit.",
        "variants": {
            "planet": {
                "display_name": "Planet",
                "description": "Complete OpenStreetMap planet snapshot in PBF format.",
            }
        },
    },
    "internet_archive": {
        "display_name": "Internet Archive",
        "description": "Prepare preserved Internet Archive collections using vendored EmergencyStorage scripts.",
        "variants": {
            "software": {
                "display_name": "Software",
                "description": "Software preservation collection metadata and download placeholders.",
            },
            "music": {
                "display_name": "Music",
                "description": "Music collection metadata and download placeholders.",
            },
            "movies": {
                "display_name": "Movies",
                "description": "Public-domain movie collection metadata and download placeholders.",
            },
            "texts": {
                "display_name": "Texts",
                "description": "Text and academic collection metadata and download placeholders.",
            },
        },
    },
}


def is_valid_provider_variant(provider: str, variant: str) -> bool:
    """Return true when the provider/variant pair is part of the fixed v1 catalog."""
    return variant in MIRROR_PROVIDER_CATALOG.get(provider, {}).get("variants", {})


def get_destination_subpath(provider: str, variant: str) -> str:
    """Compute the fixed mirror destination for a provider/variant pair."""
    if not is_valid_provider_variant(provider, variant):
        raise ValueError(f"Unsupported mirror provider/variant combination: {provider}/{variant}")
    return f"mirrors/{provider}/{variant}"


def get_provider_catalog() -> List[Dict[str, Any]]:
    """Convert the internal provider catalog into an API-friendly list."""
    providers: List[Dict[str, Any]] = []
    for provider, provider_config in MIRROR_PROVIDER_CATALOG.items():
        providers.append(
            {
                "provider": provider,
                "display_name": provider_config["display_name"],
                "description": provider_config["description"],
                "variants": [
                    {
                        "variant": variant,
                        "display_name": variant_config["display_name"],
                        "description": variant_config["description"],
                        "destination_subpath": get_destination_subpath(provider, variant),
                    }
                    for variant, variant_config in provider_config["variants"].items()
                ],
            }
        )
    return providers
