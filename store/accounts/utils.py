import re

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"


def normalize_phone(value: str) -> str:
    """هر شکل شماره موبایل را به فرم استاندارد 09xxxxxxxxx تبدیل می‌کند."""
    if not value:
        return ""

    value = str(value).strip()

    for i, digit in enumerate(PERSIAN_DIGITS):
        value = value.replace(digit, str(i))
    for i, digit in enumerate(ARABIC_DIGITS):
        value = value.replace(digit, str(i))

    value = re.sub(r"[\s\-()]", "", value)

    if value.startswith("+98"):
        value = "0" + value[3:]
    elif value.startswith("0098"):
        value = "0" + value[4:]
    elif value.startswith("98") and len(value) == 12:
        value = "0" + value[2:]
    elif value.startswith("9") and len(value) == 10:
        value = "0" + value

    return value
