

def clamp(value, lower_bound, upper_bound):
    """Clamps a number between provided bounds."""
    return max(lower_bound, min(value, upper_bound))
