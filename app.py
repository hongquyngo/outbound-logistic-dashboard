# app.py - Main Outbound Logistics Dashboard

import streamlit as st
from utils.auth import AuthManager

# ── Page config ──────────────────────────────────────────────────

st.set_page_config(
    page_title="Outbound Logistics Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

APP_VERSION = "2.0.0"
auth_manager = AuthManager()


# ── Login page ───────────────────────────────────────────────────

def show_login_page():
    st.markdown(
        "<h1 style='text-align:center; color:#1f77b4;'>🚚 Outbound Logistics Dashboard</h1>",
        unsafe_allow_html=True
    )

    _, col_center, _ = st.columns([1, 2, 1])

    with col_center:
        with st.form("login_form"):
            st.subheader("🔐 Login")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")

            if st.form_submit_button("Login", use_container_width=True, type="primary"):
                if username and password:
                    success, user_info = auth_manager.authenticate(username, password)
                    if success:
                        auth_manager.login(user_info)
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error(f"❌ {user_info.get('error', 'Login failed')}")
                else:
                    st.error("Please enter both username and password")


# ── Welcome page (after login) ───────────────────────────────────

def show_welcome():
    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {auth_manager.get_user_display_name()}")
        st.markdown(f"**Role:** {st.session_state.get('user_role', 'N/A')}")
        st.markdown("---")
        st.info("📌 Use the sidebar navigation to access pages")
        st.caption(f"Version: {APP_VERSION}")
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            auth_manager.logout()
            st.rerun()

    # Main content
    st.markdown(
        "<h1 style='text-align:center; color:#1f77b4;'>📦 Outbound Logistics Dashboard</h1>",
        unsafe_allow_html=True
    )

    st.markdown("---")

    name = auth_manager.get_user_display_name()
    st.markdown(f"### Welcome back, {name}! 👋")
    st.markdown("Select a page from the sidebar to get started.")

    st.markdown("")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        #### 📊 Delivery Schedule
        View delivery data with filters, pivot tables, product analysis,
        overdue alerts, and send email notifications — all in one page.
        """)

    with col2:
        st.markdown("""
        #### 🔜 Coming soon
        More modules will be added here as the system grows.
        """)


# ── Entry point ──────────────────────────────────────────────────

def main():
    if not auth_manager.check_session():
        show_login_page()
    else:
        show_welcome()


if __name__ == "__main__":
    main()