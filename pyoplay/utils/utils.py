import bisect

def quantize(value, quant, with_index=False):
    """Quantizes a value to the closest value in a list of quantized values.
    Args:
        value (float): Value to be quantized
        quant (List[float]): Quantized value options.
    Returns:
        float: Quantized input value.
    """
    mids = [(quant[i] + quant[i + 1]) / 2.0
            for i in range(len(quant) - 1)]
    ind = bisect.bisect_right(mids, value)
    if with_index:
        return ind, quant[ind]
    else:
        return quant[ind]

def linear_interpolate(x, x0, y0, x1, y1):
    """Linear interpolation from two points.
    
    Args:
        x (float): x to interpolate
        x0 (float): x of first point
        y0 (float): y of first point
        x1 (float): x of second point
        y1 (float): y of second point
    
    Returns:
        float: interpolated value
    """
    try:
        return (y0 * (x1 - x) + y1 * (x - x0)) / (x1 - x0)
    except ZeroDivisionError:
        return 0.0