"""Validation helpers for InfraMapper inventory checks."""

import ipaddress
from datetime import datetime

import pandas as pd

from utils.inventory_tools import IMPORTANT_COLUMNS


OUTDATED_OS_KEYWORDS = [
    "Windows Server 2012",
    "Windows Server 2008",
    "Ubuntu 18.04",
    "Ubuntu 16.04",
    "Debian 9",
    "CentOS 7",
    "Windows 7",
    "Windows 8",
]


def _is_missing(value):
    """Treat empty values and common placeholders as missing documentation."""
    text = str(value).strip().lower()
    return text in ["", "nan", "none", "null", "n/a", "na", "-"]


def _is_valid_ip(value):
    """Validate an IP address with Python's standard ipaddress module."""
    try:
        ipaddress.ip_address(str(value).strip())
        return True
    except ValueError:
        return False


def find_duplicate_ips(df):
    """Find IP addresses used by more than one asset."""
    if "ip_address" not in df.columns or df.empty:
        return pd.DataFrame(columns=["ip_address", "hostnames", "count"])

    working_df = df.copy()
    working_df["ip_address"] = working_df["ip_address"].astype(str).str.strip()
    working_df = working_df[~working_df["ip_address"].apply(_is_missing)]

    duplicates = (
        working_df.groupby("ip_address")
        .agg(
            hostnames=("hostname", lambda values: ", ".join(values.astype(str))),
            count=("ip_address", "size"),
        )
        .reset_index()
    )
    return duplicates[duplicates["count"] > 1].sort_values("count", ascending=False)


def find_invalid_ips(df):
    """Find rows where ip_address exists but is not a valid IP address."""
    if "ip_address" not in df.columns or df.empty:
        return pd.DataFrame()

    mask = (~df["ip_address"].apply(_is_missing)) & (~df["ip_address"].apply(_is_valid_ip))
    return df[mask].copy()


def find_missing_ips(df):
    """Find rows without an IP address."""
    if "ip_address" not in df.columns or df.empty:
        return df.copy()

    return df[df["ip_address"].apply(_is_missing)].copy()


def calculate_documentation_health(df):
    """Calculate documentation completeness across important columns."""
    if df.empty:
        return {
            "total_missing_fields": 0,
            "total_possible_fields": 0,
            "completeness_percentage": 0,
            "score_label": "Poor",
        }

    available_columns = [column for column in IMPORTANT_COLUMNS if column in df.columns]
    total_possible_fields = len(df) * len(available_columns)
    total_missing_fields = 0

    for column in available_columns:
        total_missing_fields += int(df[column].apply(_is_missing).sum())

    complete_fields = total_possible_fields - total_missing_fields
    completeness_percentage = round((complete_fields / total_possible_fields) * 100, 1)

    if completeness_percentage >= 90:
        score_label = "Excellent"
    elif completeness_percentage >= 75:
        score_label = "Good"
    elif completeness_percentage >= 50:
        score_label = "Needs Review"
    else:
        score_label = "Poor"

    return {
        "total_missing_fields": total_missing_fields,
        "total_possible_fields": total_possible_fields,
        "completeness_percentage": completeness_percentage,
        "score_label": score_label,
    }


def find_missing_documentation(df):
    """Return assets with missing documentation and list the missing fields."""
    rows = []

    for index, row in df.iterrows():
        missing_fields = []
        for column in IMPORTANT_COLUMNS:
            if column in df.columns and _is_missing(row[column]):
                missing_fields.append(column)

        if missing_fields:
            row_data = row.to_dict()
            row_data["missing_fields"] = ", ".join(missing_fields)
            row_data["missing_field_count"] = len(missing_fields)
            rows.append(row_data)

    return pd.DataFrame(rows)


def find_outdated_systems(df):
    """Find assets with operating systems that match known outdated examples."""
    if "os" not in df.columns or df.empty:
        return pd.DataFrame()

    pattern = "|".join(OUTDATED_OS_KEYWORDS)
    return df[df["os"].astype(str).str.contains(pattern, case=False, na=False)].copy()


def find_stale_records(df, threshold_days):
    """Find records where last_updated is older than the chosen threshold."""
    if "last_updated" not in df.columns or df.empty:
        return pd.DataFrame()

    working_df = df.copy()
    working_df["last_updated_date"] = pd.to_datetime(
        working_df["last_updated"],
        errors="coerce",
    )
    today = pd.Timestamp(datetime.now().date())
    working_df["record_age_days"] = (today - working_df["last_updated_date"]).dt.days

    stale_mask = working_df["last_updated_date"].isna() | (
        working_df["record_age_days"] > threshold_days
    )
    return working_df[stale_mask].copy()


def get_issue_list(df):
    """Build one combined issue table for report export."""
    issue_rows = []

    for _, row in find_duplicate_ips(df).iterrows():
        issue_rows.append({
            "issue_type": "Duplicate IP",
            "asset": row.get("hostnames", ""),
            "details": f"IP address {row.get('ip_address', '')} is used {row.get('count', 0)} times.",
        })

    for _, row in find_invalid_ips(df).iterrows():
        issue_rows.append({
            "issue_type": "Invalid IP",
            "asset": row.get("hostname", ""),
            "details": f"Invalid IP value: {row.get('ip_address', '')}",
        })

    for _, row in find_missing_ips(df).iterrows():
        issue_rows.append({
            "issue_type": "Missing IP",
            "asset": row.get("hostname", ""),
            "details": "No IP address documented.",
        })

    for _, row in find_missing_documentation(df).iterrows():
        issue_rows.append({
            "issue_type": "Missing Documentation",
            "asset": row.get("hostname", ""),
            "details": f"Missing fields: {row.get('missing_fields', '')}",
        })

    for _, row in find_outdated_systems(df).iterrows():
        issue_rows.append({
            "issue_type": "Outdated OS",
            "asset": row.get("hostname", ""),
            "details": f"Outdated system detected: {row.get('os', '')}",
        })

    return pd.DataFrame(issue_rows)
