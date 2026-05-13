# Fake News Detection

Fake News Detection System using Python, Flask, SQLite and Machine Learning.

## Introduction

Fake News Detection is a machine learning based web application that analyzes news text and predicts whether it is real or fake. The project uses Natural Language Processing with TF-IDF vectorization and a Logistic Regression model for text classification. It also includes user authentication, analysis history, admin management, SQLite database support, and optional live news verification through an API.

This project is built using Python, Flask, SQLite, HTML, CSS, JavaScript, Pandas, and Scikit-learn. Dataset files, trained model files, database files, and API keys are not included in this public repository for privacy, security, and storage reasons. Users can add their own dataset, train the model, create a fresh database, and run the application locally.


## Setup

Open PowerShell inside the project folder and run:

```powershell
cd fake-news-detection
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Dataset

Dataset files are not included in this public repository.

Before training, add your own dataset files here:

```text
data/Fake.csv
data/True.csv
```

Both files must contain a column named:

```text
text
```

Then create the combined dataset:

```powershell
python python_files\combine.py
```

This creates:

```text
data/news.csv
```

## Train Model

The trained `.pkl` files are not included in this repository.

After adding the dataset and running `combine.py`, train the model:

```powershell
python python_files\model.py
```

This creates:

```text
models/model.pkl
models/vectorizer.pkl
```

## Create Database

Create a fresh SQLite database:

```powershell
python python_files\db_setup.py
```

This creates:

```text
data/database.db
```

## Run App

Start the Flask app:

```powershell
python python_files\app.py
```

Open in browser:

```text
http://127.0.0.1:5000
```

## Optional News API

The app can run without a News API key, but live verification will be skipped.

To use live verification:

```powershell
$env:NEWS_API_KEY="your_api_key_here"
python python_files\app.py
```

## Admin Login

Default admin login:

```text
Username: admin
Password: admin123
```

To change it:

```powershell
$env:ADMIN_USERNAME="your_admin_username"
$env:ADMIN_PASSWORD="your_admin_password"
python python_files\app.py
```
