# Business Recommendations

These recommendations are based on the Phase 5 evaluation and risk scores. The relationships are associations in one historical dataset, not proof that changing a factor will cause retention.

## 1. Prioritize High-Risk Customers

The High tier contains 2,236 customers and has an observed churn rate of 57.83%, compared with 31.89% for Medium and 8.89% for Low. Start a monitored retention queue for High-risk customers, contact them within a defined service-level window, and measure contact rate, offer acceptance, and subsequent churn separately by tier.

## 2. Focus Onboarding on the First Year

Customers with 0-12 months of tenure had a 47.44% churn rate, compared with 9.51% for 49-72 months. High-risk customers also averaged only 13.79 months of tenure. Use 30/60/90-day onboarding checks, service-usage education, and early support follow-ups, then compare 12-month churn with a documented baseline.

## 3. Test Contract Upgrade Offers

Month-to-month customers churned at 42.71%, while two-year customers churned at 2.83%. Both Medium and High tiers most commonly had month-to-month contracts. Test transparent upgrade incentives or commitment benefits for eligible month-to-month customers, measuring conversion, incremental retention, and offer cost rather than assuming every upgrade is beneficial.

## 4. Review Electronic-Check Payment Friction

Electronic-check customers had a 45.29% churn rate, compared with 15.24% for credit-card automatic payment. Medium and High tiers most commonly used electronic check. Test payment-method education or an opt-in automatic-payment nudge, and track successful payment setup, churn, and customer complaints so the action does not penalize customers who prefer their current method.

## 5. Offer Service Reviews to Customers Without Support Add-ons

EDA rates were 41.64% for customers marked `No` for TechSupport and 41.77% for `No` for OnlineSecurity. XGBoost permutation importance also ranked TechSupport at 0.0056 and OnlineSecurity at 0.0055. Offer a needs-based service review or support trial, and measure uptake and churn by the original service category. `No internet service` is a separate category with a 7.40% rate and should not be treated as equivalent to `No`.

## Cost Assumption Note

The evaluation used editable placeholder scenarios, not company facts: offer costs of $10, $25, and $50 with retained-customer values of $100, $250, and $500. The corresponding placeholder net values were $24,070, $60,175, and $120,350 for the selected test threshold. Replace these assumptions with finance-approved values before using them for decisions.

## Limitations

- The findings are associations, not causal conclusions.
- The analysis uses one customer dataset and one historical snapshot.
- The dataset contains no verified retention-offer cost, customer lifetime value, or treatment/outcome fields.
- Thresholds and recommendations need monitoring, calibration, fairness review, and controlled business testing.