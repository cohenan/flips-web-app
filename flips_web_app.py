import streamlit as st
import pandas as pd
from io import BytesIO

# ---- Streamlit App ----
st.set_page_config(page_title="Flip Analyzer", layout="wide")
st.title("Real Estate Flip Analyzer")

uploaded_listings = st.file_uploader("Upload Listings CSV", type="csv", key="listings")
uploaded_comps = st.file_uploader("Upload Sold Comps CSV", type="csv", key="comps")

if uploaded_listings and uploaded_comps:
    listings_df = pd.read_csv(uploaded_listings)
    comps_df = pd.read_csv(uploaded_comps)

    st.subheader("Uploaded Listings")
    st.dataframe(listings_df)

    st.subheader("Uploaded Comps")
    st.dataframe(comps_df)

    # --- Area Summary ---
    area_summary = listings_df.groupby("Zip")["List Price"].agg(["count", "mean", "min", "max"]).reset_index()
    area_summary.columns = ["Zip", "Count", "Avg Price", "Min Price", "Max Price"]
    st.subheader("Area Summary from Listings")
    st.dataframe(area_summary)

    # --- Export Example ---
    def to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        return output.getvalue()

    if st.button("Export Listings Summary to Excel"):
        excel_data = to_excel(area_summary)
        st.download_button(label="Download Excel File",
                           data=excel_data,
                           file_name='area_summary.xlsx',
                           mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

else:
    st.info("Please upload both a listings CSV and a comps CSV to begin analysis.")
