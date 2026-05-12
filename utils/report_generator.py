"""Report helpers for InfraMapper."""

from datetime import datetime
from io import StringIO


def _format_count_table(title, table_df):
    """Convert a small count dataframe into readable report lines."""
    lines = [title]

    if table_df is None or table_df.empty:
        lines.append("- No data available")
        return lines

    first_column = table_df.columns[0]
    for _, row in table_df.iterrows():
        lines.append(f"- {row[first_column]}: {row['count']}")

    return lines


def generate_text_report(summary, issues, threshold_days):
    """Generate a clean text report that can be downloaded from Streamlit."""
    report_lines = [
        "InfraMapper Infrastructure Report",
        "by mrachcore",
        "",
        f"Audit date/time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Stale record threshold: {threshold_days} days",
        "",
        "Inventory Summary",
        f"- Total assets: {summary.get('total_assets', 0)}",
        f"- Online assets: {summary.get('online_assets', 0)}",
        f"- Offline assets: {summary.get('offline_assets', 0)}",
        f"- Unknown status assets: {summary.get('unknown_status_assets', 0)}",
        "",
    ]

    report_lines.extend(_format_count_table("Assets by Type", summary.get("by_device_type")))
    report_lines.append("")
    report_lines.extend(_format_count_table("Assets by Status", summary.get("by_status")))
    report_lines.append("")

    report_lines.extend([
        "Checks",
        f"- Duplicate IP groups: {issues.get('duplicate_ip_groups', 0)}",
        f"- Invalid IP records: {issues.get('invalid_ip_count', 0)}",
        f"- Missing IP records: {issues.get('missing_ip_count', 0)}",
        f"- Documentation completeness: {issues.get('documentation_completeness', 0)}%",
        f"- Documentation score: {issues.get('documentation_score', 'Unknown')}",
        f"- Outdated systems: {issues.get('outdated_system_count', 0)}",
        f"- Stale records: {issues.get('stale_record_count', 0)}",
        "",
        "Top Critical Assets",
    ])

    top_critical_assets = issues.get("top_critical_assets", [])
    if top_critical_assets:
        for asset in top_critical_assets:
            report_lines.append(f"- {asset}")
    else:
        report_lines.append("- No critical assets listed")

    report_lines.extend([
        "",
        "Recommendations",
        "- Review duplicate IP addresses before making infrastructure changes.",
        "- Complete missing owner, location, OS, and criticality fields.",
        "- Prioritize outdated high and critical systems for lifecycle planning.",
        "- Update stale inventory records and agree on a regular documentation cycle.",
        "- Keep this CSV inventory in version control or a controlled documentation process.",
        "",
        "Disclaimer",
        "This report is generated from uploaded CSV data only. InfraMapper does not scan networks or connect to production systems.",
    ])

    return "\n".join(report_lines)


def dataframe_to_csv(df):
    """Convert a dataframe to CSV text for Streamlit download buttons."""
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()
