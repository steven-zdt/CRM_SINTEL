import pandas as pd
import re
from decimal import Decimal

df = pd.read_excel('media/extractos/10800014844_AGO2026.xlsx', header=None)
pat = re.compile(r'^\d{1,2}/\d{1,2}$')

count = 0
total_credit = Decimal('0')
total_debit = Decimal('0')
for i, row in df.iterrows():
    v = str(row[0]).strip() if pd.notna(row[0]) else ''
    if pat.match(v):
        count += 1
        raw = str(row[4]).strip().replace(',', '')
        val = Decimal(raw)
        if val >= 0:
            total_credit += val
        else:
            total_debit += -val

print('date-pattern rows:', count)
print('total_credit:', total_credit)
print('total_debit:', total_debit)
