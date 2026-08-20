import re

lines = [
    'AREAASSIGN  "F166"  "1F"  SECTION "RES-270"  DIAPH  "D2"',
    'AREACONNECTIVITY  "F166"  "1F"  NUMPTS 4  POINTS "101" "102" "103" "104"',
    'LINEASSIGN  "B1"  "1F"  SECTION "B 300X1000"',
    'LINECONNECTIVITY  "B1"  "1F"  POINT1 "101" POINT2 "102"'
]

for line in lines:
    quotes = re.findall(r'"([^"]+)"', line)
    print("Line:", line)
    print(" -> Quotes extracted:", quotes)
