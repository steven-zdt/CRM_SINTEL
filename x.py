import pandas as pd, re
from decimal import Decimal
df = pd.read_excel('media/extractos/10800014844_AGO2026.xlsx', header=None)
pat = re.compile(r'^\d{1,2}/\d{1,2}$')
cred=deb=0
for i,row in df.iterrows():
    v = str(row[0]).strip() if pd.notna(row[0]) else ''
    if pat.match(v):
        raw = str(row[4]).strip().replace(',', '')
        val = Decimal(raw)
        if val >= 0: cred+=1
        else: deb+=1
print('credits', cred, 'debits', deb)
