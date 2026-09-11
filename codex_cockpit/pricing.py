"""Standard API-equivalent estimates, USD per million tokens.

Source: https://developers.openai.com/api/docs/models/gpt-5.3-codex
Unknown models are explicitly unpriced; never guess a family price.
Configure additional exact model IDs through model_prices in config.json.
"""
from . import config

# Verified 2026-09-10 against the respective official model pages.
_MODELS = {
    "gpt-5.3-codex": (1.75, 14.0, 0.175),
    "gpt-5.4": (2.5, 15.0, 0.25),
    "gpt-5.5": (5.0, 30.0, 0.5),
    "gpt-6-astra": (10.0, 50.0, 1.0),
    "gpt-5.6-sol": (4.0, 20.0, 0.40),
    "gpt-5.6": (4.0, 20.0, 0.40),
}


def resolve(model):
    custom = config.load().get("model_prices", {}).get(model)
    if custom is not None:
        try:
            values = tuple(float(custom[k]) for k in ("input", "output", "cached_input"))
            if all(0 <= v < float('inf') for v in values):
                return values
        except (KeyError, TypeError, ValueError):
            pass
    return _MODELS.get(model)


def cost(model, inp, out, write, read):
    prices = resolve(model)
    if prices is None:
        return 0.0
    p_in, p_out, p_cache = prices
    long = model in ("gpt-6-astra", "gpt-5.6-sol", "gpt-5.6", "gpt-5.4", "gpt-5.5") and inp + write + read > 272_000
    return ((inp + write * 1.25) * p_in * (2 if long else 1)
            + out * p_out * (1.5 if long else 1)
            + read * p_cache * (2 if long else 1)) / 1_000_000


def known_models():
    return sorted(set(_MODELS) | set(config.load().get("model_prices", {})))
