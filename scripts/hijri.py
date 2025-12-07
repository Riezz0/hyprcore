#!/usr/bin/env python3

from hijri_converter import convert

def get_hijri_date():
    try:
        # Get today's date and convert to Hijri
        today_gregorian = convert.Gregorian.today()
        today_hijri = today_gregorian.to_hijri()

        # Format the date in a nice string
        # Example: "24 Dhul-Hijjah 1445 AH"
        hijri_day = today_hijri.day
        hijri_month = today_hijri.month_name()  # Gets full month name
        hijri_year = today_hijri.year

        # Format: Day Month Year AH
        hijri_date_string = f"{hijri_day} {hijri_month} {hijri_year} AH"
        return hijri_date_string

    except Exception as e:
        # Return a simple fallback if there's any error
        return "Hijri Date"

if __name__ == "__main__":
    print(get_hijri_date())
