import math

R = 8.314


def calculate_mkt(temperatures, activation_energy=83.144):
    if not temperatures:
        return 0.0

    dh = activation_energy * 1000
    n = len(temperatures)

    total = 0.0
    for t_celsius in temperatures:
        t_kelvin = t_celsius + 273.15
        total += math.exp(-dh / (R * t_kelvin))

    mkt_kelvin = dh / (R * (-math.log(total / n)))
    return mkt_kelvin - 273.15
