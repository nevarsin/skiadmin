import datetime

def format_season(date):
    cutoff = datetime.date(date.year, 8, 31)
    if date > cutoff:
        start_year = date.year
        end_year = date.year + 1
    else:
        start_year = date.year + 1
        end_year = date.year + 2
    return f"{start_year}/{end_year}"
