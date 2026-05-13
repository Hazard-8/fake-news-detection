import pandas as pd
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent if APP_DIR.name == "python_files" else APP_DIR
DATA_DIR = PROJECT_ROOT / "data"

true_data = pd.read_csv(DATA_DIR / 'True.csv')
fake_data = pd.read_csv(DATA_DIR / 'Fake.csv')

# Add labels
true_data['label'] = 0   # Real
fake_data['label'] = 1   # Fake

# Keep only required columns
true_data = true_data[['text', 'label']]
fake_data = fake_data[['text', 'label']]

# Combine
data = pd.concat([true_data, fake_data], axis=0)

# Shuffle
data = data.sample(frac=1, random_state=42)

# Save
data.to_csv(DATA_DIR / 'news.csv', index=False)

print("Dataset combined")
print(data['label'].value_counts())
