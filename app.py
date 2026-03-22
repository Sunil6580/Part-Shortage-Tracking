import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# =========================================================
# PAGE SETTINGS
# =========================================================
st.set_page_config(page_title="Company Ready Part Shortage Dashboard", layout="wide")

st.title("🚗 Company Ready Part Shortage Prediction Dashboard")
st.write("Upload your Excel or CSV file for shortage prediction, risk analysis, and urgent alerts.")

# =========================================================
# REQUIRED COLUMNS
# =========================================================
required_columns = [
    "Model_Number",
    "Model_Name",
    "Part_Number",
    "Part_Name",
    "Monthly_Schedule",
    "Assembly_Qty",
    "Current_Stock",
    "Incoming_Qty",
    "Lead_Time_Days",
    "Supplier_Reliability",
    "Criticality",
    "Safety_Stock"
]

# =========================================================
# SAMPLE FILE DOWNLOAD
# =========================================================
sample_df = pd.DataFrame({
    "Model_Number": [
        "822567/822421/820076",
        "822567",
        "820076",
        "822421/820076",
        "822567"
    ],
    "Model_Name": [
        "Model A/Model B/Model C",
        "Model A",
        "Model C",
        "Model B/Model C",
        "Model A"
    ],
    "Part_Number": ["P1001", "P1002", "P1003", "P1004", "P1005"],
    "Part_Name": ["Brake Pad", "Clutch Plate", "Oil Filter", "Air Filter", "Spark Plug"],
    "Monthly_Schedule": [3000, 2500, 1800, 2200, 1500],
    "Assembly_Qty": [2, 1, 1, 2, 4],
    "Current_Stock": [2500, 1800, 1200, 900, 500],
    "Incoming_Qty": [500, 300, 200, 100, 0],
    "Lead_Time_Days": [10, 18, 7, 14, 20],
    "Supplier_Reliability": [0.90, 0.75, 0.95, 0.85, 0.70],
    "Criticality": ["High", "Medium", "Low", "Medium", "High"],
    "Safety_Stock": [400, 300, 200, 250, 150]
})

sample_csv = sample_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="📥 Download Sample CSV File",
    data=sample_csv,
    file_name="company_ready_sample_part_shortage_data.csv",
    mime="text/csv"
)

# =========================================================
# FILE UPLOAD
# =========================================================
uploaded_file = st.file_uploader("📂 Upload Excel or CSV File", type=["xlsx", "xls", "csv"])

# =========================================================
# MAIN LOGIC
# =========================================================
if uploaded_file is not None:
    try:
        # ---------------------------------------------
        # READ FILE
        # ---------------------------------------------
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Clean column names
        df.columns = df.columns.str.strip()

        st.success("✅ File uploaded successfully!")
        st.write("Detected columns:", list(df.columns))

        # Check required columns
        missing_cols = [col for col in required_columns if col not in df.columns]

        if missing_cols:
            st.error(f"❌ Missing required columns: {missing_cols}")
            st.info("Please make sure your file has exact required column names.")
            st.stop()

        # Keep only required columns
        df = df[required_columns].copy()

        # ---------------------------------------------
        # CLEAN TEXT COLUMNS
        # ---------------------------------------------
        text_cols = ["Model_Number", "Model_Name", "Part_Number", "Part_Name", "Criticality"]
        for col in text_cols:
            df[col] = df[col].astype(str).str.strip()

        df["Criticality"] = df["Criticality"].str.title()

        # ---------------------------------------------
        # CONVERT NUMERIC COLUMNS
        # ---------------------------------------------
        numeric_cols = [
            "Monthly_Schedule",
            "Assembly_Qty",
            "Current_Stock",
            "Incoming_Qty",
            "Lead_Time_Days",
            "Supplier_Reliability",
            "Safety_Stock"
        ]

        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Check numeric errors
        if df[numeric_cols].isnull().any().any():
            st.error("❌ Some numeric columns have blank or invalid values.")
            st.write("Please check these columns:", numeric_cols)
            st.dataframe(df)
            st.stop()

        # ---------------------------------------------
        # VALIDATIONS
        # ---------------------------------------------
        if (df["Monthly_Schedule"] < 0).any():
            st.error("❌ Monthly_Schedule cannot be negative.")
            st.stop()

        if (df["Assembly_Qty"] <= 0).any():
            st.error("❌ Assembly_Qty must be greater than 0.")
            st.stop()

        if (df["Current_Stock"] < 0).any():
            st.error("❌ Current_Stock cannot be negative.")
            st.stop()

        if (df["Incoming_Qty"] < 0).any():
            st.error("❌ Incoming_Qty cannot be negative.")
            st.stop()

        if (df["Lead_Time_Days"] <= 0).any():
            st.error("❌ Lead_Time_Days must be greater than 0.")
            st.stop()

        if (df["Safety_Stock"] < 0).any():
            st.error("❌ Safety_Stock cannot be negative.")
            st.stop()

        if ((df["Supplier_Reliability"] < 0) | (df["Supplier_Reliability"] > 1)).any():
            st.error("❌ Supplier_Reliability must be between 0 and 1.")
            st.stop()

        # ---------------------------------------------
        # SPLIT MODEL NUMBERS COUNT
        # Example: 822567/822421/820076 -> 3 models
        # ---------------------------------------------
        df["Model_Count"] = df["Model_Number"].apply(
            lambda x: len([m.strip() for m in str(x).split("/") if m.strip() != ""])
        )

        # ---------------------------------------------
        # CALCULATIONS
        # ---------------------------------------------
        # Total required quantity for month
        df["Monthly_Requirement"] = df["Monthly_Schedule"] * df["Assembly_Qty"]

        # Daily usage (assuming 30 days month)
        df["Daily_Usage"] = df["Monthly_Requirement"] / 30

        # Net available stock
        df["Net_Available_Stock"] = df["Current_Stock"] + df["Incoming_Qty"]

        # Usable stock after safety stock
        df["Usable_Stock"] = df["Net_Available_Stock"] - df["Safety_Stock"]
        df["Usable_Stock"] = df["Usable_Stock"].apply(lambda x: max(x, 0))

        # Days cover
        df["Days_Cover"] = df["Usable_Stock"] / df["Daily_Usage"]

        # Lead time demand
        df["Lead_Time_Demand"] = df["Daily_Usage"] * df["Lead_Time_Days"]

        # Shortage quantity during lead time
        df["Shortage_Qty"] = df["Lead_Time_Demand"] - df["Usable_Stock"]
        df["Shortage_Qty"] = df["Shortage_Qty"].apply(lambda x: max(x, 0))

        # Shortage alert
        df["Shortage_Alert"] = np.where(df["Shortage_Qty"] > 0, "YES", "NO")

        # Criticality mapping
        criticality_map = {"High": 1.0, "Medium": 0.6, "Low": 0.3}
        df["Criticality_Score"] = df["Criticality"].map(criticality_map)

        if df["Criticality_Score"].isnull().any():
            st.error("❌ Invalid values in Criticality column.")
            st.info("Allowed values are only: High, Medium, Low")
            st.stop()

        # Avoid division error
        df["Days_Cover_Adjusted"] = df["Days_Cover"].replace(0, 0.01)

        # Risk score
        df["Shortage_Risk_Score"] = (
            (df["Lead_Time_Days"] / df["Days_Cover_Adjusted"]) * 0.45 +
            (1 - df["Supplier_Reliability"]) * 0.25 +
            df["Criticality_Score"] * 0.20 +
            (df["Model_Count"] / 5) * 0.10 # more models = more dependency risk
        )

        # Risk classification
        def classify_risk(score):
            if score >= 1.5:
                return "High Risk"
            elif score >= 0.9:
                return "Medium Risk"
            else:
                return "Low Risk"

        df["Risk_Level"] = df["Shortage_Risk_Score"].apply(classify_risk)

        # Urgency ranking
        df["Urgency_Score"] = (
            df["Shortage_Qty"] * 0.5 +
            (np.where(df["Risk_Level"] == "High Risk", 3,
             np.where(df["Risk_Level"] == "Medium Risk", 2, 1))) * 100
        )

        # Round values
        round_cols = [
            "Monthly_Requirement", "Daily_Usage", "Net_Available_Stock", "Usable_Stock",
            "Days_Cover", "Lead_Time_Demand", "Shortage_Qty", "Shortage_Risk_Score"
        ]
        for col in round_cols:
            df[col] = df[col].round(2)

        # Sort by urgency
        df = df.sort_values(by=["Shortage_Alert", "Shortage_Risk_Score", "Shortage_Qty"], ascending=[False, False, False])

        # =========================================================
        # SIDEBAR FILTERS
        # =========================================================
        st.sidebar.header("🔎 Filters")

        risk_filter = st.sidebar.multiselect(
            "Select Risk Level",
            options=df["Risk_Level"].unique(),
            default=df["Risk_Level"].unique()
        )

        alert_filter = st.sidebar.multiselect(
            "Select Shortage Alert",
            options=df["Shortage_Alert"].unique(),
            default=df["Shortage_Alert"].unique()
        )

        criticality_filter = st.sidebar.multiselect(
            "Select Criticality",
            options=df["Criticality"].unique(),
            default=df["Criticality"].unique()
        )

        search_part = st.sidebar.text_input("Search Part Number or Part Name")

        filtered_df = df[
            (df["Risk_Level"].isin(risk_filter)) &
            (df["Shortage_Alert"].isin(alert_filter)) &
            (df["Criticality"].isin(criticality_filter))
        ].copy()

        if search_part:
            filtered_df = filtered_df[
                filtered_df["Part_Number"].str.contains(search_part, case=False, na=False) |
                filtered_df["Part_Name"].str.contains(search_part, case=False, na=False)
            ]

        # =========================================================
        # SUMMARY
        # =========================================================
        st.subheader("📊 Summary")

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Parts", len(filtered_df))
        col2.metric("High Risk Parts", (filtered_df["Risk_Level"] == "High Risk").sum())
        col3.metric("Shortage Alerts", (filtered_df["Shortage_Alert"] == "YES").sum())
        col4.metric("Total Shortage Qty", int(filtered_df["Shortage_Qty"].sum()))
        col5.metric("Average Days Cover", round(filtered_df["Days_Cover"].mean(), 2) if len(filtered_df) > 0 else 0)

        # =========================================================
        # RESULTS TABLE
        # =========================================================
        st.subheader("📋 Full Results Table")
        st.dataframe(filtered_df, use_container_width=True)

        # =========================================================
        # TOP 20 URGENT PARTS
        # =========================================================
        st.subheader("🚨 Top 20 Most Urgent Parts")
        top_urgent = filtered_df.sort_values(by=["Shortage_Qty", "Shortage_Risk_Score"], ascending=[False, False]).head(20)
        st.dataframe(top_urgent, use_container_width=True)

        # =========================================================
        # HIGH RISK / ALERT PARTS
        # =========================================================
        st.subheader("⚠️ High Risk or Shortage Alert Parts")
        alert_df = filtered_df[
            (filtered_df["Risk_Level"] == "High Risk") |
            (filtered_df["Shortage_Alert"] == "YES")
        ]

        if not alert_df.empty:
            st.dataframe(alert_df, use_container_width=True)
        else:
            st.success("✅ No high risk or shortage alert parts found.")

        # =========================================================
        # CHARTS
        # =========================================================
        st.subheader("📈 Charts")

        # Risk distribution
        risk_count = filtered_df["Risk_Level"].value_counts().reset_index()
        risk_count.columns = ["Risk_Level", "Count"]

        fig1 = px.bar(
            risk_count,
            x="Risk_Level",
            y="Count",
            title="Risk Level Distribution"
        )
        st.plotly_chart(fig1, use_container_width=True)

        # Top 20 shortage qty
        top_shortage = filtered_df.sort_values(by="Shortage_Qty", ascending=False).head(20)

        fig2 = px.bar(
            top_shortage,
            x="Part_Number",
            y="Shortage_Qty",
            color="Risk_Level",
            hover_data=["Part_Name", "Model_Number"],
            title="Top 20 Parts by Shortage Quantity"
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Top 20 lowest days cover
        top_low_cover = filtered_df.sort_values(by="Days_Cover", ascending=True).head(20)

        fig3 = px.bar(
            top_low_cover,
            x="Part_Number",
            y="Days_Cover",
            color="Risk_Level",
            hover_data=["Part_Name", "Model_Number"],
            title="Top 20 Lowest Days Cover Parts"
        )
        st.plotly_chart(fig3, use_container_width=True)

        # =========================================================
        # DOWNLOAD BUTTONS
        # =========================================================
        full_result_csv = filtered_df.to_csv(index=False).encode("utf-8")
        alert_result_csv = alert_df.to_csv(index=False).encode("utf-8")
        urgent_result_csv = top_urgent.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="📥 Download Full Results CSV",
            data=full_result_csv,
            file_name="company_ready_full_results.csv",
            mime="text/csv"
        )

        st.download_button(
            label="📥 Download Alert Parts CSV",
            data=alert_result_csv,
            file_name="company_ready_alert_parts.csv",
            mime="text/csv"
        )

        st.download_button(
            label="📥 Download Top 20 Urgent Parts CSV",
            data=urgent_result_csv,
            file_name="company_ready_top20_urgent_parts.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")

else:
    st.info("⬆️ Please upload your Excel or CSV file.")