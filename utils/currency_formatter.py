"""
Currency and salary formatting utilities.
Standardizes compensation display to Indian Rupees (INR / ₹) with LPA representation.
"""
from typing import Union, Optional

def format_inr(amount: Union[int, float, None]) -> str:
    """
    Formats a numeric amount in Indian Rupees (₹).
    If >= 1,00,000 (1 Lakh), includes LPA representation.
    Example: 1500000 -> "₹ 15,00,000 (15.0 LPA)"
    """
    if amount is None or amount == "":
        return ""
    try:
        val = float(amount)
        if val >= 100000:
            lpa = val / 100000.0
            return f"₹ {val:,.0f} ({lpa:.1f} LPA)"
        return f"₹ {val:,.0f}"
    except (ValueError, TypeError):
        return str(amount)


def format_job_salary(job) -> str:
    """
    Formats a Job model instance's compensation into Indian Rupees (₹).
    If the job's native currency is USD or another foreign currency, converts it
    to approximate INR value at base FX rates so Indian candidates have instant clarity.
    """
    if not job or (getattr(job, "salary_min", None) is None and getattr(job, "salary_max", None) is None):
        return ""

    s_min = job.salary_min
    s_max = job.salary_max
    curr = (getattr(job, "currency", None) or "INR").upper()

    # Base FX conversion to INR if job is in foreign currency (e.g. USD)
    FX_TO_INR = {
        "USD": 83.33,
        "EUR": 90.0,
        "GBP": 107.5,
        "CAD": 61.0,
        "AUD": 55.0,
        "SGD": 63.0,
        "INR": 1.0
    }

    fx_rate = FX_TO_INR.get(curr, 1.0)
    is_foreign = (curr != "INR")

    # If foreign currency, calculate INR equivalents
    inr_min = (s_min * fx_rate) if s_min else None
    inr_max = (s_max * fx_rate) if s_max else None

    # Format Rupee representation
    if inr_min and inr_max:
        if inr_min >= 100000:
            rupee_str = f"₹ {inr_min / 100000:.1f}–{inr_max / 100000:.1f} LPA"
        else:
            rupee_str = f"₹ {inr_min:,.0f}–{inr_max:,.0f}"

        if is_foreign:
            return f"{rupee_str} (${int(s_min / 1000)}k–${int(s_max / 1000)}k {curr})"
        return rupee_str

    if inr_min:
        if inr_min >= 100000:
            rupee_str = f"₹ {inr_min / 100000:.1f} LPA+"
        else:
            rupee_str = f"₹ {inr_min:,.0f}+ / yr"

        if is_foreign:
            return f"{rupee_str} (${int(s_min / 1000)}k+ {curr})"
        return rupee_str

    if inr_max:
        if inr_max >= 100000:
            rupee_str = f"Up to ₹ {inr_max / 100000:.1f} LPA"
        else:
            rupee_str = f"Up to ₹ {inr_max:,.0f}"

        if is_foreign:
            return f"{rupee_str} (Up to ${int(s_max / 1000)}k {curr})"
        return rupee_str

    return ""
