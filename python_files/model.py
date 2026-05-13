import pandas as pd
import pickle
import re
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent if APP_DIR.name == "python_files" else APP_DIR
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)

# Load dataset
data = pd.read_csv(DATA_DIR / 'news.csv')

# Remove null values
data = data.dropna()

# Preprocess function
def preprocess(text):
    text = re.sub(r'[^a-zA-Z]', ' ', str(text))
    text = text.lower()
    return text

# Apply preprocessing
data['text'] = data['text'].apply(preprocess)

X = data['text']
y = data['label']

print("Label count:")
print(y.value_counts())

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# TF-IDF
vectorizer = TfidfVectorizer(stop_words='english', max_df=0.7)
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

# Logistic Regression Model
model = LogisticRegression()
model.fit(X_train_vec, y_train)

# Accuracy
y_pred = model.predict(X_test_vec)
print("Accuracy:", accuracy_score(y_test, y_pred))

# Confusion Matrix
print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# Save model
pickle.dump(model, open(MODELS_DIR / 'model.pkl', 'wb'))
pickle.dump(vectorizer, open(MODELS_DIR / 'vectorizer.pkl', 'wb'))

print("Model saved")
print("Sample predictions:")
print(y_pred[:20])
print("Actual values:")
print(y_test.values[:20])
