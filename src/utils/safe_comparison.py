"""
Safer comparison utilities to prevent type errors
"""

def safe_greater_than(value, threshold):
    """Safely compare value > threshold, handling dict responses"""
    if isinstance(value, dict):
        # If it's a dict, try to extract numeric value
        if 'result' in value:
            value = value['result']
        elif 'value' in value:
            value = value['value']
        elif 'amount' in value:
            value = value['amount']
        else:
            return False
    
    try:
        return float(value) > float(threshold)
    except (TypeError, ValueError):
        return False

def safe_less_than(value, threshold):
    """Safely compare value < threshold"""
    if isinstance(value, dict):
        if 'result' in value:
            value = value['result']
        elif 'value' in value:
            value = value['value']
        elif 'amount' in value:
            value = value['amount']
        else:
            return False
    
    try:
        return float(value) < float(threshold)
    except (TypeError, ValueError):
        return False
