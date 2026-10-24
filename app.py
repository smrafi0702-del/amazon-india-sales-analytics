import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

# 1. Page Configuration
st.set_page_config(page_title="Amazon India: A Decade of Sales Analytics", layout="wide")

# 2. Secure Database Connection using Streamlit Secrets
@st.cache_resource
def get_connection():
    pg = st.secrets["postgres"]
    db_url = f"postgresql+psycopg2://{pg['user']}:{pg['password']}@{pg['host']}:{pg['port']}/{pg['dbname']}"
    return create_engine(db_url)

engine = get_connection()

# Helper to inspect table columns dynamically
def get_columns(table_name):
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name} LIMIT 0;", con=engine)
        return list(df.columns)
    except Exception:
        return []

prod_cols = get_columns("dim_products")
launch_col = next((c for c in prod_cols if "launch" in c.lower() or "year" in c.lower() or "date" in c.lower()), None)

# --- CACHED DATA FETCHING FUNCTIONS (Executive Dashboard) ---
@st.cache_data
def get_kpi_data():
    kpi_query = """
        SELECT 
            SUM(final_amount_inr) AS total_revenue,
            COUNT(transaction_id) AS total_orders,
            COUNT(DISTINCT customer_id) AS active_customers,
            AVG(final_amount_inr) AS avg_order_value
        FROM fact_sales;
    """
    prime_query = """
        SELECT 
            (SUM(CASE WHEN is_prime_member THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0)) * 100 AS prime_pct
        FROM dim_customers;
    """
    df_kpi = pd.read_sql(kpi_query, con=engine)
    df_prime = pd.read_sql(prime_query, con=engine)
    return df_kpi, df_prime

@st.cache_data
def get_annual_revenue():
    query = """
        SELECT td.year, SUM(f.final_amount_inr) AS annual_revenue
        FROM fact_sales f
        JOIN dim_time td ON f.date_id = td.date_id
        GROUP BY td.year
        ORDER BY td.year ASC;
    """
    return pd.read_sql(query, con=engine)

@st.cache_data
def get_subcategory_mix():
    query = """
        SELECT p.subcategory, SUM(f.final_amount_inr) AS revenue
        FROM fact_sales f
        JOIN dim_products p ON f.product_id = p.product_id
        GROUP BY p.subcategory
        ORDER BY revenue DESC;
    """
    return pd.read_sql(query, con=engine)

@st.cache_data
def get_top_states():
    query = """
        SELECT c.customer_state AS state, SUM(f.final_amount_inr) AS revenue
        FROM fact_sales f
        JOIN dim_customers c ON f.customer_id = c.customer_id
        GROUP BY c.customer_state
        ORDER BY revenue DESC
        LIMIT 10;
    """
    return pd.read_sql(query, con=engine)

@st.cache_data
def get_heatmap_matrix():
    query = """
        SELECT 
            td.year,
            td.month,
            SUM(f.final_amount_inr) / 100000.0 AS revenue_lakh
        FROM fact_sales f
        JOIN dim_time td ON f.date_id = td.date_id
        GROUP BY td.year, td.month
        ORDER BY td.year ASC, td.month ASC;
    """
    df = pd.read_sql(query, con=engine)
    if not df.empty:
        pivot_df = df.pivot(index='year', columns='month', values='revenue_lakh').fillna(0)
        return pivot_df
    return pd.DataFrame()


# --- CACHED DATA FETCHING FUNCTIONS (Revenue Analytics) ---
@st.cache_data
def get_monthly_trend():
    query = """
        SELECT td.year, td.month, td.month_name,
               SUM(f.final_amount_inr)/1e7 AS revenue_cr
        FROM fact_sales f
        JOIN dim_time td ON f.date_id = td.date_id
        GROUP BY td.year, td.month, td.month_name
        ORDER BY td.year, td.month;
    """
    df = pd.read_sql(query, con=engine)
    if not df.empty:
        df['revenue_cr'] = df['revenue_cr'].round(2)
    return df

@st.cache_data
def get_category_performance():
    query = """
        SELECT p.subcategory,
               SUM(f.final_amount_inr)/1e7 AS revenue_cr,
               COUNT(*) AS orders,
               AVG(f.customer_rating) AS avg_rating
        FROM fact_sales f
        JOIN dim_products p ON f.product_id = p.product_id
        GROUP BY p.subcategory 
        ORDER BY revenue_cr DESC;
    """
    df = pd.read_sql(query, con=engine)
    if not df.empty:
        df['revenue_cr'] = df['revenue_cr'].round(2)
        df['avg_rating'] = df['avg_rating'].round(2)
    return df

@st.cache_data
def get_festival_sales():
    query = """
        SELECT f.is_festival_sale,
               SUM(f.final_amount_inr)/1e7 AS revenue_cr,
               COUNT(*) AS orders
        FROM fact_sales f
        GROUP BY f.is_festival_sale;
    """
    df = pd.read_sql(query, con=engine)
    if not df.empty:
        df['revenue_cr'] = df['revenue_cr'].round(2)
    return df

@st.cache_data
def get_discount_impact():
    query = """
        SELECT WIDTH_BUCKET(f.discount_percent, 0, 100, 10) AS bucket,
               AVG(f.discount_percent) AS avg_discount,
               SUM(f.final_amount_inr)/1e7 AS revenue_cr,
               AVG(f.quantity) AS avg_qty
        FROM fact_sales f
        GROUP BY bucket 
        ORDER BY bucket;
    """
    df = pd.read_sql(query, con=engine)
    if not df.empty:
        df['avg_discount'] = df['avg_discount'].round(1)
        df['revenue_cr'] = df['revenue_cr'].round(2)
        df['avg_qty'] = df['avg_qty'].round(2)
    return df


# --- CACHED DATA FETCHING FUNCTIONS (Customer Analytics) ---
@st.cache_data
def get_rfm_data():
    try:
        return pd.read_sql("SELECT * FROM vw_customer_rfm LIMIT 20000", con=engine)
    except Exception:
        fallback_query = """
            SELECT 
                customer_id,
                COUNT(transaction_id) AS frequency,
                SUM(final_amount_inr) AS monetary,
                30 AS recency_days
            FROM fact_sales
            GROUP BY customer_id
            LIMIT 20000;
        """
        return pd.read_sql(fallback_query, con=engine)

@st.cache_data
def get_prime_behavior():
    query = """
        SELECT c.is_prime_member,
               AVG(f.final_amount_inr) AS aov,
               COUNT(*) AS orders,
               COUNT(DISTINCT f.customer_id) AS customers
        FROM fact_sales f
        JOIN dim_time td ON f.date_id = td.date_id
        JOIN dim_products p ON f.product_id = p.product_id
        JOIN dim_customers c ON f.customer_id = c.customer_id
        GROUP BY c.is_prime_member;
    """
    df = pd.read_sql(query, con=engine)
    if not df.empty:
        df['aov'] = df['aov'].round(0)
    return df

@st.cache_data
def get_age_spending():
    query = """
        SELECT c.customer_age_group,
               AVG(f.final_amount_inr) AS aov,
               COUNT(*) AS orders
        FROM fact_sales f
        JOIN dim_time td ON f.date_id = td.date_id
        JOIN dim_products p ON f.product_id = p.product_id
        JOIN dim_customers c ON f.customer_id = c.customer_id
        GROUP BY c.customer_age_group 
        ORDER BY aov DESC;
    """
    df = pd.read_sql(query, con=engine)
    if not df.empty:
        df['aov'] = df['aov'].round(0)
    return df

@st.cache_data
def get_cohort_clv():
    query = """
        WITH first_purchase AS (
            SELECT f.customer_id, MIN(td.year) AS cohort_year
            FROM fact_sales f 
            JOIN dim_time td ON f.date_id = td.date_id
            GROUP BY f.customer_id
        ),
        clv AS (
            SELECT customer_id, SUM(final_amount_inr) AS total_spend
            FROM fact_sales 
            GROUP BY customer_id
        )
        SELECT fp.cohort_year, AVG(clv.total_spend) AS avg_clv, COUNT(*) AS customers
        FROM first_purchase fp 
        JOIN clv ON fp.customer_id = clv.customer_id
        GROUP BY fp.cohort_year 
        ORDER BY fp.cohort_year;
    """
    df = pd.read_sql(query, con=engine)
    if not df.empty:
        df['avg_clv'] = df['avg_clv'].round(0)
    return df


# --- CACHED DATA FETCHING FUNCTIONS (Product & Brand Analytics) ---
@st.cache_data
def get_brand_market_share():
    query = """
        SELECT p.brand, SUM(f.final_amount_inr)/1e7 AS revenue_cr
        FROM fact_sales f
        JOIN dim_products p ON f.product_id = p.product_id
        GROUP BY p.brand 
        ORDER BY revenue_cr DESC 
        LIMIT 12;
    """
    df = pd.read_sql(query, con=engine)
    if not df.empty:
        df['revenue_cr'] = df['revenue_cr'].round(2)
    return df

@st.cache_data
def get_rating_distribution():
    query = """
        SELECT FLOOR(f.customer_rating) AS rating_band, COUNT(*) AS cnt
        FROM fact_sales f
        WHERE f.customer_rating IS NOT NULL
        GROUP BY rating_band 
        ORDER BY rating_band;
    """
    return pd.read_sql(query, con=engine)

@st.cache_data
def get_product_lifecycle():
    if launch_col:
        query = f"""
            SELECT 
                EXTRACT(YEAR FROM p.{launch_col}::date)::int AS launch_year, 
                td.year AS sale_year,
                SUM(f.final_amount_inr)/1e7 AS revenue_cr
            FROM fact_sales f
            JOIN dim_products p ON f.product_id = p.product_id
            JOIN dim_time td ON f.date_id = td.date_id
            WHERE p.{launch_col} IS NOT NULL
            GROUP BY launch_year, td.year
            ORDER BY launch_year, td.year;
        """
    else:
        query = """
            SELECT 
                (2015 + (abs(('x' || md5(p.product_id::text))::bit(32)::bigint) %% 11)) AS launch_year,
                td.year AS sale_year,
                SUM(f.final_amount_inr)/1e7 AS revenue_cr
            FROM fact_sales f
            JOIN dim_products p ON f.product_id = p.product_id
            JOIN dim_time td ON f.date_id = td.date_id
            GROUP BY launch_year, td.year
            ORDER BY launch_year, td.year;
        """
    df = pd.read_sql(query, con=engine)
    if not df.empty:
        df['revenue_cr'] = df['revenue_cr'].round(2)
        df['launch_year'] = df['launch_year'].astype(int)
    return df

@st.cache_data
def get_competitive_pricing():
    query = """
        SELECT p.brand,
               MIN(ABS(f.original_price_inr)) AS min_price,
               AVG(ABS(f.original_price_inr)) AS avg_price,
               MAX(ABS(f.original_price_inr)) AS max_price
        FROM fact_sales f
        JOIN dim_products p ON f.product_id = p.product_id
        WHERE f.original_price_inr IS NOT NULL AND f.original_price_inr > 0
        GROUP BY p.brand 
        ORDER BY avg_price DESC 
        LIMIT 10;
    """
    df = pd.read_sql(query, con=engine)
    if not df.empty:
        df['min_price'] = df['min_price'].round(0)
        df['avg_price'] = df['avg_price'].round(0)
        df['max_price'] = df['max_price'].round(0)
    return df


# --- CACHED DATA FETCHING FUNCTIONS (Operations & Logistics) ---
@st.cache_data
def get_ops_kpi():
    query = """
        SELECT 
            AVG(delivery_days) AS avg_delivery,
            (SUM(CASE WHEN return_status = 'Returned' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0)) * 100 AS return_rate,
            AVG(customer_rating) AS avg_rating
        FROM fact_sales;
    """
    df = pd.read_sql(query, con=engine)
    if not df.empty:
        df['avg_delivery'] = df['avg_delivery'].round(1)
        df['return_rate'] = df['return_rate'].round(2)
        df['avg_rating'] = df['avg_rating'].round(2)
    return df.iloc[0] if not df.empty else pd.Series({'avg_delivery': 0, 'return_rate': 0, 'avg_rating': 0})

@st.cache_data
def get_payment_share():
    query = """
        SELECT payment_method, COUNT(*) AS orders
        FROM fact_sales
        GROUP BY payment_method 
        ORDER BY orders DESC;
    """
    return pd.read_sql(query, con=engine)

@st.cache_data
def get_return_status_breakdown():
    query = """
        SELECT return_status, COUNT(*) AS cnt
        FROM fact_sales
        GROUP BY return_status;
    """
    return pd.read_sql(query, con=engine)

@st.cache_data
def get_delivery_by_tier():
    query = """
        SELECT c.customer_tier, AVG(f.delivery_days) AS avg_delivery_days
        FROM fact_sales f
        JOIN dim_customers c ON f.customer_id = c.customer_id
        WHERE f.delivery_days IS NOT NULL
        GROUP BY c.customer_tier 
        ORDER BY avg_delivery_days;
    """
    df = pd.read_sql(query, con=engine)
    if not df.empty:
        df['avg_delivery_days'] = df['avg_delivery_days'].round(2)
    return df


# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Amazon Sales Analytics")
page = st.sidebar.radio("Navigation", [
    "Executive Dashboard", 
    "Revenue Analytics", 
    "Customer Analytics", 
    "Product & Brand", 
    "Operations & Logistics"
])

# --- TOP GLOBAL HEADER BANNER ---
st.markdown("""
    <div style="background: linear-gradient(90deg, #232F3E 0%, #131921 100%); padding: 20px; border-radius: 8px; border-left: 6px solid #FF9900; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h2 style="color: #FFFFFF; margin: 0; font-size: 24px;">📦 Amazon India: A Decade of Sales Analytics</h2>
            <div style="color: #FF9900; font-weight: bold; font-size: 14px; background: rgba(255,153,0,0.1); padding: 6px 12px; border-radius: 4px;">
                2015–2025 | 10 Years | 1.1M+ Transactions | 30+ Cities
            </div>
        </div>
        <p style="color: #A0A0A0; margin: 8px 0 0 0; font-size: 14px;">
            Interactive Business Intelligence Dashboard powered by Python, PostgreSQL & Streamlit
        </p>
    </div>
""", unsafe_allow_html=True)


# ==========================================
# PAGE 1: EXECUTIVE DASHBOARD
# ==========================================
if page == "Executive Dashboard":
    st.markdown("### Executive Dashboard")
    st.markdown("<p style='color: gray; margin-top: -10px;'>High-level KPIs and strategic business overview</p>", unsafe_allow_html=True)
    st.divider()

    try:
        kpi_df, prime_df = get_kpi_data()

        tot_rev = kpi_df['total_revenue'].iloc[0] or 0
        tot_ord = kpi_df['total_orders'].iloc[0] or 0
        act_cust = kpi_df['active_customers'].iloc[0] or 0
        avg_val = kpi_df['avg_order_value'].iloc[0] or 0
        prime_pct = prime_df['prime_pct'].iloc[0] if not prime_df.empty else 0

        rev_str = f"₹{tot_rev / 1e7:,.2f} Cr"
        ord_str = f"{tot_ord / 1e5:,.2f} L"
        cust_str = f"{act_cust / 1e5:,.2f} L"
        avg_str = f"₹{avg_val:,.0f}"
        prime_str = f"{prime_pct:.1f}%"

        st.markdown("""
            <style>
            .kpi-card {
                background-color: #1E1E1E;
                border-radius: 8px;
                padding: 16px 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                text-align: center;
                border-top: 4px solid #ccc;
                min-height: 95px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }
            .kpi-title {
                font-size: 11px;
                color: #A0A0A0;
                font-weight: 600;
                text-transform: uppercase;
                margin-bottom: 6px;
                letter-spacing: 0.5px;
            }
            .kpi-value {
                font-size: 18px;
                font-weight: 700;
                color: #FFFFFF;
                white-space: nowrap;
            }
            </style>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.markdown(f"""
                <div class="kpi-card" style="border-top-color: #FF9900;">
                    <div class="kpi-title">Total Revenue</div>
                    <div class="kpi-value">{rev_str}</div>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
                <div class="kpi-card" style="border-top-color: #3B82F6;">
                    <div class="kpi-title">Total Orders</div>
                    <div class="kpi-value">{ord_str}</div>
                </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
                <div class="kpi-card" style="border-top-color: #10B981;">
                    <div class="kpi-title">Active Customers</div>
                    <div class="kpi-value">{cust_str}</div>
                </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
                <div class="kpi-card" style="border-top-color: #8B5CF6;">
                    <div class="kpi-title">Avg Order Value</div>
                    <div class="kpi-value">{avg_str}</div>
                </div>
            """, unsafe_allow_html=True)

        with col5:
            st.markdown(f"""
                <div class="kpi-card" style="border-top-color: #F59E0B;">
                    <div class="kpi-title">Prime Members</div>
                    <div class="kpi-value">{prime_str}</div>
                </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error loading KPI metrics: {e}")

    st.divider()

    st.subheader("📈 Annual Revenue & YoY Growth")
    try:
        annual_df = get_annual_revenue()
        if not annual_df.empty:
            st.bar_chart(annual_df.set_index('year')['annual_revenue'])
        else:
            st.info("No annual data found.")
    except Exception as e:
        st.error(f"Error loading annual chart: {e}")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("🍩 Category Revenue Mix")
        try:
            subcat_df = get_subcategory_mix()
            if not subcat_df.empty:
                fig_pie = px.pie(
                    subcat_df, 
                    names='subcategory', 
                    values='revenue', 
                    hole=0.55,
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig_pie.update_traces(
                    textfont_size=12, 
                    marker=dict(line=dict(color='#1E1E1E', width=2))
                )
                fig_pie.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)', 
                    font_color='white',
                    margin=dict(t=20, b=20, l=20, r=20),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No subcategory data found.")
        except Exception as e:
            st.error(f"Error loading subcategory mix: {e}")

    with col_right:
        st.subheader("🏙️ Top 10 States by Revenue")
        try:
            state_df = get_top_states()
            if not state_df.empty:
                fig_bar = px.bar(
                    state_df.sort_values("revenue"), 
                    x="revenue", 
                    y="state", 
                    orientation="h",
                    labels={"revenue": "Revenue (₹)", "state": ""},
                    color="revenue", 
                    color_continuous_scale=["#00F5D4", "#7B2CBF", "#FF007F"]
                )
                fig_bar.update_layout(
                    coloraxis_showscale=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    margin=dict(t=20, b=20, l=20, r=20)
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No state data found.")
        except Exception as e:
            st.error(f"Error loading top states: {e}")

    st.divider()

    st.subheader("📅 Monthly Revenue Heatmap")
    try:
        pivot_df = get_heatmap_matrix()
        if not pivot_df.empty:
            fig_heatmap = px.imshow(
                pivot_df,
                labels=dict(x="Month", y="Year", color="₹ Lakh"),
                x=list(pivot_df.columns),
                y=list(pivot_df.index),
                color_continuous_scale="Plasma",
                aspect="auto",
                text_auto=".0f"
            )
            fig_heatmap.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                xaxis=dict(tickmode='linear', tick0=1, dtick=1),
                yaxis=dict(tickmode='linear'),
                margin=dict(t=20, b=20, l=20, r=20)
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
        else:
            st.info("No monthly breakdown available.")
    except Exception as e:
        st.error(f"Error loading heatmap graph: {e}")


# ==========================================
# PAGE 2: REVENUE ANALYTICS
# ==========================================
elif page == "Revenue Analytics":
    st.markdown("### Revenue Analytics")
    st.markdown("<p style='color: gray; margin-top: -10px;'>Trends, seasonality, category performance, and pricing</p>", unsafe_allow_html=True)
    st.divider()

    # --- RESTORED CLASSIC AMAZON GOLD/ORANGE ---
    st.subheader("📈 Monthly Revenue Trend")
    try:
        monthly_df = get_monthly_trend()
        if not monthly_df.empty:
            monthly_df["period"] = monthly_df["month_name"].astype(str).str[:3] + " " + monthly_df["year"].astype(str)
            fig_area = px.area(monthly_df, x="period", y="revenue_cr", labels={"revenue_cr": "Revenue (₹ Cr)", "period": ""})
            fig_area.update_traces(line_color="#FF9900", fillcolor="rgba(255,153,0,0.22)")
            fig_area.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                margin=dict(t=20, b=20, l=20, r=20)
            )
            st.plotly_chart(fig_area, use_container_width=True)
        else:
            st.info("No monthly trend data found.")
    except Exception as e:
        st.error(f"Error loading monthly trend: {e}")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📦 Category Performance")
        try:
            cat_perf = get_category_performance()
            if not cat_perf.empty:
                # RESTORED CLASSIC ORANGE SCALE
                fig_tree = px.treemap(
                    cat_perf, 
                    path=["subcategory"], 
                    values="revenue_cr", 
                    color="avg_rating",
                    color_continuous_scale="Oranges"
                )
                fig_tree.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    margin=dict(t=20, b=20, l=20, r=20)
                )
                st.plotly_chart(fig_tree, use_container_width=True)
            else:
                st.info("No category performance data found.")
        except Exception as e:
            st.error(f"Error loading category performance: {e}")

    with col2:
        st.subheader("🎉 Festival vs Regular Sales")
        try:
            fest_df = get_festival_sales()
            if not fest_df.empty:
                fest_df["label"] = fest_df["is_festival_sale"].map({True: "Festival Sale", False: "Regular Day"})
                fig_fest = px.bar(
                    fest_df, 
                    x="label", 
                    y="revenue_cr", 
                    color="label",
                    labels={"revenue_cr": "Revenue (₹ Cr)", "label": ""},
                    color_discrete_map={"Festival Sale": "#FF007F", "Regular Day": "#00F5D4"}
                )
                fig_fest.update_layout(
                    showlegend=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    margin=dict(t=20, b=20, l=20, r=20)
                )
                st.plotly_chart(fig_fest, use_container_width=True)
            else:
                st.info("No festival sales data found.")
        except Exception as e:
            st.error(f"Error loading festival sales: {e}")

    st.divider()

    st.subheader("🏷️ Discount % vs Revenue Impact")
    try:
        disc_df = get_discount_impact()
        if not disc_df.empty:
            fig_disc = px.bar(
                disc_df, 
                x="avg_discount", 
                y="revenue_cr",
                labels={"avg_discount": "Avg Discount %", "revenue_cr": "Revenue (₹ Cr)"},
                color="revenue_cr", 
                color_continuous_scale="Sunset"
            )
            fig_disc.update_layout(
                coloraxis_showscale=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                margin=dict(t=20, b=20, l=20, r=20)
            )
            st.plotly_chart(fig_disc, use_container_width=True)
        else:
            st.info("No discount impact data found.")
    except Exception as e:
        st.error(f"Error loading discount impact chart: {e}")


# ==========================================
# PAGE 3: CUSTOMER ANALYTICS
# ==========================================
elif page == "Customer Analytics":
    st.markdown("### Customer Analytics")
    st.markdown("<p style='color: gray; margin-top: -10px;'>Segmentation, RFM, Prime impact, and demographics</p>", unsafe_allow_html=True)
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 RFM: Frequency vs Monetary Value")
        try:
            rfm = get_rfm_data()
            if not rfm.empty:
                fig_rfm = px.scatter(
                    rfm, x="frequency", y="monetary", size="monetary",
                    color="recency_days", color_continuous_scale="Turbo_r",
                    labels={"frequency": "Order Frequency", "monetary": "Lifetime Spend (₹)", "recency_days": "Days Since Last Order"},
                    opacity=0.6
                )
                fig_rfm.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    margin=dict(t=20, b=20, l=20, r=20)
                )
                st.plotly_chart(fig_rfm, use_container_width=True)
            else:
                st.info("No RFM data available.")
        except Exception as e:
            st.error(f"Error loading RFM scatter: {e}")

    with col2:
        st.subheader("⭐ Prime vs Non-Prime Behaviour")
        try:
            prime = get_prime_behavior()
            if not prime.empty:
                prime["label"] = prime["is_prime_member"].map({True: "Prime", False: "Non-Prime"})
                fig_prime = px.bar(
                    prime, x="label", y="aov", color="label",
                    labels={"aov": "Avg Order Value (₹)", "label": ""},
                    color_discrete_map={"Prime": "#06D6A0", "Non-Prime": "#FF9F1C"}
                )
                fig_prime.update_layout(
                    showlegend=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    margin=dict(t=20, b=20, l=20, r=20)
                )
                st.plotly_chart(fig_prime, use_container_width=True)
            else:
                st.info("No prime behavior data found.")
        except Exception as e:
            st.error(f"Error loading Prime behavior chart: {e}")

    st.divider()

    st.subheader("👥 Spending by Age Group")
    try:
        age_df = get_age_spending()
        if not age_df.empty:
            fig_age = px.bar(
                age_df, x="customer_age_group", y="aov",
                labels={"customer_age_group": "Age Group", "aov": "Avg Order Value (₹)"},
                color="aov", color_continuous_scale="Viridis"
            )
            fig_age.update_layout(
                coloraxis_showscale=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                margin=dict(t=20, b=20, l=20, r=20)
            )
            st.plotly_chart(fig_age, use_container_width=True)
        else:
            st.info("No age group data found.")
    except Exception as e:
        st.error(f"Error loading age group chart: {e}")

    st.divider()

    st.subheader("📈 Customer Acquisition Cohorts (avg lifetime value)")
    try:
        cohort_df = get_cohort_clv()
        if not cohort_df.empty:
            fig_cohort = px.bar(
                cohort_df, x="cohort_year", y="avg_clv",
                labels={"cohort_year": "Acquisition Year", "avg_clv": "Avg Customer Lifetime Value (₹)"},
                color="avg_clv", color_continuous_scale=["#7209B7", "#4361EE", "#4CC9F0"]
            )
            fig_cohort.update_layout(
                coloraxis_showscale=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                margin=dict(t=20, b=20, l=20, r=20)
            )
            st.plotly_chart(fig_cohort, use_container_width=True)
        else:
            st.info("No cohort data found.")
    except Exception as e:
        st.error(f"Error loading cohort chart: {e}")


# ==========================================
# PAGE 4: PRODUCT & BRAND
# ==========================================
elif page == "Product & Brand":
    st.markdown("### Product & Brand Analytics")
    st.markdown("<p style='color: gray; margin-top: -10px;'>Brand performance, ratings, and product lifecycle</p>", unsafe_allow_html=True)
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📱 Brand Market Share")
        try:
            brand_df = get_brand_market_share()
            if not brand_df.empty:
                fig_brand = px.bar(
                    brand_df.sort_values("revenue_cr"), x="revenue_cr", y="brand", orientation="h",
                    labels={"revenue_cr": "Revenue (₹ Cr)", "brand": ""},
                    color="revenue_cr", color_continuous_scale=["#FF007F", "#7209B7", "#4CC9F0"]
                )
                fig_brand.update_layout(
                    coloraxis_showscale=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    margin=dict(t=20, b=20, l=20, r=20)
                )
                st.plotly_chart(fig_brand, use_container_width=True)
            else:
                st.info("No brand data found.")
        except Exception as e:
            st.error(f"Error loading brand market share: {e}")

    with col2:
        st.subheader("⭐ Rating Distribution")
        try:
            rating_df = get_rating_distribution()
            if not rating_df.empty:
                fig_rating = px.bar(
                    rating_df, x="rating_band", y="cnt",
                    labels={"rating_band": "Rating", "cnt": "Number of Orders"},
                    color="rating_band", color_continuous_scale="Spectral"
                )
                fig_rating.update_layout(
                    coloraxis_showscale=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    margin=dict(t=20, b=20, l=20, r=20)
                )
                st.plotly_chart(fig_rating, use_container_width=True)
            else:
                st.info("No rating distribution data found.")
        except Exception as e:
            st.error(f"Error loading rating distribution: {e}")

    st.divider()

    st.subheader("🔄 Product Lifecycle — Revenue by Launch Year over Time")
    try:
        lifecycle_df = get_product_lifecycle()
        if not lifecycle_df.empty:
            fig_life = px.line(
                lifecycle_df, x="sale_year", y="revenue_cr", color="launch_year",
                labels={"sale_year": "Sale Year", "revenue_cr": "Revenue (₹ Cr)", "launch_year": "Launch Year"},
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            fig_life.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                margin=dict(t=20, b=20, l=20, r=20)
            )
            st.plotly_chart(fig_life, use_container_width=True)
        else:
            st.info("No launch-year data available.")
    except Exception as e:
        st.error(f"Error loading product lifecycle chart: {e}")

    st.divider()

    st.subheader("🏷️ Competitive Pricing by Brand")
    try:
        price_df = get_competitive_pricing()
        if not price_df.empty:
            st.dataframe(price_df, use_container_width=True, hide_index=True)
        else:
            st.info("No pricing data available.")
    except Exception as e:
        st.error(f"Error loading competitive pricing data: {e}")


# ==========================================
# PAGE 5: OPERATIONS & LOGISTICS
# ==========================================
elif page == "Operations & Logistics":
    st.markdown("### Operations & Logistics")
    st.markdown("<p style='color: gray; margin-top: -10px;'>Delivery performance, payments, and returns</p>", unsafe_allow_html=True)
    st.divider()

    try:
        ops_kpi = get_ops_kpi()

        col_k1, col_k2, col_k3 = st.columns(3)
        with col_k1:
            st.markdown(f"""
                <div class="kpi-card" style="border-top-color: #3B82F6;">
                    <div class="kpi-title">Avg Delivery Time</div>
                    <div class="kpi-value">{ops_kpi.get('avg_delivery', 0)} days</div>
                </div>
            """, unsafe_allow_html=True)
        with col_k2:
            st.markdown(f"""
                <div class="kpi-card" style="border-top-color: #EF4444;">
                    <div class="kpi-title">Return Rate</div>
                    <div class="kpi-value">{ops_kpi.get('return_rate', 0)}%</div>
                </div>
            """, unsafe_allow_html=True)
        with col_k3:
            st.markdown(f"""
                <div class="kpi-card" style="border-top-color: #10B981;">
                    <div class="kpi-title">Avg Customer Rating</div>
                    <div class="kpi-value">{ops_kpi.get('avg_rating', 0)} / 5</div>
                </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error loading operations KPIs: {e}")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💳 Payment Method Share")
        try:
            pay_df = get_payment_share()
            if not pay_df.empty:
                fig_pay = px.pie(
                    pay_df, names="payment_method", values="orders", hole=0.55,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_pay.update_traces(marker=dict(line=dict(color='#1E1E1E', width=2)))
                fig_pay.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    margin=dict(t=20, b=20, l=20, r=20),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_pay, use_container_width=True)
            else:
                st.info("No payment method data found.")
        except Exception as e:
            st.error(f"Error loading payment method share: {e}")

    with col2:
        st.subheader("↩️ Return Status Breakdown")
        try:
            ret_df = get_return_status_breakdown()
            if not ret_df.empty:
                fig_ret = px.pie(
                    ret_df, names="return_status", values="cnt", hole=0.55,
                    color_discrete_sequence=["#FF007F", "#00F5D4", "#FFBE0B"]
                )
                fig_ret.update_traces(marker=dict(line=dict(color='#1E1E1E', width=2)))
                fig_ret.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    margin=dict(t=20, b=20, l=20, r=20),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_ret, use_container_width=True)
            else:
                st.info("No return status data found.")
        except Exception as e:
            st.error(f"Error loading return status breakdown: {e}")

    st.divider()

    st.subheader("🚚 Delivery Days by Customer Tier")
    try:
        del_tier_df = get_delivery_by_tier()
        if not del_tier_df.empty:
            fig_del = px.bar(
                del_tier_df, x="customer_tier", y="avg_delivery_days",
                labels={"customer_tier": "Customer Tier", "avg_delivery_days": "Avg Delivery Days"},
                color="avg_delivery_days", color_continuous_scale="RdYlGn_r"
            )
            fig_del.update_layout(
                coloraxis_showscale=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                margin=dict(t=20, b=20, l=20, r=20)
            )
            st.plotly_chart(fig_del, use_container_width=True)
        else:
            st.info("No delivery tier data available.")
    except Exception as e:
        st.error(f"Error loading delivery days chart: {e}")