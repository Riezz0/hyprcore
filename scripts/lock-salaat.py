#!/usr/bin/env python3

import requests
from datetime import datetime, timedelta
import pytz
import os
from pathlib import Path

# --- CONFIGURE FLORIDA, JOHANNESBURG LOCATION ---
LATITUDE = -26.1585    # Florida, Johannesburg coordinates
LONGITUDE = 27.9266
TIMEZONE = "Africa/Johannesburg"
METHOD = 1  # University of Islamic Sciences, Karachi (Shafi'i compatible)
MADHHAB = 3  # Shafi'i madhhab

def get_next_prayer_formatted():
    """Get the next prayer time with 'Next Prayer:' prefix"""
    try:
        # Get current date and time
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        today = now.date()
        
        # API endpoint for today's prayer times
        url = f"http://api.aladhan.com/v1/timings/{today.strftime('%d-%m-%Y')}"
        
        params = {
            'latitude': LATITUDE,
            'longitude': LONGITUDE,
            'method': METHOD,
            'school': MADHHAB,
            'timezonestring': TIMEZONE
        }
        
        # Make API request
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data['code'] != 200:
            return "Next Prayer: Prayer Time"
        
        timings = data['data']['timings']
        
        # Define prayer order and names
        prayers = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
        prayer_times = {}
        
        # Convert prayer times to datetime objects
        for prayer in prayers:
            time_str = timings[prayer]
            prayer_dt = datetime.strptime(f"{today} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
            prayer_times[prayer] = prayer_dt
        
        # Find the next prayer
        next_prayer = None
        next_prayer_time = None
        
        for prayer in prayers:
            if now < prayer_times[prayer]:
                next_prayer = prayer
                next_prayer_time = prayer_times[prayer]
                break
        
        # If no prayer found for today, get first prayer of tomorrow
        if next_prayer is None:
            tomorrow = today + timedelta(days=1)
            url_tomorrow = f"http://api.aladhan.com/v1/timings/{tomorrow.strftime('%d-%m-%Y')}"
            
            response_tomorrow = requests.get(url_tomorrow, params=params, timeout=10)
            response_tomorrow.raise_for_status()
            
            data_tomorrow = response_tomorrow.json()
            timings_tomorrow = data_tomorrow['data']['timings']
            
            next_prayer = 'Fajr'
            time_str = timings_tomorrow['Fajr']
            next_prayer_time = datetime.strptime(f"{tomorrow} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        
        # Format the output with "Next Prayer:" prefix
        time_formatted = next_prayer_time.strftime("%H:%M")
        return f"Next Prayer: {next_prayer} {time_formatted}"
        
    except requests.exceptions.RequestException:
        return "Next Prayer: Prayer Time"
    except KeyError:
        return "Next Prayer: Prayer Time"
    except Exception as e:
        return "Next Prayer: Prayer Time"

def get_next_prayer_with_fallback():
    """Get next prayer with offline fallback calculation"""
    try:
        # Try API first
        return get_next_prayer_formatted()
        
    except Exception:
        # Fallback to basic calculation if API fails
        return offline_prayer_calculation()

def offline_prayer_calculation():
    """Basic offline prayer time estimation as fallback"""
    try:
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        current_hour = now.hour + now.minute/60
        
        # Simplified prayer time estimates for Johannesburg
        prayer_times = {
            'Fajr': 5.0,    # 5:00 AM
            'Dhuhr': 12.5,  # 12:30 PM
            'Asr': 16.0,    # 4:00 PM
            'Maghrib': 18.5, # 6:30 PM
            'Isha': 20.0    # 8:00 PM
        }
        
        # Find next prayer
        for prayer, hour in prayer_times.items():
            if current_hour < hour:
                hours = int(hour)
                minutes = int((hour - hours) * 60)
                return f"Next Prayer: {prayer} {hours:02d}:{minutes:02d}"
        
        # If no prayer today, return Fajr tomorrow
        return "Next Prayer: Fajr 05:00"
        
    except Exception:
        return "Next Prayer: Prayer Time"

if __name__ == "__main__":
    result = get_next_prayer_with_fallback()
    print(result)
