from datetime import date, timedelta


def is_minor(birth_date):
    """Returns True if the person is under 18 years old, False otherwise."""
    today = date.today()
    age_18 = birth_date + timedelta(days=18 * 365.25)  # Approximate leap years
    return today < age_18