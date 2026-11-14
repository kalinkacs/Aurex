"""Neutral, exact, reversible experiment independent of agent claims."""
from fractions import Fraction


def forward(value, shift, multiplier):
    if multiplier == 0:
        raise ValueError('multiplier must be nonzero')
    return (Fraction(value) + Fraction(shift)) * Fraction(multiplier)


def backward(value, shift, multiplier):
    if multiplier == 0:
        raise ValueError('multiplier must be nonzero')
    return Fraction(value) / Fraction(multiplier) - Fraction(shift)


def recheck(value, shift, multiplier):
    original = Fraction(value)
    transformed = forward(original, shift, multiplier)
    restored = backward(transformed, shift, multiplier)
    replayed = forward(restored, shift, multiplier)
    return {'input': str(original), 'forward': str(transformed),
            'backflow': str(restored), 'forward_again': str(replayed),
            'roundtrip_exact': restored == original,
            'forward_consistent': replayed == transformed}


if __name__ == '__main__':
    import json
    print(json.dumps(recheck(7, 3, 5), indent=2))
