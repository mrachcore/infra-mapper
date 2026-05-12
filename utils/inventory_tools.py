"""Simple helper functions for working with infrastructure inventory data."""

import pandas as pd


IMPORTANT_COLUMNS = [
    "hostname",
    "ip_address",
    "device_type",
    "os",
    "location",
    "owner",
    "status",
    "environment",
    "criticality",
    "last_updated",
]


def normalize_columns(df):
    """Return a copy of the dataframe with clean, predictable column names."""
    clean_df = df.copy()
    clean_df.columns = (
        clean_df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )
    return clean_df


def validate_columns(df):
    """Check which recommended inventory columns are available or missing."""
    existing_columns = list(df.columns)
    missing_columns = [column for column in IMPORTANT_COLUMNS if column not in existing_columns]
    return {
        "existing_columns": existing_columns,
        "missing_columns": missing_columns,
        "has_minimum_columns": "hostname" in existing_columns and "ip_address" in existing_columns,
    }


def clean_inventory_dataframe(df):
    """Normalize columns, remove empty rows and fill missing optional columns."""
    clean_df = normalize_columns(df)
    clean_df = clean_df.drop_duplicates()
    clean_df = clean_df.dropna(how="all")

    # Add missing expected columns so the app can continue gracefully.
    for column in IMPORTANT_COLUMNS:
        if column not in clean_df.columns:
            clean_df[column] = ""

    for column in clean_df.columns:
        clean_df[column] = clean_df[column].fillna("").astype(str).str.strip()

    return clean_df


def get_inventory_summary(df):
    """Create simple inventory metrics used on the dashboard and reports."""
    total_assets = len(df)

    status_series = df.get("status", pd.Series(dtype=str)).astype(str).str.lower()
    online_assets = int((status_series == "online").sum())
    offline_assets = int((status_series == "offline").sum())
    unknown_status_assets = int((~status_series.isin(["online", "offline"])).sum())

    return {
        "total_assets": total_assets,
        "online_assets": online_assets,
        "offline_assets": offline_assets,
        "unknown_status_assets": unknown_status_assets,
        "by_device_type": get_assets_by_category(df, "device_type"),
        "by_environment": get_assets_by_category(df, "environment"),
        "by_criticality": get_assets_by_category(df, "criticality"),
        "by_status": get_assets_by_category(df, "status"),
    }


def filter_inventory(df, filters):
    """Filter inventory by selected sidebar/page filter values."""
    filtered_df = df.copy()

    for column, selected_values in filters.items():
        if column in filtered_df.columns and selected_values:
            filtered_df = filtered_df[filtered_df[column].isin(selected_values)]

    return filtered_df


def get_assets_by_category(df, column):
    """Return a count table for a category such as status or device_type."""
    if column not in df.columns or df.empty:
        return pd.DataFrame(columns=[column, "count"])

    category_counts = (
        df[column]
        .replace("", "missing")
        .fillna("missing")
        .value_counts()
        .reset_index()
    )
    category_counts.columns = [column, "count"]
    return category_counts
