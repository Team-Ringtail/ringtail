"""Sub-optimal: many conditionals; optimal is table-driven."""
def int_to_roman(num: int) -> str:
    sym = [(1000,"M"),(900,"CM"),(500,"D"),(400,"CD"),(100,"C"),(90,"XC"),(50,"L"),(40,"XL"),(10,"X"),(9,"IX"),(5,"V"),(4,"IV"),(1,"I")]
    out = []
    for v, s in sym:
        while num >= v:
            out.append(s)
            num -= v
    return "".join(out)
