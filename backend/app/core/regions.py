"""Markets (D-39, widened by D-43): any country can be chosen per project.

A project's country decides its currency, distance unit and address-search scope. Distances are always stored
in kilometres; the UI converts for display. US is the default and, with India, is pinned at the top of the picker.
"""
from __future__ import annotations

DEFAULT_COUNTRY = "US"
PINNED = ("US", "IN")
MILES_COUNTRIES = {"US", "GB", "LR", "MM"}
LOCALE = {"US": "en-US", "IN": "en-IN", "GB": "en-GB"}

# ISO 3166-1 alpha-2 → (English name, ISO 4217 currency)
COUNTRIES: dict[str, tuple[str, str]] = {
    "AD": ("Andorra", "EUR"), "AE": ("United Arab Emirates", "AED"), "AF": ("Afghanistan", "AFN"),
    "AG": ("Antigua and Barbuda", "XCD"), "AL": ("Albania", "ALL"), "AM": ("Armenia", "AMD"), "AO": ("Angola", "AOA"),
    "AR": ("Argentina", "ARS"), "AT": ("Austria", "EUR"), "AU": ("Australia", "AUD"), "AW": ("Aruba", "AWG"),
    "AZ": ("Azerbaijan", "AZN"), "BA": ("Bosnia and Herzegovina", "BAM"), "BB": ("Barbados", "BBD"),
    "BD": ("Bangladesh", "BDT"), "BE": ("Belgium", "EUR"), "BF": ("Burkina Faso", "XOF"), "BG": ("Bulgaria", "BGN"),
    "BH": ("Bahrain", "BHD"), "BI": ("Burundi", "BIF"), "BJ": ("Benin", "XOF"), "BM": ("Bermuda", "BMD"),
    "BN": ("Brunei", "BND"), "BO": ("Bolivia", "BOB"), "BR": ("Brazil", "BRL"), "BS": ("Bahamas", "BSD"),
    "BT": ("Bhutan", "BTN"), "BW": ("Botswana", "BWP"), "BY": ("Belarus", "BYN"), "BZ": ("Belize", "BZD"),
    "CA": ("Canada", "CAD"), "CD": ("DR Congo", "CDF"), "CF": ("Central African Republic", "XAF"),
    "CG": ("Congo", "XAF"), "CH": ("Switzerland", "CHF"), "CI": ("Côte d'Ivoire", "XOF"), "CL": ("Chile", "CLP"),
    "CM": ("Cameroon", "XAF"), "CN": ("China", "CNY"), "CO": ("Colombia", "COP"), "CR": ("Costa Rica", "CRC"),
    "CU": ("Cuba", "CUP"), "CV": ("Cape Verde", "CVE"), "CY": ("Cyprus", "EUR"), "CZ": ("Czechia", "CZK"),
    "DE": ("Germany", "EUR"), "DJ": ("Djibouti", "DJF"), "DK": ("Denmark", "DKK"), "DM": ("Dominica", "XCD"),
    "DO": ("Dominican Republic", "DOP"), "DZ": ("Algeria", "DZD"), "EC": ("Ecuador", "USD"), "EE": ("Estonia", "EUR"),
    "EG": ("Egypt", "EGP"), "ER": ("Eritrea", "ERN"), "ES": ("Spain", "EUR"), "ET": ("Ethiopia", "ETB"),
    "FI": ("Finland", "EUR"), "FJ": ("Fiji", "FJD"), "FM": ("Micronesia", "USD"), "FR": ("France", "EUR"),
    "GA": ("Gabon", "XAF"), "GB": ("United Kingdom", "GBP"), "GD": ("Grenada", "XCD"), "GE": ("Georgia", "GEL"),
    "GH": ("Ghana", "GHS"), "GM": ("Gambia", "GMD"), "GN": ("Guinea", "GNF"), "GQ": ("Equatorial Guinea", "XAF"),
    "GR": ("Greece", "EUR"), "GT": ("Guatemala", "GTQ"), "GU": ("Guam", "USD"), "GW": ("Guinea-Bissau", "XOF"),
    "GY": ("Guyana", "GYD"), "HK": ("Hong Kong", "HKD"), "HN": ("Honduras", "HNL"), "HR": ("Croatia", "EUR"),
    "HT": ("Haiti", "HTG"), "HU": ("Hungary", "HUF"), "ID": ("Indonesia", "IDR"), "IE": ("Ireland", "EUR"),
    "IL": ("Israel", "ILS"), "IN": ("India", "INR"), "IQ": ("Iraq", "IQD"), "IR": ("Iran", "IRR"),
    "IS": ("Iceland", "ISK"), "IT": ("Italy", "EUR"), "JM": ("Jamaica", "JMD"), "JO": ("Jordan", "JOD"),
    "JP": ("Japan", "JPY"), "KE": ("Kenya", "KES"), "KG": ("Kyrgyzstan", "KGS"), "KH": ("Cambodia", "KHR"),
    "KI": ("Kiribati", "AUD"), "KM": ("Comoros", "KMF"), "KN": ("Saint Kitts and Nevis", "XCD"),
    "KP": ("North Korea", "KPW"), "KR": ("South Korea", "KRW"), "KW": ("Kuwait", "KWD"), "KY": ("Cayman Islands", "KYD"),
    "KZ": ("Kazakhstan", "KZT"), "LA": ("Laos", "LAK"), "LB": ("Lebanon", "LBP"), "LC": ("Saint Lucia", "XCD"),
    "LI": ("Liechtenstein", "CHF"), "LK": ("Sri Lanka", "LKR"), "LR": ("Liberia", "LRD"), "LS": ("Lesotho", "LSL"),
    "LT": ("Lithuania", "EUR"), "LU": ("Luxembourg", "EUR"), "LV": ("Latvia", "EUR"), "LY": ("Libya", "LYD"),
    "MA": ("Morocco", "MAD"), "MC": ("Monaco", "EUR"), "MD": ("Moldova", "MDL"), "ME": ("Montenegro", "EUR"),
    "MG": ("Madagascar", "MGA"), "MH": ("Marshall Islands", "USD"), "MK": ("North Macedonia", "MKD"),
    "ML": ("Mali", "XOF"), "MM": ("Myanmar", "MMK"), "MN": ("Mongolia", "MNT"), "MO": ("Macao", "MOP"),
    "MR": ("Mauritania", "MRU"), "MT": ("Malta", "EUR"), "MU": ("Mauritius", "MUR"), "MV": ("Maldives", "MVR"),
    "MW": ("Malawi", "MWK"), "MX": ("Mexico", "MXN"), "MY": ("Malaysia", "MYR"), "MZ": ("Mozambique", "MZN"),
    "NA": ("Namibia", "NAD"), "NE": ("Niger", "XOF"), "NG": ("Nigeria", "NGN"), "NI": ("Nicaragua", "NIO"),
    "NL": ("Netherlands", "EUR"), "NO": ("Norway", "NOK"), "NP": ("Nepal", "NPR"), "NR": ("Nauru", "AUD"),
    "NZ": ("New Zealand", "NZD"), "OM": ("Oman", "OMR"), "PA": ("Panama", "PAB"), "PE": ("Peru", "PEN"),
    "PG": ("Papua New Guinea", "PGK"), "PH": ("Philippines", "PHP"), "PK": ("Pakistan", "PKR"), "PL": ("Poland", "PLN"),
    "PR": ("Puerto Rico", "USD"), "PS": ("Palestine", "ILS"), "PT": ("Portugal", "EUR"), "PW": ("Palau", "USD"),
    "PY": ("Paraguay", "PYG"), "QA": ("Qatar", "QAR"), "RO": ("Romania", "RON"), "RS": ("Serbia", "RSD"),
    "RU": ("Russia", "RUB"), "RW": ("Rwanda", "RWF"), "SA": ("Saudi Arabia", "SAR"), "SB": ("Solomon Islands", "SBD"),
    "SC": ("Seychelles", "SCR"), "SD": ("Sudan", "SDG"), "SE": ("Sweden", "SEK"), "SG": ("Singapore", "SGD"),
    "SI": ("Slovenia", "EUR"), "SK": ("Slovakia", "EUR"), "SL": ("Sierra Leone", "SLE"), "SM": ("San Marino", "EUR"),
    "SN": ("Senegal", "XOF"), "SO": ("Somalia", "SOS"), "SR": ("Suriname", "SRD"), "SS": ("South Sudan", "SSP"),
    "ST": ("São Tomé and Príncipe", "STN"), "SV": ("El Salvador", "USD"), "SY": ("Syria", "SYP"),
    "SZ": ("Eswatini", "SZL"), "TD": ("Chad", "XAF"), "TG": ("Togo", "XOF"), "TH": ("Thailand", "THB"),
    "TJ": ("Tajikistan", "TJS"), "TL": ("Timor-Leste", "USD"), "TM": ("Turkmenistan", "TMT"), "TN": ("Tunisia", "TND"),
    "TO": ("Tonga", "TOP"), "TR": ("Türkiye", "TRY"), "TT": ("Trinidad and Tobago", "TTD"), "TV": ("Tuvalu", "AUD"),
    "TW": ("Taiwan", "TWD"), "TZ": ("Tanzania", "TZS"), "UA": ("Ukraine", "UAH"), "UG": ("Uganda", "UGX"),
    "US": ("United States", "USD"), "UY": ("Uruguay", "UYU"), "UZ": ("Uzbekistan", "UZS"), "VA": ("Vatican City", "EUR"),
    "VC": ("Saint Vincent and the Grenadines", "XCD"), "VE": ("Venezuela", "VES"), "VG": ("British Virgin Islands", "USD"),
    "VI": ("U.S. Virgin Islands", "USD"), "VN": ("Vietnam", "VND"), "VU": ("Vanuatu", "VUV"), "WS": ("Samoa", "WST"),
    "XK": ("Kosovo", "EUR"), "YE": ("Yemen", "YER"), "ZA": ("South Africa", "ZAR"), "ZM": ("Zambia", "ZMW"),
    "ZW": ("Zimbabwe", "USD"),
}


def _row(code: str) -> dict:
    name, currency = COUNTRIES[code]
    miles = code in MILES_COUNTRIES
    return {"code": code, "label": name, "currency": currency, "distance_unit": "mi" if miles else "km",
            "locale": LOCALE.get(code, f"en-{code}"), "default_radius_km": 8.047 if miles else 8.0}


# Pinned markets first, then alphabetical by name.
REGIONS: dict[str, dict] = {c: _row(c) for c in PINNED}
REGIONS.update({c: _row(c) for c in sorted(COUNTRIES, key=lambda k: COUNTRIES[k][0]) if c not in PINNED})


def region(country: str | None) -> dict:
    return REGIONS.get((country or "").upper(), REGIONS[DEFAULT_COUNTRY])
