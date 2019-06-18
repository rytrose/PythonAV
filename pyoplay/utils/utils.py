import bisect

def quantize(value, quant):
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
    return quant[ind]