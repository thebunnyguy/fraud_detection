"""
Create a sample creditcard.csv dataset for testing purposes.
This is a simplified version of the Kaggle credit card fraud dataset.
"""
import pandas as pd
import numpy as np

# Set seed for reproducibility
np.random.seed(42)

# Create 10,000 sample transactions
n_samples = 10000
fraud_rate = 0.001  # 0.1% fraud rate, like real data

# Create features (v1-v28 from PCA, time, amount, Class)
data = {}
data['Time'] = np.arange(n_samples)  # Sequence of times
data['Amount'] = np.random.exponential(scale=100, size=n_samples)  # Amount distribution

# PCA-transformed features (v1-v28)
for i in range(1, 29):
    data[f'V{i}'] = np.random.normal(0, 1, n_samples)

# Create class labels (0=legit, 1=fraud)
data['Class'] = np.random.choice([0, 1], size=n_samples, p=[1-fraud_rate, fraud_rate])

# Make fraud transactions have slightly different feature distributions
fraud_mask = data['Class'] == 1
for i in range(1, 29):
    data[f'V{i}'][fraud_mask] += np.random.normal(2, 0.5, fraud_mask.sum())

# Rename columns to match expected format
rename_cols = {'Time': 'time', 'Amount': 'amount', 'Class': 'Class'}
for i in range(1, 29):
    rename_cols[f'V{i}'] = f'v{i}'

df = pd.DataFrame(data)
df = df.rename(columns=rename_cols)

# Reorder columns: time, amount, v1-v28, Class
cols_order = ['time', 'amount'] + [f'v{i}' for i in range(1, 29)] + ['Class']
df = df[cols_order]

df.to_csv('creditcard.csv', index=False)
print(f"Sample dataset created: creditcard.csv")
print(f"Shape: {df.shape}")
print(f"Fraud rate: {df['Class'].mean()*100:.3f}%")
