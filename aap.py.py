from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from matplotlib.lines import Line2D


@st.cache_data
def load_data():
    csv_path = Path(__file__).resolve().parent / "Nassau Candy Distributor (1).csv"
    df = pd.read_csv(csv_path)

    df["Order Date"] = pd.to_datetime(df["Order Date"], dayfirst=True, errors="coerce")
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], dayfirst=True, errors="coerce")
    df["Sales"] = pd.to_numeric(df["Sales"], errors="coerce")
    df["Cost"] = pd.to_numeric(df["Cost"], errors="coerce")
    df["Units"] = pd.to_numeric(df["Units"], errors="coerce")
    df["Gross Profit"] = pd.to_numeric(df["Gross Profit"], errors="coerce")

    df = df.dropna(subset=["Sales", "Cost", "Units", "Gross Profit"])
    df = df[df["Sales"] > 0].copy()

    df["Gross Margin %"] = (df["Gross Profit"] / df["Sales"]) * 100
    df["Profit per Unit"] = df["Gross Profit"] / df["Units"]
    return df


def build_dashboard(df):
    st.title("Product Line Profitability & Margin Performance Analysis")
    st.caption("Nassau Candy Distributor")

    min_date = df["Order Date"].min().date()
    max_date = df["Order Date"].max().date()
    date_col1, date_col2 = st.columns(2)
    start_date = date_col1.date_input(
        "Start date",
        value=min_date,
        min_value=min_date,
        max_value=max_date,
        key="start_date",
    )
    end_date = date_col2.date_input(
        "End date",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
        key="end_date",
    )

    if start_date > end_date:
        st.error("Start date must be on or before the end date.")
        return

    filtered = df[
        (df["Order Date"].dt.date >= start_date)
        & (df["Order Date"].dt.date <= end_date)
    ].copy()
    st.caption(
        f"Showing {len(filtered):,} orders from {start_date:%d %b %Y} "
        f"to {end_date:%d %b %Y}."
    )

    division = st.selectbox("Division", ["All"] + sorted(filtered["Division"].dropna().unique().tolist()))
    if division != "All":
        filtered = filtered[filtered["Division"] == division]

    product_search = st.text_input("Search product")
    if product_search:
        filtered = filtered[filtered["Product Name"].str.contains(product_search, case=False, na=False)]

    if filtered.empty:
        st.warning("No data available for the selected filters.")
        return

    total_sales = filtered["Sales"].sum()
    total_profit = filtered["Gross Profit"].sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Sales", f"${total_sales:,.2f}")
    col2.metric("Total Gross Profit", f"${total_profit:,.2f}")
    col3.metric("Avg Gross Margin", f"{(total_profit / total_sales * 100):.2f}%")
    col4.metric("Avg Profit per Unit", f"${(total_profit / filtered['Units'].sum()):,.2f}")

    st.subheader("Product Profitability Leaderboard")
    product_summary = (
        filtered.groupby("Product Name", as_index=False)
        .agg(
            Sales=("Sales", "sum"),
            Gross_Profit=("Gross Profit", "sum"),
            Units=("Units", "sum"),
        )
    )
    product_summary["Gross_Margin"] = product_summary["Gross_Profit"] / product_summary["Sales"] * 100
    product_summary["Profit_Per_Unit"] = product_summary["Gross_Profit"] / product_summary["Units"]
    product_summary = product_summary.sort_values("Gross_Profit", ascending=False).head(10)
    st.dataframe(product_summary, use_container_width=True)

    st.subheader("Division Performance")
    division_perf = (
        filtered.groupby("Division", as_index=False)
        .agg(
            Sales=("Sales", "sum"),
            Gross_Profit=("Gross Profit", "sum"),
        )
    )
    division_perf["Gross_Margin"] = (
        division_perf["Gross_Profit"] / division_perf["Sales"] * 100
    )
    division_perf = division_perf.sort_values("Sales", ascending=True)
    division_chart, division_ax = plt.subplots(figsize=(8, 4.5))
    y_positions = range(len(division_perf))
    division_ax.barh(
        [y - 0.18 for y in y_positions],
        division_perf["Sales"],
        height=0.34,
        label="Sales",
        color="#4C78A8",
    )
    division_ax.barh(
        [y + 0.18 for y in y_positions],
        division_perf["Gross_Profit"],
        height=0.34,
        label="Gross profit",
        color="#59A14F",
    )
    division_ax.set_yticks(list(y_positions))
    division_ax.set_yticklabels(division_perf["Division"])
    division_ax.set_xlabel("Amount ($)")
    division_ax.set_title("Sales and Gross Profit by Division")
    max_sales = division_perf["Sales"].max()
    division_ax.set_xlim(0, max_sales * 1.35)
    division_ax.legend()
    division_ax.grid(axis="x", alpha=0.25)
    for y, margin in zip(y_positions, division_perf["Gross_Margin"]):
        division_ax.text(
            max_sales * 1.02,
            y,
            f"{margin:.1f}% profit margin",
            va="center",
            fontsize=9,
        )
    division_chart.tight_layout()
    st.pyplot(division_chart)
    pie_fig, pie_ax = plt.subplots(figsize=(6, 4.5))
    pie_ax.pie(
        division_perf["Sales"],
        labels=division_perf["Division"],
        autopct="%1.1f%%",
        startangle=90,
        colors=["#4C78A8", "#F58518", "#59A14F"],
        wedgeprops={"edgecolor": "white", "linewidth": 1},
    )
    pie_ax.set_title("Share of Total Sales by Division")
    st.pyplot(pie_fig)
    top_sales_division = division_perf.iloc[-1]
    top_margin_division = division_perf.loc[division_perf["Gross_Margin"].idxmax()]
    st.caption(
        f"How to read this: blue bars show money earned from sales; green bars show "
        f"money kept as gross profit. {top_sales_division['Division']} has the highest "
        f"sales, while {top_margin_division['Division']} has the strongest margin "
        f"({top_margin_division['Gross_Margin']:.1f}%)."
    )
    division_display = division_perf.sort_values("Gross_Profit", ascending=False).copy()
    division_display.columns = ["Division", "Sales ($)", "Gross Profit ($)", "Profit Margin (%)"]
    st.dataframe(division_display, use_container_width=True, hide_index=True)

    st.subheader("Monthly Sales and Gross Profit Trend")
    monthly_perf = (
        filtered.assign(Month=filtered["Order Date"].dt.to_period("M").dt.to_timestamp())
        .groupby("Month", as_index=False)
        .agg(
            Sales=("Sales", "sum"),
            Gross_Profit=("Gross Profit", "sum"),
        )
    )
    trend_fig, trend_ax = plt.subplots(figsize=(8, 4.5))
    trend_ax.plot(
        monthly_perf["Month"],
        monthly_perf["Sales"],
        marker="o",
        linewidth=2,
        label="Sales",
        color="#4C78A8",
    )
    trend_ax.plot(
        monthly_perf["Month"],
        monthly_perf["Gross_Profit"],
        marker="o",
        linewidth=2,
        label="Gross profit",
        color="#59A14F",
    )
    trend_ax.set_xlabel("Month")
    trend_ax.set_ylabel("Amount ($)")
    trend_ax.set_title("Monthly Sales and Gross Profit Trend")
    trend_ax.legend()
    trend_ax.grid(True, alpha=0.25)
    trend_fig.autofmt_xdate()
    trend_fig.tight_layout()
    st.pyplot(trend_fig)
    st.caption(
        "How to read this: the blue line shows monthly sales and the green line shows "
        "monthly gross profit. A widening gap means costs are taking a larger share of sales."
    )

    st.subheader("Cost vs Margin Diagnostics")
    item_cost_margin = (
        filtered.groupby("Product Name", as_index=False)
        .agg(
            Cost=("Cost", "mean"),
            Sales=("Sales", "sum"),
            Gross_Profit=("Gross Profit", "sum"),
            Units=("Units", "sum"),
        )
    )
    item_cost_margin["Gross Margin %"] = (
        item_cost_margin["Gross_Profit"] / item_cost_margin["Sales"] * 100
    )
    median_cost = item_cost_margin["Cost"].median()
    median_margin = item_cost_margin["Gross Margin %"].median()
    item_cost_margin["Segment"] = item_cost_margin.apply(
        lambda item: (
            "High margin / low cost"
            if item["Cost"] <= median_cost and item["Gross Margin %"] >= median_margin
            else "High margin / high cost"
            if item["Cost"] > median_cost and item["Gross Margin %"] >= median_margin
            else "Low margin / low cost"
            if item["Cost"] <= median_cost
            else "Low margin / high cost"
        ),
        axis=1,
    )
    colors = {
        "High margin / low cost": "#2ca02c",
        "High margin / high cost": "#1f77b4",
        "Low margin / low cost": "#ff7f0e",
        "Low margin / high cost": "#d62728",
    }
    margin_view = item_cost_margin.sort_values("Gross Margin %")
    margin_colors = [
        "#59A14F" if margin >= median_margin else "#E15759"
        for margin in margin_view["Gross Margin %"]
    ]
    margin_fig, margin_ax = plt.subplots(figsize=(8, 5))
    margin_ax.barh(
        margin_view["Product Name"],
        margin_view["Gross Margin %"],
        color=margin_colors,
    )
    for y_position, margin in enumerate(margin_view["Gross Margin %"]):
        margin_ax.text(
            margin + 0.8,
            y_position,
            f"{margin:.1f}%",
            va="center",
            fontsize=8,
        )
    margin_ax.axvline(
        median_margin,
        color="gray",
        linestyle="--",
        linewidth=1,
        label=f"Average: {median_margin:.1f}%",
    )
    margin_ax.set_xlabel("Gross Margin (%)")
    margin_ax.set_title("Which Products Keep the Most Money?")
    margin_ax.grid(axis="x", alpha=0.25)
    margin_ax.legend(
        handles=[
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="#59A14F",
                markersize=9,
                label="Above-average margin",
            ),
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="#E15759",
                markersize=9,
                label="Below-average margin",
            ),
            Line2D(
                [0],
                [0],
                color="gray",
                linestyle="--",
                label=f"Average: {median_margin:.1f}%",
            ),
        ],
        loc="lower right",
    )
    margin_fig.tight_layout()
    st.pyplot(margin_fig)
    st.caption(
        "Gross margin = (Sales - Cost) / Sales. In simple terms, it is the percentage "
        "of each sales dollar left after product cost. Green products are above average; "
        "red products are below average. The dashed line marks the average product margin."
    )
    highest_margin = margin_view.iloc[-1]
    lowest_margin = margin_view.iloc[0]
    st.info(
        f"**Business takeaway:** {highest_margin['Product Name']} has the strongest margin "
        f"({highest_margin['Gross Margin %']:.1f}%). {lowest_margin['Product Name']} has "
        f"the weakest margin ({lowest_margin['Gross Margin %']:.1f}%) and should be "
        "reviewed for price or cost improvement."
    )
    correlation = item_cost_margin["Cost"].corr(item_cost_margin["Gross Margin %"])
    st.write(
        f"**Analysis:** Cost and margin have a {correlation:+.2f} correlation across products. "
        "Prioritize high-sales products in the low-margin quadrants for pricing or cost review."
    )
    st.dataframe(
        item_cost_margin[
            ["Product Name", "Segment", "Cost", "Gross Margin %", "Sales", "Gross_Profit", "Units"]
        ].sort_values("Gross_Profit", ascending=False),
        use_container_width=True,
    )

    st.subheader("Pareto Analysis")
    pareto = (
        filtered.groupby("Product Name", as_index=False)["Gross Profit"]
        .sum()
        .sort_values("Gross Profit", ascending=False)
    )
    pareto["Profit Share %"] = pareto["Gross Profit"] / pareto["Gross Profit"].sum() * 100
    pareto["Cumulative Profit %"] = pareto["Profit Share %"].cumsum()
    pareto_fig, pareto_ax = plt.subplots(figsize=(8, 5))
    bar_colors = [
        "#4C78A8" if value >= pareto["Profit Share %"].median() else "#9ECAE1"
        for value in pareto["Profit Share %"]
    ]
    pareto_ax.bar(
        pareto["Product Name"],
        pareto["Gross Profit"],
        color=bar_colors,
    )
    pareto_ax.set_ylabel("Gross Profit ($)")
    pareto_ax.set_title("Gross Profit Contribution by Product")
    pareto_ax.tick_params(axis="x", rotation=60, labelsize=8)
    pareto_ax.grid(axis="y", alpha=0.25)
    pareto_fig.tight_layout()
    st.pyplot(pareto_fig)
    top_three_share = pareto.head(3)["Profit Share %"].sum()
    st.caption(
        f"Products are ranked from highest to lowest gross profit. The top three products "
        f"generate {top_three_share:.1f}% of total gross profit."
    )
    pareto_display = pareto.copy()
    pareto_display.columns = [
        "Product",
        "Gross Profit ($)",
        "Profit Share (%)",
        "Cumulative Profit (%)",
    ]
    st.dataframe(pareto_display, use_container_width=True, hide_index=True)

    st.subheader("Key Insights")
    top_product = product_summary.iloc[0]
    worst_margin = product_summary.sort_values("Gross_Margin").iloc[0]
    st.write(f"- Top profit product: {top_product['Product Name']} with ${top_product['Gross_Profit']:,.2f} gross profit.")
    st.write(f"- Lowest margin product: {worst_margin['Product Name']} with {worst_margin['Gross_Margin']:.2f}% gross margin.")
    st.write(f"- Revenue from selected data: ${total_sales:,.2f}.")
    st.write(f"- Profit from selected data: ${total_profit:,.2f}.")


if __name__ == "__main__":
    df = load_data()
    build_dashboard(df)