from pyo import *
import bisect

def quantize(value, quant, with_index=False):
    """Quantizes a value to the closest value in a list of quantized values.
    Args:
        value (float): Value to be quantized
        quant (list[float]): Quantized value options.
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


def delay_func(delay, func, arg=None):
    """Calls a provided function after a delay using pyo.
    WARNING: the returned values MUST be kept in scope until after the 
    function is triggered or else they will get garbage collected and pyo will
    not trigger the function.
    
    Args:
        delay (float): Delay in seconds.
        func (callable): Function to call after delay.
        arg (tuple, optional): Tuple of arguments to provide to the function. Defaults to None.
    """
    trig = Trig()
    trig_func = TrigFunc(trig, func, arg=arg)
    trig.play(delay=delay)
    return trig, trig_func