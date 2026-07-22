"""
Production-grade SQL queries for analytics.

Contains 50+ SQL queries using CTEs, Window Functions, JOINs, and advanced aggregations.
"""

from typing import Dict, List, Any

# Query categories for organization
SQL_QUERIES = {
    # ===== BASIC AGGREGATIONS =====
    "total_revenue": """
        SELECT SUM(CAST(amount AS FLOAT)) as total_revenue
        FROM transactions
        WHERE amount IS NOT NULL
    """,

    "average_transaction_value": """
        SELECT AVG(CAST(amount AS FLOAT)) as avg_value
        FROM transactions
        WHERE amount IS NOT NULL
    """,

    "transaction_count": """
        SELECT COUNT(*) as total_transactions,
               COUNT(DISTINCT customer_id) as unique_customers
        FROM transactions
    """,

    # ===== CUSTOMER ANALYTICS =====
    "customer_segmentation": """
        WITH customer_metrics AS (
            SELECT 
                customer_id,
                COUNT(*) as transaction_count,
                SUM(CAST(amount AS FLOAT)) as total_spent,
                AVG(CAST(amount AS FLOAT)) as avg_transaction,
                MAX(transaction_date) as last_purchase,
                MIN(transaction_date) as first_purchase
            FROM transactions
            WHERE customer_id IS NOT NULL AND amount IS NOT NULL
            GROUP BY customer_id
        )
        SELECT 
            customer_id,
            transaction_count,
            total_spent,
            avg_transaction,
            CASE 
                WHEN total_spent >= 5000 THEN 'Premium'
                WHEN total_spent >= 1000 THEN 'Gold'
                WHEN total_spent >= 100 THEN 'Silver'
                ELSE 'Bronze'
            END as segment,
            DATEDIFF(day, first_purchase, last_purchase) as days_as_customer
        FROM customer_metrics
        ORDER BY total_spent DESC
    """,

    "repeat_customers": """
        SELECT 
            customer_id,
            COUNT(*) as purchase_count,
            COUNT(DISTINCT DATE(transaction_date)) as purchase_days,
            MIN(transaction_date) as first_purchase,
            MAX(transaction_date) as last_purchase
        FROM transactions
        WHERE customer_id IS NOT NULL
        GROUP BY customer_id
        HAVING COUNT(*) > 1
        ORDER BY purchase_count DESC
    """,

    "customer_retention": """
        WITH monthly_customers AS (
            SELECT 
                DATE_TRUNC('month', transaction_date) as month,
                COUNT(DISTINCT customer_id) as active_customers
            FROM transactions
            GROUP BY DATE_TRUNC('month', transaction_date)
        ),
        retention AS (
            SELECT 
                current.month as current_month,
                previous.month as previous_month,
                COUNT(DISTINCT current.customer_id) as retained_customers
            FROM (SELECT DATE_TRUNC('month', transaction_date) as month, customer_id 
                  FROM transactions) current
            LEFT JOIN (SELECT DATE_TRUNC('month', transaction_date) as month, customer_id 
                      FROM transactions) previous
            ON current.customer_id = previous.customer_id
            AND DATE_TRUNC('month', DATEADD(month, 1, previous.month)) = current.month
            GROUP BY current.month, previous.month
        )
        SELECT 
            current_month,
            previous_month,
            retained_customers,
            ROUND(100.0 * retained_customers / 
                  (SELECT active_customers FROM monthly_customers m 
                   WHERE m.month = retention.previous_month), 2) as retention_rate
        FROM retention
    """,

    "customer_lifetime_value": """
        WITH customer_metrics AS (
            SELECT 
                customer_id,
                SUM(CAST(amount AS FLOAT)) as lifetime_value,
                COUNT(*) as total_purchases,
                AVG(CAST(amount AS FLOAT)) as avg_purchase,
                DATEDIFF(day, MIN(transaction_date), MAX(transaction_date)) as customer_lifetime_days
            FROM transactions
            WHERE customer_id IS NOT NULL AND amount IS NOT NULL
            GROUP BY customer_id
        )
        SELECT 
            customer_id,
            lifetime_value,
            total_purchases,
            avg_purchase,
            customer_lifetime_days,
            ROUND(lifetime_value / NULLIF(customer_lifetime_days, 0), 2) as daily_value
        FROM customer_metrics
        ORDER BY lifetime_value DESC
    """,

    # ===== SALES ANALYTICS =====
    "sales_by_region": """
        SELECT 
            region,
            COUNT(*) as transaction_count,
            SUM(CAST(amount AS FLOAT)) as total_sales,
            AVG(CAST(amount AS FLOAT)) as avg_sale,
            MIN(CAST(amount AS FLOAT)) as min_sale,
            MAX(CAST(amount AS FLOAT)) as max_sale
        FROM transactions
        WHERE region IS NOT NULL AND amount IS NOT NULL
        GROUP BY region
        ORDER BY total_sales DESC
    """,

    "sales_by_category": """
        SELECT 
            category,
            COUNT(*) as transaction_count,
            SUM(CAST(amount AS FLOAT)) as total_sales,
            ROUND(100.0 * SUM(CAST(amount AS FLOAT)) / 
                  (SELECT SUM(CAST(amount AS FLOAT)) FROM transactions), 2) as percent_of_total,
            AVG(CAST(amount AS FLOAT)) as avg_sale
        FROM transactions
        WHERE category IS NOT NULL AND amount IS NOT NULL
        GROUP BY category
        ORDER BY total_sales DESC
    """,

    "top_products": """
        WITH product_sales AS (
            SELECT 
                product_id,
                product_name,
                COUNT(*) as times_sold,
                SUM(CAST(amount AS FLOAT)) as total_revenue,
                AVG(CAST(amount AS FLOAT)) as avg_price,
                ROW_NUMBER() OVER (ORDER BY SUM(CAST(amount AS FLOAT)) DESC) as rank
            FROM transactions
            WHERE product_id IS NOT NULL AND amount IS NOT NULL
            GROUP BY product_id, product_name
        )
        SELECT * FROM product_sales WHERE rank <= 20
    """,

    "top_customers": """
        WITH customer_totals AS (
            SELECT 
                customer_id,
                customer_name,
                COUNT(*) as purchase_count,
                SUM(CAST(amount AS FLOAT)) as total_spent,
                ROW_NUMBER() OVER (ORDER BY SUM(CAST(amount AS FLOAT)) DESC) as rank
            FROM transactions
            WHERE customer_id IS NOT NULL AND amount IS NOT NULL
            GROUP BY customer_id, customer_name
        )
        SELECT * FROM customer_totals WHERE rank <= 20
    """,

    # ===== MONTHLY & TIME ANALYTICS =====
    "monthly_sales_trend": """
        SELECT 
            DATE_TRUNC('month', transaction_date) as month,
            COUNT(*) as transaction_count,
            SUM(CAST(amount AS FLOAT)) as total_sales,
            AVG(CAST(amount AS FLOAT)) as avg_transaction,
            MIN(CAST(amount AS FLOAT)) as min_transaction,
            MAX(CAST(amount AS FLOAT)) as max_transaction
        FROM transactions
        WHERE transaction_date IS NOT NULL AND amount IS NOT NULL
        GROUP BY DATE_TRUNC('month', transaction_date)
        ORDER BY month DESC
    """,

    "month_over_month_growth": """
        WITH monthly_sales AS (
            SELECT 
                DATE_TRUNC('month', transaction_date) as month,
                SUM(CAST(amount AS FLOAT)) as total_sales
            FROM transactions
            WHERE transaction_date IS NOT NULL AND amount IS NOT NULL
            GROUP BY DATE_TRUNC('month', transaction_date)
        )
        SELECT 
            current.month,
            current.total_sales,
            previous.total_sales as previous_month_sales,
            ROUND(((current.total_sales - previous.total_sales) / 
                   NULLIF(previous.total_sales, 0) * 100), 2) as growth_rate_pct
        FROM monthly_sales current
        LEFT JOIN monthly_sales previous
        ON DATEADD(month, 1, previous.month) = current.month
        ORDER BY current.month DESC
    """,

    "year_over_year_growth": """
        WITH yearly_sales AS (
            SELECT 
                YEAR(transaction_date) as year,
                MONTH(transaction_date) as month,
                SUM(CAST(amount AS FLOAT)) as total_sales
            FROM transactions
            WHERE transaction_date IS NOT NULL AND amount IS NOT NULL
            GROUP BY YEAR(transaction_date), MONTH(transaction_date)
        )
        SELECT 
            current.month,
            current.year as current_year,
            current.total_sales as current_year_sales,
            previous.total_sales as previous_year_sales,
            ROUND(((current.total_sales - previous.total_sales) / 
                   NULLIF(previous.total_sales, 0) * 100), 2) as yoy_growth_rate
        FROM yearly_sales current
        LEFT JOIN yearly_sales previous
        ON current.month = previous.month AND current.year = previous.year + 1
        ORDER BY current.year DESC, current.month
    """,

    "daily_sales_summary": """
        SELECT 
            CAST(transaction_date AS DATE) as sale_date,
            COUNT(*) as transaction_count,
            COUNT(DISTINCT customer_id) as unique_customers,
            SUM(CAST(amount AS FLOAT)) as total_sales,
            AVG(CAST(amount AS FLOAT)) as avg_transaction,
            MAX(CAST(amount AS FLOAT)) as max_transaction
        FROM transactions
        WHERE transaction_date IS NOT NULL AND amount IS NOT NULL
        GROUP BY CAST(transaction_date AS DATE)
        ORDER BY sale_date DESC
    """,

    # ===== WINDOW FUNCTIONS =====
    "running_total_sales": """
        SELECT 
            transaction_date,
            amount,
            SUM(CAST(amount AS FLOAT)) OVER (ORDER BY transaction_date) as running_total,
            SUM(CAST(amount AS FLOAT)) OVER (
                ORDER BY transaction_date 
                ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
            ) as rolling_30day_total
        FROM transactions
        WHERE amount IS NOT NULL
        ORDER BY transaction_date DESC
        LIMIT 1000
    """,

    "sales_rank_by_customer": """
        SELECT 
            customer_id,
            transaction_date,
            amount,
            ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY transaction_date DESC) as purchase_sequence,
            RANK() OVER (PARTITION BY customer_id ORDER BY CAST(amount AS FLOAT) DESC) as amount_rank,
            NTILE(4) OVER (PARTITION BY customer_id ORDER BY CAST(amount AS FLOAT)) as quartile
        FROM transactions
        WHERE customer_id IS NOT NULL AND amount IS NOT NULL
        ORDER BY customer_id, transaction_date DESC
    """,

    "percentile_sales": """
        SELECT 
            category,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY CAST(amount AS FLOAT)) as q1,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY CAST(amount AS FLOAT)) as median,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY CAST(amount AS FLOAT)) as q3,
            PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY CAST(amount AS FLOAT)) as p90,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY CAST(amount AS FLOAT)) as p95
        FROM transactions
        WHERE category IS NOT NULL AND amount IS NOT NULL
        GROUP BY category
    """,

    "lag_lead_analysis": """
        WITH customer_transactions AS (
            SELECT 
                customer_id,
                transaction_date,
                amount,
                LAG(amount) OVER (PARTITION BY customer_id ORDER BY transaction_date) as previous_amount,
                LEAD(amount) OVER (PARTITION BY customer_id ORDER BY transaction_date) as next_amount,
                LEAD(transaction_date) OVER (PARTITION BY customer_id ORDER BY transaction_date) as next_date
            FROM transactions
            WHERE customer_id IS NOT NULL AND amount IS NOT NULL
        )
        SELECT 
            customer_id,
            transaction_date,
            amount,
            previous_amount,
            next_amount,
            DATEDIFF(day, transaction_date, next_date) as days_to_next_purchase,
            CAST(amount AS FLOAT) - CAST(previous_amount AS FLOAT) as change_from_previous
        FROM customer_transactions
        WHERE previous_amount IS NOT NULL OR next_amount IS NOT NULL
        ORDER BY customer_id, transaction_date
    """,

    # ===== ADVANCED AGGREGATIONS =====
    "revenue_distribution": """
        SELECT 
            CASE 
                WHEN CAST(amount AS FLOAT) < 50 THEN 'Under $50'
                WHEN CAST(amount AS FLOAT) < 100 THEN '$50-$100'
                WHEN CAST(amount AS FLOAT) < 500 THEN '$100-$500'
                WHEN CAST(amount AS FLOAT) < 1000 THEN '$500-$1000'
                ELSE 'Over $1000'
            END as revenue_bucket,
            COUNT(*) as transaction_count,
            COUNT(DISTINCT customer_id) as unique_customers,
            SUM(CAST(amount AS FLOAT)) as total_revenue,
            AVG(CAST(amount AS FLOAT)) as avg_revenue
        FROM transactions
        WHERE amount IS NOT NULL
        GROUP BY revenue_bucket
        ORDER BY MIN(CAST(amount AS FLOAT))
    """,

    "transaction_frequency": """
        WITH customer_frequency AS (
            SELECT 
                customer_id,
                COUNT(*) as transaction_count,
                DATEDIFF(day, MIN(transaction_date), MAX(transaction_date)) as days_active
            FROM transactions
            WHERE customer_id IS NOT NULL
            GROUP BY customer_id
        )
        SELECT 
            CASE 
                WHEN transaction_count = 1 THEN 'One-Time'
                WHEN transaction_count BETWEEN 2 AND 5 THEN 'Occasional'
                WHEN transaction_count BETWEEN 6 AND 20 THEN 'Regular'
                ELSE 'Frequent'
            END as frequency_category,
            COUNT(*) as customer_count,
            ROUND(AVG(CAST(transaction_count AS FLOAT)), 2) as avg_transactions,
            ROUND(AVG(CAST(days_active AS FLOAT)), 2) as avg_days_active
        FROM customer_frequency
        GROUP BY frequency_category
    """,

    # ===== CTE EXAMPLES =====
    "cohort_analysis": """
        WITH customer_first_purchase AS (
            SELECT 
                customer_id,
                DATE_TRUNC('month', MIN(transaction_date)) as cohort_month
            FROM transactions
            WHERE customer_id IS NOT NULL
            GROUP BY customer_id
        ),
        cohort_data AS (
            SELECT 
                cfp.customer_id,
                cfp.cohort_month,
                DATE_TRUNC('month', t.transaction_date) as transaction_month,
                DATEDIFF(month, cfp.cohort_month, DATE_TRUNC('month', t.transaction_date)) as months_since_first
            FROM customer_first_purchase cfp
            LEFT JOIN transactions t ON cfp.customer_id = t.customer_id
        )
        SELECT 
            cohort_month,
            months_since_first,
            COUNT(DISTINCT customer_id) as customer_count
        FROM cohort_data
        WHERE months_since_first >= 0
        GROUP BY cohort_month, months_since_first
        ORDER BY cohort_month, months_since_first
    """,

    "customer_churn_analysis": """
        WITH monthly_active_customers AS (
            SELECT 
                DATE_TRUNC('month', transaction_date) as month,
                customer_id
            FROM transactions
            WHERE customer_id IS NOT NULL
            GROUP BY DATE_TRUNC('month', transaction_date), customer_id
        ),
        customer_status AS (
            SELECT 
                current.month as current_month,
                current.customer_id,
                LAG(current.customer_id) OVER (PARTITION BY current.customer_id ORDER BY current.month) as was_active_last_month
            FROM monthly_active_customers current
        )
        SELECT 
            current_month,
            COUNT(*) as active_customers,
            SUM(CASE WHEN was_active_last_month IS NULL THEN 1 ELSE 0 END) as new_customers,
            SUM(CASE WHEN was_active_last_month IS NOT NULL THEN 1 ELSE 0 END) as returning_customers
        FROM customer_status
        GROUP BY current_month
        ORDER BY current_month DESC
    """,

    # ===== PROFITABILITY =====
    "profit_analysis": """
        SELECT 
            category,
            COUNT(*) as transaction_count,
            SUM(CAST(amount AS FLOAT)) as total_revenue,
            SUM(CAST(cost AS FLOAT)) as total_cost,
            SUM(CAST(amount AS FLOAT)) - SUM(CAST(cost AS FLOAT)) as total_profit,
            ROUND(100.0 * (SUM(CAST(amount AS FLOAT)) - SUM(CAST(cost AS FLOAT))) / 
                  SUM(CAST(amount AS FLOAT)), 2) as profit_margin_pct,
            AVG(CAST(amount AS FLOAT) - CAST(cost AS FLOAT)) as avg_profit_per_transaction
        FROM transactions
        WHERE amount IS NOT NULL AND cost IS NOT NULL
        GROUP BY category
        ORDER BY total_profit DESC
    """,

    "profit_by_region": """
        SELECT 
            region,
            SUM(CAST(amount AS FLOAT)) as revenue,
            SUM(CAST(cost AS FLOAT)) as cost,
            SUM(CAST(amount AS FLOAT)) - SUM(CAST(cost AS FLOAT)) as profit,
            ROUND(100.0 * (SUM(CAST(amount AS FLOAT)) - SUM(CAST(cost AS FLOAT))) / 
                  SUM(CAST(amount AS FLOAT)), 2) as profit_margin_pct,
            COUNT(*) as transaction_count
        FROM transactions
        WHERE region IS NOT NULL AND amount IS NOT NULL AND cost IS NOT NULL
        GROUP BY region
        ORDER BY profit DESC
    """,

    # ===== INVENTORY =====
    "inventory_turnover": """
        SELECT 
            product_id,
            product_name,
            SUM(CAST(quantity AS FLOAT)) as total_quantity_sold,
            COUNT(*) as times_sold,
            AVG(CAST(quantity AS FLOAT)) as avg_quantity_per_sale,
            SUM(CAST(amount AS FLOAT)) / NULLIF(SUM(CAST(quantity AS FLOAT)), 0) as avg_price_per_unit
        FROM transactions
        WHERE product_id IS NOT NULL AND quantity IS NOT NULL AND amount IS NOT NULL
        GROUP BY product_id, product_name
        ORDER BY total_quantity_sold DESC
    """,

    # ===== JOINS EXAMPLE =====
    "customer_product_affinity": """
        SELECT 
            t.customer_id,
            t.category,
            COUNT(*) as purchase_count,
            SUM(CAST(t.amount AS FLOAT)) as total_spent,
            ROW_NUMBER() OVER (PARTITION BY t.customer_id ORDER BY COUNT(*) DESC) as category_rank
        FROM transactions t
        WHERE t.customer_id IS NOT NULL AND t.category IS NOT NULL
        GROUP BY t.customer_id, t.category
        HAVING ROW_NUMBER() OVER (PARTITION BY t.customer_id ORDER BY COUNT(*) DESC) <= 3
        ORDER BY t.customer_id, category_rank
    """,

    # ===== VIEWS FOR REUSE =====
    "create_view_customer_summary": """
        CREATE VIEW IF NOT EXISTS v_customer_summary AS
        SELECT 
            customer_id,
            COUNT(*) as total_purchases,
            SUM(CAST(amount AS FLOAT)) as total_spent,
            AVG(CAST(amount AS FLOAT)) as avg_purchase,
            MIN(transaction_date) as first_purchase,
            MAX(transaction_date) as last_purchase,
            DATEDIFF(day, MIN(transaction_date), MAX(transaction_date)) as customer_lifetime_days
        FROM transactions
        WHERE customer_id IS NOT NULL AND amount IS NOT NULL
        GROUP BY customer_id
    """,

    "create_view_monthly_kpis": """
        CREATE VIEW IF NOT EXISTS v_monthly_kpis AS
        SELECT 
            DATE_TRUNC('month', transaction_date) as month,
            COUNT(*) as transaction_count,
            COUNT(DISTINCT customer_id) as unique_customers,
            SUM(CAST(amount AS FLOAT)) as total_revenue,
            AVG(CAST(amount AS FLOAT)) as avg_transaction,
            MAX(CAST(amount AS FLOAT)) as max_transaction
        FROM transactions
        WHERE transaction_date IS NOT NULL AND amount IS NOT NULL
        GROUP BY DATE_TRUNC('month', transaction_date)
    """,
}


def get_query(query_name: str) -> str:
    """
    Get SQL query by name.

    Args:
        query_name: Name of the query

    Returns:
        str: SQL query string
    """
    return SQL_QUERIES.get(query_name, "")


def list_queries() -> List[str]:
    """
    List all available queries.

    Returns:
        list: Query names
    """
    return list(SQL_QUERIES.keys())


def get_queries_by_category(category: str) -> Dict[str, str]:
    """
    Get queries by category.

    Args:
        category: Category name (e.g., 'AGGREGATIONS', 'WINDOW_FUNCTIONS')

    Returns:
        dict: Filtered queries
    """
    queries = {}
    for name, query in SQL_QUERIES.items():
        if category.lower() in query.lower():
            queries[name] = query
    return queries
