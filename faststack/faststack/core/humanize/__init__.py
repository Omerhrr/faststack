"""
FastStack Humanize - Human-readable formatting.

Example:
    from faststack.core.humanize import (
        naturaltime,
        naturaldate,
        intword,
        intcomma,
        filesizeformat,
        ordinal
    )

    naturaltime(timedelta(hours=2))  # '2 hours ago'
    intword(1500000)  # '1.5 million'
    filesizeformat(1024*1024)  # '1.0 MB'
"""

from typing import Union
from datetime import datetime, timedelta
import math


def naturaltime(value: Union[datetime, timedelta], when: datetime = None) -> str:
    """
    Format a datetime or timedelta as human-readable time ago.

    Args:
        value: Datetime or timedelta
        when: Reference time (default: now)

    Returns:
        Human-readable string

    Example:
        naturaltime(datetime.now() - timedelta(hours=2))  # '2 hours ago'
        naturaltime(timedelta(minutes=30))  # '30 minutes'
    """
    if isinstance(value, timedelta):
        delta = value
    else:
        if when is None:
            when = datetime.now()
        delta = when - value if value < when else value - when

    seconds = abs(delta.total_seconds())
    is_future = isinstance(value, timedelta) or value > (when or datetime.now())

    if seconds < 1:
        return 'now'
    elif seconds < 60:
        count = int(seconds)
        plural = '' if count == 1 else 's'
        return f"{count} second{plural}" + (' from now' if is_future else ' ago')
    elif seconds < 3600:
        count = int(seconds / 60)
        plural = '' if count == 1 else 's'
        return f"{count} minute{plural}" + (' from now' if is_future else ' ago')
    elif seconds < 86400:
        count = int(seconds / 3600)
        plural = '' if count == 1 else 's'
        return f"{count} hour{plural}" + (' from now' if is_future else ' ago')
    elif seconds < 604800:  # 7 days
        count = int(seconds / 86400)
        plural = '' if count == 1 else 's'
        return f"{count} day{plural}" + (' from now' if is_future else ' ago')
    elif seconds < 2592000:  # 30 days
        count = int(seconds / 604800)
        plural = '' if count == 1 else 's'
        return f"{count} week{plural}" + (' from now' if is_future else ' ago')
    elif seconds < 31536000:  # 365 days
        count = int(seconds / 2592000)
        plural = '' if count == 1 else 's'
        return f"{count} month{plural}" + (' from now' if is_future else ' ago')
    else:
        count = int(seconds / 31536000)
        plural = '' if count == 1 else 's'
        return f"{count} year{plural}" + (' from now' if is_future else ' ago')


def naturaldate(value: datetime) -> str:
    """
    Format a date as human-readable.

    Args:
        value: Datetime

    Returns:
        Human-readable string

    Example:
        naturaldate(datetime.now() - timedelta(days=1))  # 'yesterday'
    """
    today = datetime.now().date()
    date = value.date() if isinstance(value, datetime) else value
    delta = (today - date).days

    if delta == 0:
        return 'today'
    elif delta == 1:
        return 'yesterday'
    elif delta == -1:
        return 'tomorrow'
    elif delta < 7:
        return f"{abs(delta)} days ago" if delta > 0 else f"in {abs(delta)} days"
    else:
        return value.strftime('%B %d, %Y')


def intword(value: int) -> str:
    """
    Convert a large integer to a human-readable string.

    Args:
        value: Integer value

    Returns:
        Human-readable string

    Example:
        intword(1500000)  # '1.5 million'
        intword(2300000000)  # '2.3 billion'
    """
    value = int(value)

    if value < 1000:
        return str(value)

    suffixes = [
        (10**18, 'quintillion'),
        (10**15, 'quadrillion'),
        (10**12, 'trillion'),
        (10**9, 'billion'),
        (10**6, 'million'),
        (10**3, 'thousand'),
    ]

    for threshold, suffix in suffixes:
        if value >= threshold:
            new_value = value / threshold
            # Format with one decimal if needed
            if new_value == int(new_value):
                return f"{int(new_value)} {suffix}"
            return f"{new_value:.1f} {suffix}"

    return str(value)


def intcomma(value: int) -> str:
    """
    Convert an integer to a string with commas.

    Args:
        value: Integer value

    Returns:
        String with commas

    Example:
        intcomma(1500000)  # '1,500,000'
    """
    value = str(value)

    if '.' in value:
        integer, decimal = value.split('.')
    else:
        integer, decimal = value, None

    # Add commas
    result = ''
    for i, digit in enumerate(reversed(integer)):
        if i > 0 and i % 3 == 0:
            result = ',' + result
        result = digit + result

    if decimal:
        result += '.' + decimal

    return result


def filesizeformat(bytes: int) -> str:
    """
    Format a file size in human-readable format.

    Args:
        bytes: Size in bytes

    Returns:
        Human-readable string

    Example:
        filesizeformat(1024)  # '1.0 KB'
        filesizeformat(1024*1024)  # '1.0 MB'
    """
    bytes = float(bytes)

    if bytes < 1024:
        return f"{bytes:.0f} bytes" if bytes != 1 else "1 byte"
    elif bytes < 1024 * 1024:
        return f"{bytes/1024:.1f} KB"
    elif bytes < 1024 * 1024 * 1024:
        return f"{bytes/(1024*1024):.1f} MB"
    elif bytes < 1024 * 1024 * 1024 * 1024:
        return f"{bytes/(1024*1024*1024):.1f} GB"
    else:
        return f"{bytes/(1024*1024*1024*1024):.1f} TB"


def ordinal(value: int) -> str:
    """
    Convert an integer to its ordinal string.

    Args:
        value: Integer value

    Returns:
        Ordinal string

    Example:
        ordinal(1)  # '1st'
        ordinal(22)  # '22nd'
    """
    value = int(value)
    suffixes = ['th', 'st', 'nd', 'rd']

    if 10 <= value % 100 <= 20:
        suffix = suffixes[0]
    else:
        suffix = suffixes[min(value % 10, 3)]

    return f"{value}{suffix}"


def apnumber(value: int) -> str:
    """
    Convert an integer to an AP-style number string.

    Args:
        value: Integer (0-10)

    Returns:
        AP-style string

    Example:
        apnumber(1)  # 'one'
        apnumber(10)  # '10'
    """
    value = int(value)
    ap_numbers = ['zero', 'one', 'two', 'three', 'four', 'five',
                  'six', 'seven', 'eight', 'nine', 'ten']

    if 0 <= value <= 10:
        return ap_numbers[value]
    return str(value)


def fractional(value: float) -> str:
    """
    Convert a decimal to a fractional string.

    Args:
        value: Decimal value

    Returns:
        Fractional string

    Example:
        fractional(1.5)  # '1 1/2'
    """
    from fractions import Fraction

    frac = Fraction(value).limit_denominator(100)

    if frac.denominator == 1:
        return str(frac.numerator)

    whole = frac.numerator // frac.denominator
    remainder = frac.numerator % frac.denominator

    if whole:
        return f"{whole} {remainder}/{frac.denominator}"
    return f"{remainder}/{frac.denominator}"


def percentage(value: float, decimal_places: int = 1) -> str:
    """
    Convert a decimal to a percentage string.

    Args:
        value: Decimal value (0-1)
        decimal_places: Number of decimal places

    Returns:
        Percentage string

    Example:
        percentage(0.75)  # '75.0%'
    """
    return f"{value * 100:.{decimal_places}f}%"


def pluralize(value: int, singular: str = '', plural: str = 's') -> str:
    """
    Return singular or plural suffix based on count.

    Args:
        value: Count
        singular: Singular suffix
        plural: Plural suffix

    Returns:
        Appropriate suffix

    Example:
        f"{count} item{pluralize(count)}"  # '1 item', '2 items'
    """
    if value == 1:
        return singular
    return plural


def truncatewords(value: str, num: int) -> str:
    """
    Truncate a string to a certain number of words.

    Args:
        value: String to truncate
        num: Number of words

    Returns:
        Truncated string

    Example:
        truncatewords('Hello world how are you', 3)  # 'Hello world how ...'
    """
    words = value.split()
    if len(words) <= num:
        return value
    return ' '.join(words[:num]) + ' ...'


def truncatechars(value: str, num: int) -> str:
    """
    Truncate a string to a certain number of characters.

    Args:
        value: String to truncate
        num: Number of characters

    Returns:
        Truncated string
    """
    if len(value) <= num:
        return value
    return value[:num-3] + '...' if num > 3 else value[:num]
