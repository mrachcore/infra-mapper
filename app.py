from pathlib import Path

import pandas as pd
import streamlit as st

from utils.inventory_tools import (
    IMPORTANT_COLUMNS,
    clean_inventory_dataframe,
    filter_inventory,
    get_assets_by_category,
    get_inventory_summary,
    validate_columns,
)
from utils.report_generator import dataframe_to_csv, generate_text_report
from utils.validation_tools import (
    calculate_documentation_health,
    find_duplicate_ips,
    find_invalid_ips,
    find_missing_documentation,
    find_missing_ips,
    find_outdated_systems,
    find_stale_records,
    get_issue_list,
)


BASE_DIR = Path(__file__).parent
SAMPLE_DATA_PATH = BASE_DIR / "sample_data" / "infrastructure_sample.csv"
LOGO_PATH = BASE_DIR / "assets" / "logo.png"


st.set_page_config(
    page_title="InfraMapper by mrachcore",
    page_icon=str(LOGO_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_custom_css():
    """Apply a dark professional dashboard style."""
    st.markdown(
        """
        <style>
        :root {
            --bg: #07111f;
            --panel: #0d1b2d;
            --panel-soft: #102238;
            --line: rgba(111, 231, 255, 0.18);
            --cyan: #27e4ff;
            --blue: #3a8dff;
            --green: #4ade80;
            --amber: #fbbf24;
            --red: #fb7185;
            --text: #e5f0ff;
            --muted: #8aa1bd;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(39, 228, 255, 0.08), transparent 28rem),
                linear-gradient(135deg, #050b13 0%, #07111f 52%, #0b1726 100%);
            color: var(--text);
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #07111f 0%, #0b1726 100%);
            border-right: 1px solid var(--line);
        }

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: var(--text);
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(16, 34, 56, 0.96), rgba(9, 21, 36, 0.96));
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 18px 18px 14px;
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.25);
        }

        div[data-testid="stMetricValue"] {
            color: var(--cyan);
        }

        .main-title {
            font-size: 3rem;
            font-weight: 800;
            margin-bottom: 0;
            letter-spacing: 0;
        }

        .subtitle {
            color: var(--muted);
            font-size: 1.05rem;
            margin-top: 0;
        }

        .tagline {
            color: var(--cyan);
            font-size: 1.05rem;
            margin-bottom: 1.5rem;
        }

        .card {
            background: linear-gradient(180deg, rgba(16, 34, 56, 0.96), rgba(10, 23, 39, 0.96));
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 1.1rem;
            height: 100%;
            box-shadow: 0 16px 35px rgba(0, 0, 0, 0.22);
        }

        .info-card-title {
            color: var(--text);
            font-weight: 700;
            font-size: 1.02rem;
            margin-bottom: 0.35rem;
        }

        .info-card-body {
            color: var(--muted);
            font-size: 0.94rem;
            line-height: 1.55;
        }

        .badge {
            display: inline-block;
            padding: 0.25rem 0.55rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            margin: 0.12rem;
            border: 1px solid rgba(255, 255, 255, 0.12);
        }

        .badge-green { background: rgba(74, 222, 128, 0.14); color: var(--green); }
        .badge-amber { background: rgba(251, 191, 36, 0.14); color: var(--amber); }
        .badge-red { background: rgba(251, 113, 133, 0.14); color: var(--red); }
        .badge-cyan { background: rgba(39, 228, 255, 0.12); color: var(--cyan); }

        .terminal-box {
            background: #040b13;
            border: 1px solid rgba(39, 228, 255, 0.22);
            border-radius: 12px;
            color: #b7f7ff;
            padding: 1rem;
            font-family: Consolas, Monaco, monospace;
            white-space: pre-wrap;
            max-height: 420px;
            overflow: auto;
        }

        .topology-card {
            border-left: 4px solid var(--cyan);
            background: linear-gradient(90deg, rgba(39, 228, 255, 0.08), rgba(16, 34, 56, 0.65));
            border-radius: 10px;
            padding: 1rem;
        }

        .stDataFrame {
            border: 1px solid var(--line);
            border-radius: 10px;
        }

        h1, h2, h3 {
            color: var(--text);
            letter-spacing: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(title="InfraMapper", subtitle="by mrachcore"):
    """Render consistent page branding."""
    logo_col, text_col = st.columns([1, 5])
    with logo_col:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=True)
    with text_col:
        st.markdown(f"<div class='main-title'>{title}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='subtitle'>{subtitle}</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='tagline'>Local infrastructure inventory & documentation dashboard</div>",
            unsafe_allow_html=True,
        )


def render_info_card(title, body):
    """Render a small dashboard information card."""
    st.markdown(
        f"""
        <div class="card">
            <div class="info-card-title">{title}</div>
            <div class="info-card-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_badge(label, color="cyan"):
    """Render a colored status badge."""
    st.markdown(
        f"<span class='badge badge-{color}'>{label}</span>",
        unsafe_allow_html=True,
    )


def render_terminal_box(text):
    """Render text output in a terminal-style box."""
    st.markdown(f"<div class='terminal-box'>{text}</div>", unsafe_allow_html=True)


def get_inventory():
    """Return the active inventory dataframe from session state."""
    return st.session_state.get("inventory_df")


def show_no_inventory_message():
    """Tell users how to start when no CSV has been loaded yet."""
    st.info("No inventory loaded yet. Go to Upload Inventory and upload a CSV or load the included sample data.")


def load_sample_inventory():
    """Load the bundled sample CSV into session state."""
    sample_df = pd.read_csv(SAMPLE_DATA_PATH)
    st.session_state.inventory_df = clean_inventory_dataframe(sample_df)
    st.session_state.inventory_source = "Included sample CSV"


def dashboard_page():
    render_header()
    st.write("A local dashboard for infrastructure inventory, documentation checks and asset review.")

    df = get_inventory()
    if df is not None and not df.empty:
        summary = get_inventory_summary(df)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Assets", summary["total_assets"])
        col2.metric("Online", summary["online_assets"])
        col3.metric("Offline", summary["offline_assets"])
        col4.metric("Unknown Status", summary["unknown_status_assets"])
    else:
        st.warning("Start by uploading an inventory CSV or load the sample data.")

    st.subheader("What InfraMapper Helps With")
    cards = [
        ("Inventory Upload", "Load CSV-based asset inventories without databases, cloud services, or live scans."),
        ("Asset Overview", "Review devices by type, status, environment, and criticality in clean tables."),
        ("IP Conflict Detection", "Find duplicate, missing, and invalid IP addresses before they cause confusion."),
        ("Documentation Health", "Spot missing ownership, locations, operating systems, and lifecycle fields."),
        ("Lifecycle Review", "Identify outdated systems and stale inventory records for follow-up."),
        ("Report Export", "Generate simple TXT and CSV exports for documentation or portfolio review."),
    ]
    for row_start in range(0, len(cards), 3):
        cols = st.columns(3)
        for col, (title, body) in zip(cols, cards[row_start:row_start + 3]):
            with col:
                render_info_card(title, body)

    st.subheader("How To Use")
    st.markdown(
        """
        1. Upload CSV inventory
        2. Review assets
        3. Check IP conflicts
        4. Validate documentation quality
        5. Export report
        """
    )


def upload_inventory_page():
    st.title("Upload Inventory")
    st.write("Upload a CSV inventory file or load the included sample data.")

    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader("Choose CSV file", type=["csv"])
    with col2:
        st.write("")
        st.write("")
        if st.button("Load Included Sample CSV", use_container_width=True):
            load_sample_inventory()
            st.success("Sample inventory loaded.")

    if uploaded_file is not None:
        try:
            uploaded_df = pd.read_csv(uploaded_file)
            if uploaded_df.empty:
                st.warning("The uploaded CSV is empty. Please add inventory rows and try again.")
            else:
                st.session_state.inventory_df = clean_inventory_dataframe(uploaded_df)
                st.session_state.inventory_source = uploaded_file.name
                st.success("Inventory uploaded and cleaned successfully.")
        except Exception as error:
            st.error(f"Could not read this CSV file. Please check the format and try again. Details: {error}")

    df = get_inventory()
    if df is None:
        show_no_inventory_message()
        return

    validation = validate_columns(df)
    st.subheader("Detected Inventory")
    st.metric("Total Rows", len(df))
    st.write(f"Source: {st.session_state.get('inventory_source', 'Unknown')}")

    st.write("Detected columns:")
    st.write(", ".join(validation["existing_columns"]))

    if validation["missing_columns"]:
        st.warning("Missing recommended columns: " + ", ".join(validation["missing_columns"]))
    else:
        st.success("All recommended columns are available.")

    st.dataframe(df.head(25), use_container_width=True)


def asset_inventory_page():
    st.title("Asset Inventory")
    df = get_inventory()
    if df is None or df.empty:
        show_no_inventory_message()
        return

    summary = get_inventory_summary(df)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Assets", summary["total_assets"])
    col2.metric("Online Assets", summary["online_assets"])
    col3.metric("Offline Assets", summary["offline_assets"])
    col4.metric("Unknown Status", summary["unknown_status_assets"])

    st.subheader("Filters")
    filter_cols = st.columns(4)
    filters = {}
    for column, col in zip(["device_type", "status", "environment", "criticality"], filter_cols):
        options = sorted([value for value in df[column].unique() if value != ""])
        filters[column] = col.multiselect(column.replace("_", " ").title(), options)

    filtered_df = filter_inventory(df, filters)
    st.subheader("Inventory Table")
    st.dataframe(filtered_df, use_container_width=True)

    st.subheader("Inventory Breakdown")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("Assets by Device Type")
        st.dataframe(get_assets_by_category(filtered_df, "device_type"), use_container_width=True)
    with col2:
        st.write("Assets by Environment")
        st.dataframe(get_assets_by_category(filtered_df, "environment"), use_container_width=True)
    with col3:
        st.write("Assets by Criticality")
        st.dataframe(get_assets_by_category(filtered_df, "criticality"), use_container_width=True)


def ip_conflict_page():
    st.title("IP Conflict Check")
    st.write("IP conflicts can cause connectivity issues and should be reviewed.")

    df = get_inventory()
    if df is None or df.empty:
        show_no_inventory_message()
        return

    duplicate_ips = find_duplicate_ips(df)
    invalid_ips = find_invalid_ips(df)
    missing_ips = find_missing_ips(df)

    col1, col2, col3 = st.columns(3)
    col1.metric("Duplicate IP Groups", len(duplicate_ips))
    col2.metric("Invalid IP Records", len(invalid_ips))
    col3.metric("Missing IP Records", len(missing_ips))

    st.subheader("Duplicate IP Addresses")
    if duplicate_ips.empty:
        st.success("No duplicate IP addresses found.")
    else:
        st.dataframe(duplicate_ips, use_container_width=True)

    st.subheader("Invalid IP Values")
    if invalid_ips.empty:
        st.success("No invalid IP values found.")
    else:
        st.dataframe(invalid_ips, use_container_width=True)

    st.subheader("Missing IP Addresses")
    if missing_ips.empty:
        st.success("No missing IP addresses found.")
    else:
        st.dataframe(missing_ips, use_container_width=True)


def documentation_health_page():
    st.title("Documentation Health")
    st.write("Find assets with missing or incomplete documentation.")

    df = get_inventory()
    if df is None or df.empty:
        show_no_inventory_message()
        return

    health = calculate_documentation_health(df)
    missing_docs = find_missing_documentation(df)

    col1, col2, col3 = st.columns(3)
    col1.metric("Completeness", f"{health['completeness_percentage']}%")
    col2.metric("Missing Fields", health["total_missing_fields"])
    col3.metric("Score", health["score_label"])

    score_color = "green"
    if health["score_label"] == "Good":
        score_color = "cyan"
    elif health["score_label"] == "Needs Review":
        score_color = "amber"
    elif health["score_label"] == "Poor":
        score_color = "red"
    render_status_badge(health["score_label"], score_color)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Missing Owner", int(df["owner"].apply(lambda value: str(value).strip() == "").sum()))
    col2.metric("Missing Location", int(df["location"].apply(lambda value: str(value).strip() == "").sum()))
    col3.metric("Missing OS", int(df["os"].apply(lambda value: str(value).strip() == "").sum()))
    col4.metric("Missing Criticality", int(df["criticality"].apply(lambda value: str(value).strip() == "").sum()))

    st.subheader("Assets With Missing Documentation")
    if missing_docs.empty:
        st.success("No missing documentation found.")
    else:
        st.dataframe(missing_docs, use_container_width=True)


def lifecycle_review_page():
    st.title("Lifecycle Review")
    st.write("Lifecycle review helps identify systems that may require updates, replacement, or documentation review.")

    df = get_inventory()
    if df is None or df.empty:
        show_no_inventory_message()
        return

    threshold_days = st.slider("Stale inventory threshold in days", 30, 730, 180, 30)
    outdated_systems = find_outdated_systems(df)
    stale_records = find_stale_records(df, threshold_days)

    high_critical_outdated = outdated_systems[
        outdated_systems["criticality"].str.lower().isin(["high", "critical"])
    ]

    col1, col2, col3 = st.columns(3)
    col1.metric("Outdated Systems", len(outdated_systems))
    col2.metric("Stale Records", len(stale_records))
    col3.metric("High/Critical Outdated", len(high_critical_outdated))

    st.subheader("Outdated Systems")
    if outdated_systems.empty:
        st.success("No outdated systems found from the built-in example list.")
    else:
        st.dataframe(outdated_systems, use_container_width=True)

    st.subheader("Stale Inventory Records")
    if stale_records.empty:
        st.success("No stale records found for the selected threshold.")
    else:
        st.dataframe(stale_records, use_container_width=True)


def reports_page():
    st.title("Reports")
    df = get_inventory()
    if df is None or df.empty:
        show_no_inventory_message()
        return

    threshold_days = st.slider("Report stale record threshold in days", 30, 730, 180, 30)
    summary = get_inventory_summary(df)
    health = calculate_documentation_health(df)
    duplicate_ips = find_duplicate_ips(df)
    invalid_ips = find_invalid_ips(df)
    missing_ips = find_missing_ips(df)
    outdated_systems = find_outdated_systems(df)
    stale_records = find_stale_records(df, threshold_days)
    issue_list = get_issue_list(df)

    critical_assets = df[df["criticality"].str.lower() == "critical"]["hostname"].head(10).tolist()
    issues = {
        "duplicate_ip_groups": len(duplicate_ips),
        "invalid_ip_count": len(invalid_ips),
        "missing_ip_count": len(missing_ips),
        "documentation_completeness": health["completeness_percentage"],
        "documentation_score": health["score_label"],
        "outdated_system_count": len(outdated_systems),
        "stale_record_count": len(stale_records),
        "top_critical_assets": critical_assets,
    }
    report_text = generate_text_report(summary, issues, threshold_days)

    st.subheader("Report Preview")
    render_terminal_box(report_text)

    col1, col2, col3 = st.columns(3)
    col1.download_button(
        "Download TXT Report",
        data=report_text,
        file_name="inframapper_report.txt",
        mime="text/plain",
        use_container_width=True,
    )
    col2.download_button(
        "Download Cleaned Inventory CSV",
        data=dataframe_to_csv(df),
        file_name="cleaned_inventory.csv",
        mime="text/csv",
        use_container_width=True,
    )
    col3.download_button(
        "Download Issue List CSV",
        data=dataframe_to_csv(issue_list),
        file_name="inframapper_issues.csv",
        mime="text/csv",
        use_container_width=True,
    )


def about_page():
    render_header()
    st.write(
        "InfraMapper is a local infrastructure inventory and documentation dashboard created as part "
        "of my learning path during my Ausbildung as Fachinformatiker für Systemintegration."
    )

    st.subheader("Purpose")
    st.markdown(
        """
        - Document infrastructure assets
        - Review inventory quality
        - Detect IP conflicts
        - Identify missing documentation
        - Review outdated systems
        - Generate infrastructure reports
        """
    )

    st.subheader("Skills")
    badges = [
        "Python",
        "Streamlit",
        "pandas",
        "CSV Analysis",
        "Infrastructure Inventory",
        "Asset Management",
        "Documentation",
        "Reporting",
        "Sysadmin Tools",
    ]
    badge_html = "".join([f"<span class='badge badge-cyan'>{badge}</span>" for badge in badges])
    st.markdown(badge_html, unsafe_allow_html=True)

    st.subheader("Project Link")
    st.write("https://github.com/mrachcore/infra-mapper")

    st.subheader("Disclaimer")
    st.warning(
        "This tool does not scan networks or connect to production systems. "
        "It only analyzes uploaded CSV inventory files locally."
    )


def render_sidebar():
    """Render the sidebar navigation and small project status."""
    if LOGO_PATH.exists():
        st.sidebar.image(str(LOGO_PATH), use_container_width=True)
    st.sidebar.title("InfraMapper")
    st.sidebar.caption("by mrachcore")

    pages = [
        "Dashboard",
        "Upload Inventory",
        "Asset Inventory",
        "IP Conflict Check",
        "Documentation Health",
        "Lifecycle Review",
        "Reports",
        "About",
    ]
    selected_page = st.sidebar.radio("Navigation", pages)

    st.sidebar.markdown("---")
    df = get_inventory()
    if df is not None and not df.empty:
        st.sidebar.success(f"{len(df)} assets loaded")
    else:
        st.sidebar.info("No inventory loaded")

    return selected_page


def main():
    apply_custom_css()
    selected_page = render_sidebar()

    if selected_page == "Dashboard":
        dashboard_page()
    elif selected_page == "Upload Inventory":
        upload_inventory_page()
    elif selected_page == "Asset Inventory":
        asset_inventory_page()
    elif selected_page == "IP Conflict Check":
        ip_conflict_page()
    elif selected_page == "Documentation Health":
        documentation_health_page()
    elif selected_page == "Lifecycle Review":
        lifecycle_review_page()
    elif selected_page == "Reports":
        reports_page()
    elif selected_page == "About":
        about_page()


if __name__ == "__main__":
    main()
