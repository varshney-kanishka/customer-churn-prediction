# Customer Churn Prediction - Final Project Report

## 1. Business Problem

Telecom retention teams need a practical way to prioritize customers who may leave. This project validates the IBM Telco Customer Churn data, builds churn models, ranks customers for review, and exposes the results through SQLite and Streamlit. The model scores are prioritization tools, not guarantees or calibrated probabilities.

## 2. Data Overview and Validation

The raw dataset contains 7,043 rows and 21 columns (`outputs/reports/data_validation_report.md`). It has 5,174 non-churned customers and 1,869 churned customers, or 73.463% and 26.537% respectively (`outputs/reports/data_validation_report.json`). The validation found 11 whitespace-only `TotalCharges` values, no NaN values, no duplicate rows, no duplicate customer IDs, no unexpected categories, and no negative numeric values.

## 3. Cleaning Decisions

The cleaned file retained all 7,043 rows and added `churn_flag`, producing 22 columns (`outputs/reports/data_cleaning_report.md`). `TotalCharges` was converted to numeric. The 11 blank values all belonged to customers with zero tenure, so they were set to `0.0` as not-yet-billed values. No exact duplicate rows were removed. The raw CSV remained unchanged.

## 4. Exploratory Data Analysis

The EDA notebook and saved figures show these real patterns:

- Month-to-month customers had 42.71% churn versus 2.83% for two-year customers (`outputs/figures/churn_rates_main_groups.png`).
- Customers with 0-12 months of tenure had 47.44% churn versus 9.51% for 49-72 months (`outputs/figures/churn_rates_main_groups.png`).
- Electronic-check customers had 45.29% churn versus 15.24% for credit-card automatic payment (`outputs/figures/churn_rates_main_groups.png`).
- Churned customers averaged 17.98 months of tenure and $74.44 in MonthlyCharges; non-churned customers averaged 37.57 months and $61.27 (`outputs/figures/numeric_distributions_by_churn.png`).
- Tenure correlated with `churn_flag` at -0.352 and MonthlyCharges at 0.193 (`outputs/figures/numeric_correlation_heatmap.png`).

## 5. Features and Leakage Controls

The project creates five small features in `src/features.py`:

- `tenure_group`: represents the strong tenure pattern in readable bands.
- `add_on_count`: summarizes subscribed add-on services.
- `average_monthly_charge`: divides TotalCharges by tenure and safely assigns zero for zero-tenure customers.
- `has_internet`: identifies customers whose InternetService is not `No`.
- `has_phone`: identifies customers with PhoneService `Yes`.

`customerID`, text `Churn`, and `churn_flag` were excluded from model inputs. The split is stratified 80/20 with `random_state=42`. Scaling and one-hot encoding are fitted inside sklearn pipelines on training folds only. `No internet service` and `No phone service` remain distinct categorical values.

## 6. Models and Metrics

| Model | Test Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.732 | 0.497 | 0.789 | 0.610 | 0.841 | 0.632 |
| Random Forest | 0.757 | 0.529 | 0.759 | 0.623 | 0.840 | 0.647 |
| XGBoost | 0.745 | 0.513 | 0.799 | 0.625 | 0.845 | 0.661 |

Source: `outputs/reports/model_evaluation_report.md` and `outputs/metrics/evaluation_metrics.json`.

The cross-validation ROC-AUC differences are smaller than their fold standard deviations, so the models are statistically indistinguishable by that measure. XGBoost is the practical final choice for retention because it has the strongest held-out recall, ROC-AUC, PR-AUC, and F1. This is not evidence that it is universally superior.

## 7. Threshold Analysis

The decision threshold was selected by maximizing F1 on five-fold out-of-fold training predictions. The test set was not used for selection. The chosen threshold is 0.50 (`outputs/reports/model_evaluation_report.md`). At that threshold, XGBoost produced TN=751, FP=284, FN=75, and TP=299 on the held-out test set.

## 8. Churn Drivers

XGBoost permutation importance ranked Contract at 0.0736, tenure at 0.0560, InternetService at 0.0097, TechSupport at 0.0056, and OnlineSecurity at 0.0055 (`outputs/reports/model_evaluation_report.md`). Logistic odds-ratio examples included Fiber optic InternetService at 3.432 and month-to-month Contract at 2.009. The two views agree on contract, tenure, and internet/service variables, but correlated fields can change rankings. These are associations, not causes.

## 9. Risk Segmentation

All 7,043 customers received a risk score. Training customers use out-of-fold scores; test customers use the final saved model (`outputs/reports/risk_segmentation_report.md`).

| Risk tier | Customers | Observed churn rate | Average tenure | Average MonthlyCharges |
|---|---:|---:|---:|---:|
| Low | 4,161 | 8.89% | 43.25 | $57.71 |
| Medium | 646 | 31.89% | 26.62 | $67.76 |
| High | 2,236 | 57.83% | 13.79 | $77.01 |

The rates rise monotonically from Low to High. Customer-level scores are saved in `outputs/predictions/customer_risk_scores.csv` and are intentionally ignored by Git.

## 10. SQLite and Dashboard

The database at `data/processed/churn.db` contains 7,043 customer rows, 7,043 risk-score rows, 30 model-metric rows, and 3 tier-summary rows. It uses a customer primary key, a risk-score foreign key, composite model-metric keys, tier indexes, and parameterized fixed queries (`src/database.py`).

The dashboard in `dashboard/app.py` provides Overview, Churn analysis, Model performance, Risk segments, High-risk customer list, and Recommendations sections. It reads from SQLite, uses cached loading, supports filters and CSV download, and labels class-weighted scores as risk scores rather than calibrated probabilities.

## 11. Business Recommendations

The recommendations report is [business_recommendations.md](business_recommendations.md). It proposes high-risk prioritization, first-year onboarding, contract-upgrade tests, electronic-payment education, and support-service reviews. Each recommendation cites a project number and a measurable action. Offer costs and retained-customer values are explicitly editable placeholders, not company facts.

## 12. Limitations and Future Work

- The data is one public historical snapshot; customer behavior and policies may change.
- Associations do not prove that a contract, payment method, or service causes churn.
- Class-weighted model scores rank customers but are not calibrated probabilities.
- The dataset has no verified offer cost, customer lifetime value, treatment, or retention-outcome data.
- Thresholds require calibration, fairness review, and business cost validation.
- Future work should monitor drift, validate interventions experimentally, add approved business-value data, and maintain the dashboard/database deployment. No Phase 7 deployment or GitHub push was performed here.