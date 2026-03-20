---
name: data-processing
description: Data processing and ETL pipeline patterns. Use when working with data processing concepts or setting up related projects.
---

# Data Processing Pipelines

## Core Principles

- **Idempotent**: Re-running a pipeline produces the same result
- **Schema Validation**: Validate data at ingestion boundaries
- **Incremental Processing**: Process only new/changed data when possible
- **Observability**: Log record counts, processing times, error rates

## ETL vs ELT

### ETL (Extract, Transform, Load)
- Transform before loading into destination
- Good for: structured data, strict schemas

### ELT (Extract, Load, Transform)
- Load raw data, transform in-place
- Good for: data lakes, exploratory analytics

## Pandas Pipeline
```python
def process_orders(raw_df: pd.DataFrame) -> pd.DataFrame:
    return (raw_df
        .dropna(subset=['order_id', 'amount'])
        .assign(amount=lambda df: df['amount'].astype(float))
        .query('amount > 0')
        .assign(created_date=lambda df: pd.to_datetime(df['created_at']).dt.date)
        .groupby('created_date')
        .agg(total=('amount', 'sum'), count=('order_id', 'nunique'))
        .reset_index()
    )
```

## Apache Spark Pattern
```python
df = spark.read.parquet("s3://raw/orders/")
result = (df
    .filter(col("amount") > 0)
    .groupBy("date")
    .agg(sum("amount").alias("total"))
)
result.write.mode("overwrite").parquet("s3://processed/daily_totals/")
```

## Anti-Patterns
- Processing entire dataset when only delta is needed
- No data quality checks between pipeline stages
- Storing transformed data without lineage metadata
