import streamlit as st
import pandas as pd
import urllib.parse
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Flip Analyzer", layout="wide")
st.markdown("<h1 style='text-align: center; color: teal;'>🏠 Real Estate Flip Analyzer</h1>", unsafe_allow_html=True)

sort_options = ["ALL", "Area", "County", "City", "Sub"]

def zillow_search_url(address):
    if pd.isna(address):
        return ""
    address_url = urllib.parse.quote(str(address).replace(" ", "-"))
    return f"https://www.zillow.com/homes/{address_url}_rb/"

col1, col2 = st.columns(2)
with col1:
    listings_file = st.file_uploader("Upload Listings CSV", type="csv", key="listings")
with col2:
    comps_file = st.file_uploader("Upload Comps CSV", type="csv", key="comps")

df_listings = None
if listings_file:
    df_listings = pd.read_csv(listings_file)
    st.success(f"✅ Listings file uploaded successfully! Rows: {df_listings.shape[0]} | Columns: {df_listings.shape[1]}")

df_comps = None
if comps_file:
    try:
        df_comps = pd.read_csv(comps_file)
        st.success(f"✅ Comps file uploaded successfully! Rows: {df_comps.shape[0]} | Columns: {df_comps.shape[1]}")
    except pd.errors.EmptyDataError:
        df_comps = None
        st.error("❌ Comps file appears to be empty or invalid. Please upload a valid CSV.")

sort_selection = st.selectbox("Sort listings by:", sort_options)
sub_filter = None

if 'run_clicked' not in st.session_state:
    st.session_state['run_clicked'] = False
if 'area_run_clicked' not in st.session_state:
    st.session_state['area_run_clicked'] = False
if 'focus_flips_selected' not in st.session_state:
    st.session_state['focus_flips_selected'] = False
if 'show_all_candidates' not in st.session_state:
    st.session_state['show_all_candidates'] = False

if st.button("▶️ Run Analysis"):
    st.session_state['run_clicked'] = True
    st.session_state['show_all_candidates'] = False

if listings_file and comps_file and df_comps is not None and st.session_state['run_clicked']:
    listings_status_col = [col for col in df_listings.columns if 'status' in col.lower()]
    comps_status_col = [col for col in df_comps.columns if 'status' in col.lower()]
    if not listings_status_col or not comps_status_col:
        st.error("❌ Couldn't find a status column in one of the files.")
        st.stop()
    listings_status_col = listings_status_col[0]
    comps_status_col = comps_status_col[0]
    df_listings[listings_status_col] = df_listings[listings_status_col].astype(str).str.strip().str.lower()
    df_comps[comps_status_col] = df_comps[comps_status_col].astype(str).str.strip().str.lower()
    df_active = df_listings[df_listings[listings_status_col] == 'active']
    df_sold = df_comps[df_comps[comps_status_col] == 'sold']

    # ===================== "ALL" SORT =====================
    if sort_selection == "ALL":
        summary = pd.DataFrame([{
            'Listings_Count': df_active.shape[0],
            'Sold_Count': df_sold.shape[0],
            'Avg_List_Price': df_active['List Price'].mean(),
            'Avg_Sold_Price': df_sold['Sale Price'].mean(),
        }])
        summary['Sold - List ($)'] = summary['Avg_Sold_Price'] - summary['Avg_List_Price']
        summary['Sold - List (%)'] = ((summary['Avg_Sold_Price'] - summary['Avg_List_Price']) / summary['Avg_List_Price'].replace(0, pd.NA)) * 100
        styled_summary = summary.copy()
        styled_summary['Avg_List_Price'] = styled_summary['Avg_List_Price'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "")
        styled_summary['Avg_Sold_Price'] = styled_summary['Avg_Sold_Price'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "")
        styled_summary['Sold - List ($)'] = styled_summary['Sold - List ($)'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "")
        styled_summary['Sold - List (%)'] = styled_summary['Sold - List (%)'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        st.subheader("Summary by ALL")
        st.dataframe(styled_summary, use_container_width=True)

        st.markdown("### Comps Matching Criteria")
        same_zip = st.checkbox("Same ZIP", value=True, key="all_zip")
        same_county = st.checkbox("Same County", key="all_county")
        same_city = st.checkbox("Same City", key="all_city")
        same_sub = st.checkbox("Same Sub", key="all_sub")
        same_beds = st.checkbox("Same # Bedrooms", value=True, key="all_beds")
        sf_range = st.slider("± SF Range (%):", min_value=5, max_value=50, value=15, step=5, key="all_sf")

        if st.button("▶️ Show All Flip Candidates"):
            st.session_state['show_all_candidates'] = True

        if st.session_state.get('show_all_candidates', False):
            if not df_active.empty:
                all_rows = []
                all_flips_dict = {}  # Store active row & comps by MLS #
                for _, row in df_active.iterrows():
                    listing_sf = row['Total Finished SF']
                    sf_min = listing_sf * (1 - sf_range / 100)
                    sf_max = listing_sf * (1 + sf_range / 100)
                    comps_filtered = df_sold.copy()
                    if same_zip:
                        comps_filtered = comps_filtered[comps_filtered['Zip'].astype(str).str.strip() == str(row['Zip']).strip()]
                    if same_county:
                        comps_filtered = comps_filtered[comps_filtered['County'].astype(str).str.strip().str.lower() == str(row['County']).strip().lower()]
                    if same_city:
                        comps_filtered = comps_filtered[comps_filtered['City'].astype(str).str.strip().str.lower() == str(row['City']).strip().lower()]
                    if same_sub:
                        comps_filtered = comps_filtered[comps_filtered['Sub'].astype(str).str.strip().str.lower() == str(row['Sub']).strip().lower()]
                    if same_beds:
                        comps_filtered = comps_filtered[comps_filtered['Bedrooms'] == row['Bedrooms']]
                    comps_filtered = comps_filtered[
                        (comps_filtered['Total Finished SF'] >= sf_min) &
                        (comps_filtered['Total Finished SF'] <= sf_max)
                    ]
                    avg_comp_price = comps_filtered['Sale Price'].mean() if not comps_filtered.empty else None
                    num_comps = len(comps_filtered)
                    price_diff = (avg_comp_price - row['List Price']) if avg_comp_price else None
                    price_diff_pct = ((avg_comp_price - row['List Price']) / row['List Price'] * 100) if avg_comp_price else None
                    all_rows.append({
                        'Rank': 0,
                        'MLS #': str(row['MLS #']),
                        'Address': row['Address'],
                        'Bedrooms': row['Bedrooms'],
                        'Total Finished SF': row['Total Finished SF'],
                        'List Price': row['List Price'],
                        'Avg Comp Price': avg_comp_price,
                        'Price Diff ($)': price_diff,
                        'Price Diff (%)': price_diff_pct,
                        '# of Comps': num_comps
                    })
                    all_flips_dict[str(row['MLS #'])] = {
                        'active': row,
                        'comps': comps_filtered.copy()
                    }
                all_flips_table = pd.DataFrame(all_rows)
                all_flips_table.sort_values(by='Price Diff (%)', ascending=False, inplace=True)
                all_flips_table['Rank'] = range(1, len(all_flips_table) + 1)
                all_flips_table['List Price'] = all_flips_table['List Price'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "")
                all_flips_table['Avg Comp Price'] = all_flips_table['Avg Comp Price'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "")
                all_flips_table['Price Diff ($)'] = all_flips_table['Price Diff ($)'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "")
                all_flips_table['Price Diff (%)'] = all_flips_table['Price Diff (%)'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
                st.dataframe(all_flips_table, use_container_width=True)

                mls_plain_list = [row['MLS #'] for row in all_rows]
                selected_mls = st.multiselect("Select MLS #(s) to focus on:", mls_plain_list)
                if selected_mls:
                    st.write(f"You selected to focus on MLS #: {', '.join(map(str, selected_mls))}")
                    for mls in selected_mls:
                        active_row = all_flips_dict[str(mls)]['active']
                        comps = all_flips_dict[str(mls)]['comps']
                        st.markdown("---")
                        st.markdown(
                            f"📌 Flip Details: MLS {mls} "
                            f"<a href='{zillow_search_url(active_row['Address'])}' target='_blank' "
                            f"style='text-decoration:none;'>"
                            f"<button style='background:#0074e4;border:none;color:white;border-radius:3px;padding:1px 6px;font-size:85%;margin-left:3px;'>Zillow Search</button></a>",
                            unsafe_allow_html=True
                        )
                        active_cols = ['MLS #', 'Status', 'Area', 'Address', 'County', 'City', 'Zip', 'Sub', 'Bedrooms', 'Full Baths', 'Total Finished SF', 'List Price', 'List Dt']
                        active_display = pd.DataFrame([active_row[active_cols]])
                        st.dataframe(active_display, use_container_width=True)
                        st.markdown("**Matching Comps:**")
                        comps_cols = ['MLS #', 'Status', 'Area', 'Address', 'County', 'City', 'Zip', 'Sub', 'Bedrooms', 'Full Baths', 'Total Finished SF', 'Sale Price', 'Close Dt']
                        valid_cols = [col for col in comps_cols if col in comps.columns]
                        if len(valid_cols) > 0 and not comps.empty:
                            comps_display = comps[valid_cols].copy()
                            comps_display['Zillow'] = comps_display['Address'].apply(
                                lambda addr: f"<a href='{zillow_search_url(addr)}' target='_blank'><button style='background:#0074e4;border:none;color:white;border-radius:3px;padding:1px 6px;font-size:85%;'>Search</button></a>" if pd.notna(addr) else ""
                            )
                        else:
                            comps_display = pd.DataFrame(columns=comps_cols + ['Zillow'])
                        st.markdown(comps_display.to_html(index=False, escape=False), unsafe_allow_html=True)
                    
                    # EXPORT TO EXCEL
                    if st.button("⬇️ Export to Excel", key="export_all"):
                        output = BytesIO()
                        summary_df = styled_summary.copy()
                        focused_df = all_flips_table.copy()
                        details_rows = []
                        for mls in selected_mls:
                            active_row = all_flips_dict[str(mls)]['active']
                            comps = all_flips_dict[str(mls)]['comps']
                            active_cols = ['MLS #', 'Status', 'Area', 'Address', 'County', 'City', 'Zip', 'Sub',
                                           'Bedrooms', 'Full Baths', 'Total Finished SF', 'List Price', 'List Dt']
                            flip_detail_row = pd.DataFrame([active_row[active_cols]])
                            flip_detail_row['Zillow'] = f'=HYPERLINK("{zillow_search_url(active_row["Address"])}", "Zillow")'
                            details_rows.append(flip_detail_row)
                            comps_cols = ['MLS #', 'Status', 'Area', 'Address', 'County', 'City', 'Zip', 'Sub',
                                          'Bedrooms', 'Full Baths', 'Total Finished SF', 'Sale Price', 'Close Dt']
                            if not comps.empty:
                                comps_export = comps[comps_cols].copy()
                                comps_export['Zillow'] = comps_export['Address'].apply(
                                    lambda addr: f'=HYPERLINK("{zillow_search_url(addr)}", "Zillow")' if pd.notna(addr) else ""
                                )
                                details_rows.append(comps_export)
                            else:
                                empty_df = pd.DataFrame(columns=comps_cols + ['Zillow'])
                                details_rows.append(empty_df)
                            divider = pd.DataFrame([["----"] * (len(active_cols) + 1)], columns=active_cols + ['Zillow'])
                            details_rows.append(divider)
                        flip_details_export = pd.concat(details_rows, ignore_index=True)
                        criteria_dict = {
                            "Same ZIP": [same_zip],
                            "Same County": [same_county],
                            "Same City": [same_city],
                            "Same Sub": [same_sub],
                            "Same # Bedrooms": [same_beds],
                            "SF Range (%)": [sf_range],
                            "Sort selection": [sort_selection],
                            "Sub filter": [sub_filter if sub_filter else None],
                        }
                        criteria_df = pd.DataFrame(criteria_dict)
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            summary_df.to_excel(writer, sheet_name='Summary', index=False)
                            focused_df.to_excel(writer, sheet_name='Focused Area', index=False)
                            flip_details_export.to_excel(writer, sheet_name='Flip Details', index=False)
                            criteria_df.to_excel(writer, sheet_name='Comps Criteria', index=False)
                        nowstr = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                        filename = f"flip_analysis_{nowstr}.xlsx"
                        st.download_button(
                            label=f"Download Excel ({filename})",
                            data=output.getvalue(),
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
            if st.button("🔄 Reset Candidates View"):
                st.session_state['show_all_candidates'] = False

    # ================== BY AREA SORT ==================
    elif sort_selection in df_listings.columns:
        group_active = df_active.groupby(sort_selection)
        group_sold = df_sold.groupby(sort_selection)
        summary_active = group_active.agg(
            Listings_Count=('MLS #', 'count'),
            Avg_List_Price=('List Price', 'mean')
        )
        summary_sold = group_sold.agg(
            Sold_Count=('MLS #', 'count'),
            Avg_Sold_Price=('Sale Price', lambda x: x.dropna().mean())
        )
        summary = summary_active.join(summary_sold, how='outer').reset_index()
        summary.fillna({'Sold_Count': 0, 'Avg_Sold_Price': 0}, inplace=True)
        summary['Sold - List ($)'] = summary['Avg_Sold_Price'] - summary['Avg_List_Price']
        summary['Sold - List (%)'] = ((summary['Avg_Sold_Price'] - summary['Avg_List_Price']) / summary['Avg_List_Price'].replace(0, pd.NA)) * 100
        summary = summary.sort_values(by='Listings_Count', ascending=False)
        styled_summary = summary.copy()
        styled_summary[sort_selection] = summary[sort_selection]
        styled_summary['Avg_List_Price'] = styled_summary['Avg_List_Price'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "")
        styled_summary['Avg_Sold_Price'] = styled_summary['Avg_Sold_Price'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "")
        styled_summary['Sold - List ($)'] = styled_summary['Sold - List ($)'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "")
        styled_summary['Sold - List (%)'] = styled_summary['Sold - List (%)'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        st.subheader(f"Summary by {sort_selection}")
        st.dataframe(styled_summary, use_container_width=True)

        sub_options = sorted(df_listings[sort_selection].dropna().unique().astype(str).tolist())
        sub_filter = st.multiselect(f"Select {sort_selection}(s) to focus on:", sub_options)
        st.markdown("### Comps Matching Criteria")
        same_zip = st.checkbox("Same ZIP", value=True)
        same_county = st.checkbox("Same County")
        same_city = st.checkbox("Same City")
        same_sub = st.checkbox("Same Sub")
        same_beds = st.checkbox("Same # Bedrooms", value=True)
        sf_range = st.slider("± SF Range (%):", min_value=5, max_value=50, value=15, step=5)

        if st.button("▶️ Run Focused Area Analysis"):
            st.session_state['area_run_clicked'] = True

        if sub_filter and st.session_state.get('area_run_clicked', False):
            df_focus = df_active[df_active[sort_selection].astype(str).isin(sub_filter)].copy()
            focus_rows = []
            focus_comps_dict = {}
            for _, row in df_focus.iterrows():
                listing_sf = row['Total Finished SF']
                sf_min = listing_sf * (1 - sf_range / 100)
                sf_max = listing_sf * (1 + sf_range / 100)
                comps_filtered = df_sold.copy()
                if same_zip:
                    comps_filtered = comps_filtered[comps_filtered['Zip'].astype(str).str.strip() == str(row['Zip']).strip()]
                if same_county:
                    comps_filtered = comps_filtered[comps_filtered['County'].astype(str).str.strip().str.lower() == str(row['County']).strip().lower()]
                if same_city:
                    comps_filtered = comps_filtered[comps_filtered['City'].astype(str).str.strip().str.lower() == str(row['City']).strip().lower()]
                if same_sub:
                    comps_filtered = comps_filtered[comps_filtered['Sub'].astype(str).str.strip().str.lower() == str(row['Sub']).strip().lower()]
                if same_beds:
                    comps_filtered = comps_filtered[comps_filtered['Bedrooms'] == row['Bedrooms']]
                comps_filtered = comps_filtered[
                    (comps_filtered['Total Finished SF'] >= sf_min) &
                    (comps_filtered['Total Finished SF'] <= sf_max)
                ]
                avg_comp_price = comps_filtered['Sale Price'].mean() if not comps_filtered.empty else None
                num_comps = len(comps_filtered)
                price_diff = (avg_comp_price - row['List Price']) if avg_comp_price else None
                price_diff_pct = ((avg_comp_price - row['List Price']) / row['List Price'] * 100) if avg_comp_price else None
                focus_rows.append({
                    'Rank': 0,
                    'MLS #': str(row['MLS #']),
                    'Address': row['Address'],
                    'Bedrooms': row['Bedrooms'],
                    'SF': row['Total Finished SF'],
                    'List Price': row['List Price'],
                    'Avg Comp Price': avg_comp_price,
                    'Price Diff ($)': price_diff,
                    'Price Diff (%)': price_diff_pct,
                    '# of Comps': num_comps
                })
                focus_comps_dict[str(row['MLS #'])] = {
                    'active': row,
                    'comps': comps_filtered.copy()
                }
            if focus_rows:
                df_focus_table = pd.DataFrame(focus_rows)
                df_focus_table.sort_values(by='Price Diff (%)', ascending=False, inplace=True)
                df_focus_table['Rank'] = range(1, len(df_focus_table) + 1)
                cols = df_focus_table.columns.tolist()
                reordered = ['Rank'] + [col for col in cols if col != 'Rank']
                df_focus_table = df_focus_table[reordered]
                df_focus_table['List Price'] = df_focus_table['List Price'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "")
                df_focus_table['Avg Comp Price'] = df_focus_table['Avg Comp Price'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "")
                df_focus_table['Price Diff ($)'] = df_focus_table['Price Diff ($)'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "")
                df_focus_table['Price Diff (%)'] = df_focus_table['Price Diff (%)'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
                st.dataframe(df_focus_table, use_container_width=True)

                mls_plain_list = df_focus_table['MLS #'].tolist()
                selected_mls = st.multiselect("Select MLS #(s) to focus on:", mls_plain_list)
                if selected_mls:
                    st.session_state['focus_flips_selected'] = True
                    st.write(f"You selected to focus on MLS #: {', '.join(map(str, selected_mls))}")
                    for mls in selected_mls:
                        active_row = focus_comps_dict[str(mls)]['active']
                        comps = focus_comps_dict[str(mls)]['comps']
                        st.markdown("---")
                        st.markdown(
                            f"📌 Flip Details: MLS {mls} "
                            f"<a href='{zillow_search_url(active_row['Address'])}' target='_blank' "
                            f"style='text-decoration:none;'>"
                            f"<button style='background:#0074e4;border:none;color:white;border-radius:3px;padding:1px 6px;font-size:85%;margin-left:3px;'>Zillow Search</button></a>",
                            unsafe_allow_html=True
                        )
                        active_cols = ['MLS #', 'Status', 'Area', 'Address', 'County', 'City', 'Zip', 'Sub', 'Bedrooms', 'Full Baths', 'Total Finished SF', 'List Price', 'List Dt']
                        active_display = pd.DataFrame([active_row[active_cols]])
                        st.dataframe(active_display, use_container_width=True)
                        st.markdown("**Matching Comps:**")
                        comps_cols = ['MLS #', 'Status', 'Area', 'Address', 'County', 'City', 'Zip', 'Sub', 'Bedrooms', 'Full Baths', 'Total Finished SF', 'Sale Price', 'Close Dt']
                        valid_cols = [col for col in comps_cols if col in comps.columns]
                        if len(valid_cols) > 0 and not comps.empty:
                            comps_display = comps[valid_cols].copy()
                            comps_display['Zillow'] = comps_display['Address'].apply(
                                lambda addr: f"<a href='{zillow_search_url(addr)}' target='_blank'><button style='background:#0074e4;border:none;color:white;border-radius:3px;padding:1px 6px;font-size:85%;'>Search</button></a>" if pd.notna(addr) else ""
                            )
                        else:
                            comps_display = pd.DataFrame(columns=comps_cols + ['Zillow'])
                        st.markdown(comps_display.to_html(index=False, escape=False), unsafe_allow_html=True)

                    if st.button("⬇️ Export to Excel", key="export_focus"):
                        output = BytesIO()
                        summary_df = styled_summary.copy()
                        focused_df = df_focus_table.copy()
                        details_rows = []
                        for mls in selected_mls:
                            active_row = focus_comps_dict[str(mls)]['active']
                            comps = focus_comps_dict[str(mls)]['comps']
                            active_cols = ['MLS #', 'Status', 'Area', 'Address', 'County', 'City', 'Zip', 'Sub',
                                           'Bedrooms', 'Full Baths', 'Total Finished SF', 'List Price', 'List Dt']
                            flip_detail_row = pd.DataFrame([active_row[active_cols]])
                            flip_detail_row['Zillow'] = f'=HYPERLINK("{zillow_search_url(active_row["Address"])}", "Zillow")'
                            details_rows.append(flip_detail_row)
                            comps_cols = ['MLS #', 'Status', 'Area', 'Address', 'County', 'City', 'Zip', 'Sub',
                                          'Bedrooms', 'Full Baths', 'Total Finished SF', 'Sale Price', 'Close Dt']
                            if not comps.empty:
                                comps_export = comps[comps_cols].copy()
                                comps_export['Zillow'] = comps_export['Address'].apply(
                                    lambda addr: f'=HYPERLINK("{zillow_search_url(addr)}", "Zillow")' if pd.notna(addr) else ""
                                )
                                details_rows.append(comps_export)
                            else:
                                empty_df = pd.DataFrame(columns=comps_cols + ['Zillow'])
                                details_rows.append(empty_df)
                            divider = pd.DataFrame([["----"] * (len(active_cols) + 1)], columns=active_cols + ['Zillow'])
                            details_rows.append(divider)
                        flip_details_export = pd.concat(details_rows, ignore_index=True)
                        criteria_dict = {
                            "Same ZIP": [same_zip],
                            "Same County": [same_county],
                            "Same City": [same_city],
                            "Same Sub": [same_sub],
                            "Same # Bedrooms": [same_beds],
                            "SF Range (%)": [sf_range],
                            "Sort selection": [sort_selection],
                            "Sub filter": [sub_filter if sub_filter else None],
                        }
                        criteria_df = pd.DataFrame(criteria_dict)
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            summary_df.to_excel(writer, sheet_name='Summary', index=False)
                            focused_df.to_excel(writer, sheet_name='Focused Area', index=False)
                            flip_details_export.to_excel(writer, sheet_name='Flip Details', index=False)
                            criteria_df.to_excel(writer, sheet_name='Comps Criteria', index=False)
                        nowstr = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                        filename = f"flip_analysis_{nowstr}.xlsx"
                        st.download_button(
                            label=f"Download Excel ({filename})",
                            data=output.getvalue(),
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
            else:
                st.warning(f"No listings found in {sub_filter}.")
