# Watch Price Prediction: Exploratory Data Analysis and Modeling

This project develops an end-to-end machine learning pipeline for the appraisal of high-end, second-hand luxury watches. By integrating custom web-scraping infrastructure, rigorous financial data cleaning, and advanced ensemble modeling, the system navigates the complexities of a highly volatile global market.

## 🛠️ Data Collection & Scraping Infrastructure

The foundation of the research lies in a custom-built scraping infrastructure designed to navigate modern web protections while maintaining high throughput.

* **Target Selection:** Chrono24 was chosen as the primary source due to its standardized "Specifications" tables (caliber, case diameter, power reserve, etc.).
* **URL Discovery (Phase 1):** Utilized `undetected_chromedriver` to bypass Cloudflare and bot-detection algorithms. Implemented dynamic wait times (8-12 seconds) and action simulation to avoid IP banning.
* **Detailed Extraction (Phase 2):** A multithreaded Producer-Consumer model using 32 concurrent threads significantly reduced gathering time for technical specifications.
* **Data Resilience:** Utilized the **JSONL** (JSON Lines) format to ensure data safety if the scraper crashed and to allow the script to be resumable.

## 📊 Exploratory Data Analysis (EDA)

The analysis was performed on a filtered dataset of watches priced $\le$ $20,000 to focus on the "Mainstream Luxury" segment and reduce statistical noise from unique "Grail" pieces.

### Market Insights
* **Seller Imbalance:** Professional dealers account for approximately 87% of listings, confirming Chrono24 functions primarily as a B2C platform.
* **Movement Hierarchy:** Automatic and Manual winding movements command the highest median prices, reflecting the prestige value of traditional mechanical horology.
* **Physical Trends:** A clear "oversized watch" trend is visible, with average case diameters increasing from ~34mm in 1990 to over 40mm by 2020.
* **Non-Linear Depreciation:** Luxury watches do not follow a standard linear depreciation model. While modern pieces may lose retail premium, "Vintage" models (50+ years) exhibit extreme volatility and potential spikes in value.



## 🧪 Experiments and Model Training

The pipeline utilizes four high-performance base learners tuned via Randomized Search Cross-Validation, synthesized into a single predictive unit using **Stacked Generalization**.

### Hyperparameter Tuning Summary
* **Random Forest:** Highly sensitive to `max_depth`; the best configuration used `n_estimators: 100` and `max_depth: None`.
* **LightGBM:** Leveraged a leaf-wise growth strategy with `num_leaves: 127` to capture subtle nuances in high-dimensional data.
* **XGBoost:** Utilized deep interactions (`max_depth: 10`) between Brand, Age, and Condition to minimize absolute error.
* **CatBoost:** Native handling of categorical strings (Movement, Material) provided superior stability using symmetric trees.

### Final Performance Summary
| Model Configuration | $R^2$ Score | MAE (USD) | MAPE (%) |
| :--- | :--- | :--- | :--- |
| Random Forest (Best) | 0.7804 | $1,347.56 | 22.36% |
| CatBoost (Best) | 0.7962 | $1,308.63 | 20.95% |
| LightGBM (Best) | 0.7982 | $1,288.23 | 20.58% |
| XGBoost (Best) | 0.7956 | $1,285.43 | 20.92% |
| **Stacked Ensemble** | **0.8252** | **$1,202.47** | **18.77%** |

The final Stacked Ensemble successfully breached the 80% variance explanation threshold, providing a highly reliable tool for luxury asset appraisal.

## ⚙️ Technologies Used

* **Data Handling:** `pandas`, `numpy`, `re`, `currency_converter`.
* **Web Scraping:** `undetected_chromedriver`, `BeautifulSoup4`, `selenium`.
* **Machine Learning:** `xgboost`, `lightgbm`, `CatBoost`, `scikit-learn`.
* **Visualization:** `matplotlib`, `seaborn`, `scipy.stats`.
