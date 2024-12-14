# style.py
import streamlit as st


def apply_styles():
    st.markdown(
        """
        <style>
        :root {
            --bg-primary: #FFFFFF;
            --bg-secondary: #F5F5F7;
            --text-primary: #1D1D1F;
            --text-secondary: #86868B;
            --accent-primary: #2997FF;
            --accent-hover: #147CE5;
            --surface: #FFFFFF;
            --border: #E5E5E7;
        }
        .stApp {
            background: var(--bg-primary);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .header-container {
            background: var(--bg-primary);
            padding: 3rem 2rem;
            border-bottom: 1px solid var(--border);
            margin-bottom: 2rem;
        }
        .header-container h1 {
            font-size: 48px;
            font-weight: 600;
            color: var(--text-primary);
        }
        .stButton > button {
            background-color: #FF69B4 !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 4px !important;
            padding: 0.5rem 1.25rem !important;
            font-size: 16px !important;
            font-weight: 700 !important;
            min-width: 120px !important;
        }
        .stButton > button:hover {
            background-color: #FF1493 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
