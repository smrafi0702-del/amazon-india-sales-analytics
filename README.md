# 📊 10-Year Amazon India Sales Analytics & Business Intelligence Dashboard

An enterprise-grade, end-to-end data analytics and visualization solution processing over **1.1 million records** of Amazon India sales data (2015–2025). This project features a robust data cleaning pipeline, exploratory data analysis (EDA) answering core business questions, a relational PostgreSQL database backend, and an interactive 5-page Streamlit web application.

---

## 🚀 Executive Summary & Project Scale

- **Dataset Scale:** Processed and analyzed **1.1M+ rows** spanning a decade of e-commerce transactions across multiple regional and category datasets.
- **Architecture:** Decoupled architecture utilizing a local PostgreSQL 17 database for fast querying, connected dynamically to an interactive multi-page Streamlit frontend.
- **Core Objective:** Uncover macroeconomic sales trends, category performance drivers, customer retention metrics, and price-to-demand elasticities to guide strategic e-commerce decision-making.

---

## 🛠️ End-to-End Workflow & Methodology

### 1. Data Cleaning & Preprocessing (`Data_Cleaning.ipynb`)

- Handled massive multi-year raw CSV datasets (`amazon_india_2015.csv` through `2025.csv` plus product catalogs).
- Resolved complex null-value distributions, missing categorical entries, and data type inconsistencies.
- Performed feature engineering to standardize timestamps, pricing metrics, and customer identifiers across disparate file schemas.

### 2. Exploratory Data Analysis (EDA) & Business Questions (`eda.ipynb`)

Investigated core exploratory and business-driven inquiries, including:

- **Revenue Trajectory:** How have overall gross merchandise value (GMV) and seasonal spikes evolved from 2015 to 2025?
- **Category Dominance:** Which product categories consistently drive volume versus those yielding higher profit margins?
- **Customer Behavior:** What patterns define repeat buyers versus one-time purchasers, and how does customer lifetime value vary?
- **Price Sensitivity:** To what extent do price adjustments and discount structures impact product demand velocity?

### 3. Database Architecture (`sql.ipynb`)

- Engineered a local **PostgreSQL 17** relational database using SQLAlchemy.
- Loaded cleansed datasets into optimized tables to ensure sub-second query execution times for the live dashboard.

---

## 💻 Interactive 5-Page Streamlit Dashboard (`app.py`)

The application is modularized into 5 distinct analytical views accessible via interactive sidebar navigation:

1. **Sales Trends & Revenue Growth:** Multi-year performance tracking, seasonal anomaly detection, and YoY growth rates.
2. **Category & Product Catalog Performance:** Deep-dive inventory and category contribution analysis using high-contrast Plotly charts.
3. **Customer Behavior & Retention:** Metrics evaluating user engagement, repeat order rates, and segmentation.
4. **Price vs. Demand Analysis:** Statistical visualization mapping price points against order volumes and market demand.
5. **Overview & Summary Metrics:** High-level KPIs and executive summaries for quick stakeholder review.

---

## 📂 Project Directory Structure

```text
Data_Cleaning_Project_2/
│
├── .streamlit/
│   └── secrets.toml          # Local database credentials (Git-ignored for security)
├── Correct_Notebooks/
│   ├── Data_Cleaning.ipynb   # Raw data ingestion, null imputation, and preprocessing
│   └── eda.ipynb             # Exploratory Data Analysis & business question answers
├── data/
│   └── raw/                  # Multi-year raw CSV datasets (2015–2025) & product catalogs
├── app.py                    # Main 5-page modular Streamlit dashboard script
├── requirements.txt          # Python library dependencies
├── sql.ipynb                 # Database migration, table creation, and SQL workflows
└── README.md                 # Comprehensive project documentation
```
