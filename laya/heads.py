"""Strict validation of real MLX responses; no inferred/default answers."""
import math
from .questions import get_laya_seo_questions


class LayaHeadMissingError(ValueError):
    """A required Laya question output is missing or malformed."""


def validate_heads(response):
    answers = response.get("answers") if isinstance(response, dict) else None
    if not isinstance(answers, dict):
        raise LayaHeadMissingError("Laya response has no answers dictionary")
    result = {}
    for name, question in get_laya_seo_questions().items():
        answer = answers.get(name)
        try:
            if not isinstance(answer, dict):
                raise ValueError("missing answer")
            choice = answer["choice"]
            probabilities = answer["probabilities"]
            confidence = answer["confidence"]
            if answer.get("type") != "choice" or choice not in question["criteria"]:
                raise ValueError("invalid choice/type")
            if set(probabilities) != set(question["criteria"]):
                raise ValueError("missing/unknown probability labels")
            for value in [confidence, *probabilities.values()]:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                    raise ValueError("non-finite/out-of-range probability or entropy confidence")
            # Runtime rounds each probability to four decimals.
            tolerance = len(probabilities) * 0.00005 + 0.000001
            if abs(sum(probabilities.values()) - 1) > tolerance or probabilities[choice] < max(probabilities.values()):
                raise ValueError("invalid probability sum or chosen argmax")
            result[name] = {**answer, "chosen_probability": probabilities[choice]}
        except (KeyError, TypeError, ValueError) as exc:
            raise LayaHeadMissingError(f"Required Laya head '{name}' is missing or malformed: {exc}") from exc
    return result
