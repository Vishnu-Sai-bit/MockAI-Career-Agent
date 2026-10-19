from typing import Dict, Any, List

class SalaryNormalizerService:
    """
    Normalizes multi-currency compensations, performs real-time currency conversions,
    and calculates Purchasing Power Parity (PPP) & Cost of Living equivalents.
    """

    # Baseline FX rates against USD
    FX_RATES_TO_USD = {
        "USD": 1.0,
        "EUR": 1.08,
        "GBP": 1.29,
        "INR": 0.012,
        "CAD": 0.73,
        "AUD": 0.66,
        "SGD": 0.76
    }

    # World Bank / IMF implied PPP conversion factors relative to US price levels
    # (How many units of local currency have the same purchasing power as $1 USD in the USA)
    PPP_FACTORS_FROM_USD = {
        "USD": 1.0,
        "EUR": 0.85,
        "GBP": 0.72,
        "INR": 23.5, # $1 USD in US buys goods equivalent to ~23.5 INR in India
        "CAD": 1.25,
        "AUD": 1.45,
        "SGD": 1.20
    }

    def convert_salary(self, amount: float, from_curr: str, to_curr: str) -> Dict[str, Any]:
        """
        Converts nominal salary between currencies using base FX rates.
        """
        from_c = from_curr.upper()
        to_c = to_curr.upper()

        if from_c not in self.FX_RATES_TO_USD or to_c not in self.FX_RATES_TO_USD:
            return {"error": f"Unsupported currency pair: {from_c} to {to_c}"}

        # Convert to USD then to target
        amount_usd = amount * self.FX_RATES_TO_USD[from_c]
        converted_amount = amount_usd / self.FX_RATES_TO_USD[to_c]

        return {
            "original_amount": amount,
            "original_currency": from_c,
            "target_currency": to_c,
            "converted_nominal": round(converted_amount, 2),
            "amount_in_usd": round(amount_usd, 2)
        }

    def calculate_ppp_equivalent(self, salary_amount: float, from_curr: str, home_curr: str = "INR") -> Dict[str, Any]:
        """
        Calculates nominal value vs Purchasing Power Parity (PPP) equivalent.
        Example: A $100k USD remote salary offers massive purchasing power when living in India.
        """
        from_c = from_curr.upper()
        home_c = home_curr.upper()

        # Step 1: Normalize to USD
        conv = self.convert_salary(salary_amount, from_c, home_c)
        if "error" in conv:
            return conv

        amount_usd = conv["amount_in_usd"]
        nominal_home = conv["converted_nominal"]

        # Step 2: Calculate PPP equivalent
        # If earning in USD and living in home country:
        home_ppp_factor = self.PPP_FACTORS_FROM_USD.get(home_c, 1.0)
        ppp_equivalent = amount_usd * home_ppp_factor

        multiplier = round(nominal_home / ppp_equivalent, 2) if ppp_equivalent > 0 else 1.0

        return {
            "original_salary": salary_amount,
            "original_currency": from_c,
            "home_currency": home_c,
            "nominal_exchange_value": nominal_home,
            "local_ppp_buying_power": round(ppp_equivalent, 2),
            "ppp_multiplier": multiplier,
            "analysis": f"A {from_c} {salary_amount:,.0f} offer equates to {home_c} {nominal_home:,.0f} nominally. In local purchasing power, it affords a lifestyle equivalent to {home_c} {ppp_equivalent:,.0f} locally."
        }
