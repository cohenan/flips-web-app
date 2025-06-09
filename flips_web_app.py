
import streamlit as st
import pandas as pd
import streamlit_authenticator as stauth
from io import BytesIO

# ---- User Authentication ----
names = ["Kansas City User", "New York User"]
usernames = ["kc_user", "ny_user"]

# Matching order: kc_pass for kc_user, ny_pass for ny_user
hashed_passwords = stauth.Hasher(["kc_pass", "ny_pass"]).generate()
authenticator = stauth.Authenticate(
    names, usernames, hashed_passwords,
    "flips_app", "abcdef", cookie_expiry_days=1
)

name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status is False:
    st.error("Username/password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")
elif authentication_status:
    authenticator.logout("Logout", "sidebar")
    st.sidebar.success(f"Logged in as {name}")

    st.title("🏠 Real Estate Flip Analyzer")
    st.markdown("Upload **Active Listings CSV** and **Comps CSV** to begin:")

    active_file = st.file_uploader("Upload Active Listings CSV", type=["csv"])
    comps_file = st.file_uploader("Upload Comps CSV", type=["csv"])

    if active_file and comps_file:
        df_active = pd.read_csv(active_file)
        df_comps = pd.read_csv(comps_file)

        st.subheader("Active Listings Preview")
        st.dataframe(df_active.head())

        st.subheader("Comps Preview")
        st.dataframe(df_comps.head())

        # Merge on Zip and compare prices
        st.subheader("Filtered Potential Flips")
        merged_df = df_active.merge(df_comps, on="Zip", suffixes=("_active", "_comp"))
        merged_df["Price_Diff"] = merged_df["Price_comp"] - merged_df["Price_active"]
        merged_df = merged_df[merged_df["Price_Diff"] > 50000]

        st.dataframe(merged_df)

        st.subheader("📁 Export Results")
        def convert_df(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Flips')
            return output.getvalue()

        excel_data = convert_df(merged_df)
        st.download_button("Download Excel", data=excel_data, file_name="flip_candidates.xlsx")
