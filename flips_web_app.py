
import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("Flip Deals Analyzer")

# Upload Listings and Comps CSVs
listings_file = st.file_uploader("Upload Listings CSV", type="csv", key="listings")
comps_file = st.file_uploader("Upload Comps CSV", type="csv", key="comps")

if listings_file is not None and comps_file is not None:
    listings_df = pd.read_csv(listings_file)
    comps_df = pd.read_csv(comps_file)

    # Ensure expected columns exist
    if "Zip" not in listings_df.columns or "Zip" not in comps_df.columns:
        st.error("Both files must contain a 'Zip' column.")
    else:
        # Filters
        zip_codes = sorted(listings_df["Zip"].dropna().unique())
        selected_zips = st.multiselect("Select ZIP codes", zip_codes, default=zip_codes)

        filtered_listings = listings_df[listings_df["Zip"].isin(selected_zips)]
        filtered_comps = comps_df[comps_df["Zip"].isin(selected_zips)]

        st.subheader("Filtered Listings")
        st.dataframe(filtered_listings)

        st.subheader("Filtered Comps")
        st.dataframe(filtered_comps)

else:
    st.warning("Please upload both listings and comps CSV files to begin.")
