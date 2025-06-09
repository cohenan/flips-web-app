
import streamlit as st
import pandas as pd

st.title("Flip Analysis App")

# Upload Listings and Comps
listings_file = st.file_uploader("Upload Listings CSV", type="csv", key="listings")
comps_file = st.file_uploader("Upload Comps CSV", type="csv", key="comps")

if listings_file is not None and comps_file is not None:
    listings_df = pd.read_csv(listings_file)
    comps_df = pd.read_csv(comps_file)

    zip_codes = sorted(listings_df["Zip"].dropna().unique())
    # Continue with the rest of your UI/widgets...
else:
    st.warning("Please upload both listings and comps CSV files to continue.")

    # --- Sidebar Filters ---
    st.sidebar.header("Filters")

    zip_codes = sorted(listings_df["Zip"].dropna().unique())
    selected_zips = st.sidebar.multiselect("Filter by ZIP", zip_codes, default=zip_codes)

    bedrooms = sorted(listings_df["Bedrooms"].dropna().unique())
    selected_bedrooms = st.sidebar.multiselect("Filter by Bedrooms", bedrooms, default=bedrooms)

    counties = sorted(listings_df["County"].dropna().unique())
    selected_counties = st.sidebar.multiselect("Filter by County", counties, default=counties)

    cities = sorted(listings_df["City"].dropna().unique())
    selected_cities = st.sidebar.multiselect("Filter by City", cities, default=cities)

    subs = sorted(listings_df["Sub"].dropna().unique())
    selected_subs = st.sidebar.multiselect("Filter by Subdivision", subs, default=subs)

    # --- Apply Filters ---
    filtered = listings_df[
        listings_df["Zip"].isin(selected_zips) &
        listings_df["Bedrooms"].isin(selected_bedrooms) &
        listings_df["County"].isin(selected_counties) &
        listings_df["City"].isin(selected_cities) &
        listings_df["Sub"].isin(selected_subs)
    ].copy()

    # --- Match Comps ---
    def match_comps(listing, comps_df, bed_tolerance=1, area_tolerance=0.10):
        matches = comps_df[
            (comps_df["Zip"] == listing["Zip"]) &
            (comps_df["Bedrooms"].between(listing["Bedrooms"] - bed_tolerance,
                                          listing["Bedrooms"] + bed_tolerance)) &
            (comps_df["Living Area"].between(listing["Living Area"] * (1 - area_tolerance),
                                             listing["Living Area"] * (1 + area_tolerance)))
        ]
        return matches

    result_rows = []
    comp_dict = {}

    for i, row in filtered.iterrows():
        comps = match_comps(row, comps_df)
        if not comps.empty:
            est_price = comps["Sold Price"].mean()
            result_row = row.to_dict()
            result_row["Est Comp Price"] = round(est_price, 2)
            result_row["Profit"] = round(est_price - row["List Price"], 2)
            result_rows.append(result_row)
            comp_dict[row["MLS"]] = comps

    result_df = pd.DataFrame(result_rows)

    st.subheader("Flip Candidates")
    selected = st.multiselect("Select Rows by MLS to Export Comps", result_df["MLS"].tolist())
    st.dataframe(result_df)

    # --- Export Selected Flip + Comps to Excel ---
    def export_excel(selected_df, comp_dict):
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            selected_df.to_excel(writer, index=False, sheet_name="Selected Flips")
            for mls in selected_df["MLS"]:
                if mls in comp_dict:
                    comp_dict[mls].to_excel(writer, index=False, sheet_name=f"Comps_{mls}")
        return buffer.getvalue()

    if selected:
        selected_df = result_df[result_df["MLS"].isin(selected)]
        excel_data = export_excel(selected_df, comp_dict)
        st.download_button("Download Selected Flips + Comps", excel_data,
                           file_name="selected_flips_comps.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("Please upload both listings and comps CSV files to begin.")
