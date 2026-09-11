import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.ticker import FuncFormatter
import warnings
warnings.filterwarnings('ignore')


claims   = pd.read_csv('../data/claims.csv', parse_dates=['claim_date'])
patients = pd.read_csv('../data/patients.csv')
payers   = pd.read_csv('../data/payers.csv')

df = claims.merge(payers,   on='payer_id')   \
           .merge(patients, on='patient_id')

#  Highlights ===============================
total_claim   = len(df)
total_patients = df['patient_id'].nunique()
avg_cost       = df['cost'].mean()
approval_rate  = (df['status'] == 'Approved').mean() * 100
rejection_rate = (df['status'] == 'Rejected').mean() * 100

print("-" * 60)
print("\nEXECUTIVE SUMMARY")
print("-" * 60)
print(f"  Total Claims       : {total_claim}")
print(f"  Unique Patients    : {total_patients}")
print(f"  Avg Cost / Claim   : ${avg_cost:.2f}")
print(f"  Approval Rate      : {approval_rate:.1f}%")
print(f"  Rejection Rate     : {rejection_rate:.1f}%")
print("-" * 60)


# Payer Segmentation ==============================
payer_analysis = df.groupby('payer_name').agg(
    total_claim = ('claim_id', 'count'),
    avg_cost = ('cost','mean'),
    total_bill = ('cost', 'sum'),
    approval_rate = ('status', lambda x : (x == 'Approved').mean() * 100)
).round(2).sort_values('total_claim')

print("\nPayer Segmentation Summary:")
print(payer_analysis.to_string())


# Drug utilization by payer ===========================

drug_payer = df.groupby(['payer_name','drug'])['claim_id'].count().unstack(fill_value=0)
print("-" * 60)
print('\nDrug utilization by payer')
print(drug_payer.to_string())


# Patient adherence and drop off analysis ==================================

df["gap_days"] = df.groupby("patient_id")["claim_date"].diff().dt.days
df['drop_off_flag'] = df['gap_days'] > 30
# Flexible: you can tune the threshold (30, 60, 90 days) depending on therapy type.

adherence = df.groupby('patient_id').agg(
    claim_count = ('claim_id', 'count'),
    total_spend = ('cost','sum'),
    last_claim_date = ('claim_date','max')
).reset_index()

def segment(n):
    if n == 1:   return 'Drop-off Risk (1 claim)'
    if n <= 4:   return 'Low Adherence (2-4)'
    if n <= 9:   return 'Moderate (5-9)'
    return 'High Adherence (10+)'

adherence['dropoffBucket_ClaimCount'] = adherence['claim_count'].apply(segment)

# Patients with only 1 claim, OR Patients with any gap > 60 days
adherence['drop_off_flag'] = (adherence['claim_count'] == 1) | (df.groupby("patient_id")["drop_off_flag"].max().reset_index(drop=True))

drop_off_rate = adherence['drop_off_flag'].mean() * 100
print("-" * 60)
print('\nDropp off rate: ')
drop_summary = adherence['drop_off_flag'].value_counts(normalize=True).mul(100).round(1)
print(drop_summary.to_string())

# Save all to a sheet
with pd.ExcelWriter('results_report.xlsx',engine='openpyxl') as writer:
    adherence.to_excel(writer, sheet_name='adherence', index=False)
    payer_analysis.to_excel(writer, sheet_name='payer_analysis', index=True)
    drug_payer.to_excel(writer, sheet_name='payer_drug_segment', index=True)