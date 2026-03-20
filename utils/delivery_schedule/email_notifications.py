# utils/delivery_schedule/email_notifications.py
"""Email notification tab — send delivery schedules, overdue alerts,
customs clearance emails.

Enhancements (v2):
  • TO/CC recipients selectable from employee list, email groups,
    plus additional manual entry.
  • Email send audit log  (email_send_log table).
  • Duplicate-send warning (same recipient + type + today).
  • Real HTML preview of the email content.
  • Email history section (recent 30 sends).
  • Performance: O(1) lookup for format_func lambdas.
  • Bug fix: _get_customer_contacts now respects weeks_ahead.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from .permissions import can_send_email
import re
import logging

logger = logging.getLogger(__name__)

# Notification type → clean DB key
_NOTIF_DB_KEY = {
    "📅 Delivery Schedule": "delivery_schedule",
    "🚨 Overdue Alerts":    "overdue_alert",
    "🛃 Custom Clearance":  "customs_clearance",
}


# ═════════════════════════════════════════════════════════════════
# MAIN FRAGMENT
# ═════════════════════════════════════════════════════════════════

@st.fragment
def display_email_notifications(data_loader, email_sender):
    """Full email notification UI — runs as a fragment."""

    if not can_send_email():
        st.warning("🔒 You need manager/logistics role to send emails.")
        return

    st.subheader("📧 Email Notifications")
    st.caption("Send delivery schedules, urgent alerts, or customs clearance emails")

    # ── Email History (collapsible, at top) ────────────────────────
    _render_email_history(data_loader)

    # ── Layout: Recipients (left) + Settings (right) ─────────────
    col_left, col_right = st.columns([2, 1])

    with col_right:
        notification_type = st.radio(
            "📧 Notification Type",
            ["📅 Delivery Schedule", "🚨 Overdue Alerts", "🛃 Custom Clearance"],
            key="email_notif_type",
        )

        weeks_ahead = 4
        if notification_type in ["📅 Delivery Schedule", "🛃 Custom Clearance"]:
            weeks_ahead = st.selectbox(
                "📅 Time Period", options=[1, 2, 3, 4, 5, 6, 7, 8], index=3,
                format_func=lambda x: f"{x} week{'s' if x > 1 else ''}",
                key="email_weeks_ahead",
            )

        schedule_type = st.radio(
            "Schedule Type", ["Preview Only", "Send Now"], index=0,
            key="email_schedule_type",
        )

    # ── Recipients ────────────────────────────────────────────────
    with col_left:
        selected_recipients = []
        selected_customer_contacts = []
        custom_recipients = []
        customs_to_emails = []
        sales_df = pd.DataFrame()

        if notification_type == "🛃 Custom Clearance":
            recipient_type = "customs"
            _show_customs_summary(data_loader, weeks_ahead)
            customs_to_emails = _render_customs_recipients(data_loader)

        else:
            recipient_type = st.selectbox(
                "Send to:",
                ["creators", "customers", "custom"],
                format_func=lambda x: {
                    "creators":  "👤 Sales/Creators",
                    "customers": "🏢 Customers",
                    "custom":    "✉️ Custom Recipients",
                }[x],
                key="email_recipient_type",
            )

            if recipient_type == "creators":
                sales_df, selected_recipients = _render_creator_selection(
                    data_loader, notification_type, weeks_ahead,
                )
            elif recipient_type == "customers":
                selected_customer_contacts = _render_customer_selection(
                    data_loader, weeks_ahead,
                )
            else:
                custom_recipients = _render_custom_selection(data_loader)

    # ── CC settings (right column) ────────────────────────────────
    with col_right:
        cc_emails = _render_cc_settings(
            data_loader, notification_type,
            recipient_type if notification_type != "🛃 Custom Clearance" else "customs",
            selected_recipients,
            sales_df if not sales_df.empty else None,
        )

    st.markdown("---")

    # ── Preview ───────────────────────────────────────────────────
    can_preview = _can_proceed(
        notification_type, recipient_type if notification_type != "🛃 Custom Clearance" else "customs",
        selected_recipients, selected_customer_contacts,
        custom_recipients, customs_to_emails,
    )

    if can_preview and st.button("👁️ Preview Email Content", key="email_preview_btn"):
        _render_preview(
            data_loader, email_sender, notification_type,
            recipient_type if notification_type != "🛃 Custom Clearance" else "customs",
            selected_recipients, selected_customer_contacts,
            custom_recipients, customs_to_emails, sales_df, weeks_ahead,
        )

    # ── Send ──────────────────────────────────────────────────────
    if can_preview and schedule_type == "Send Now":
        st.markdown("---")
        _render_send_section(
            data_loader, email_sender, notification_type,
            recipient_type if notification_type != "🛃 Custom Clearance" else "customs",
            selected_recipients, selected_customer_contacts,
            custom_recipients, customs_to_emails,
            sales_df, cc_emails, weeks_ahead,
        )

    # ── Help ──────────────────────────────────────────────────────
    with st.expander("ℹ️ Help & Information"):
        st.markdown("""
        **📅 Delivery Schedule** — upcoming deliveries grouped by week, with Excel + calendar attachment  
        **🚨 Overdue Alerts** — urgent notifications for overdue/due-today items  
        **🛃 Custom Clearance** — EPE & Foreign customer deliveries for customs team  

        **Recipient types:** Sales/Creators · Customers (2-step: company → contact) · Custom (employee picker / email group / manual)  
        **CC sources:** Employee picker · Email group · Manager auto-CC · Manual entry  
        """)


# ═════════════════════════════════════════════════════════════════
# DATA QUERIES (cached)
# ═════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300)
def _get_sales_list(_engine, weeks_ahead=4):
    """Sales people with active deliveries."""
    query = text("""
    SELECT DISTINCT
        e.id, CONCAT(e.first_name, ' ', e.last_name) as name, e.email,
        COUNT(DISTINCT d.delivery_id) as active_deliveries,
        SUM(d.remaining_quantity_to_deliver) as total_quantity,
        COUNT(DISTINCT CASE WHEN d.delivery_timeline_status = 'Overdue'
              THEN d.delivery_id END) as overdue_deliveries,
        m.email as manager_email
    FROM employees e
    LEFT JOIN employees m ON e.manager_id = m.id
    INNER JOIN delivery_full_view d ON d.created_by_email = e.email
    WHERE d.etd >= CURDATE()
      AND d.etd <= DATE_ADD(CURDATE(), INTERVAL :weeks WEEK)
      AND d.remaining_quantity_to_deliver > 0
      AND d.shipment_status NOT IN ('DELIVERED', 'COMPLETED')
    GROUP BY e.id, e.first_name, e.last_name, e.email, m.email
    ORDER BY name
    """)
    with _engine.connect() as conn:
        return pd.read_sql(query, conn, params={'weeks': weeks_ahead})


@st.cache_data(ttl=300)
def _get_sales_list_overdue(_engine):
    """Sales with overdue/due-today deliveries."""
    query = text("""
    SELECT DISTINCT
        e.id, CONCAT(e.first_name, ' ', e.last_name) as name, e.email,
        COUNT(DISTINCT CASE WHEN d.delivery_timeline_status = 'Overdue'
              THEN d.delivery_id END) as overdue_deliveries,
        COUNT(DISTINCT CASE WHEN d.delivery_timeline_status = 'Due Today'
              THEN d.delivery_id END) as due_today_deliveries,
        MAX(d.days_overdue) as max_days_overdue,
        m.email as manager_email
    FROM employees e
    LEFT JOIN employees m ON e.manager_id = m.id
    INNER JOIN delivery_full_view d ON d.created_by_email = e.email
    WHERE d.delivery_timeline_status IN ('Overdue', 'Due Today')
      AND d.remaining_quantity_to_deliver > 0
      AND d.shipment_status NOT IN ('DELIVERED', 'COMPLETED')
    GROUP BY e.id, e.first_name, e.last_name, e.email, m.email
    HAVING (overdue_deliveries > 0 OR due_today_deliveries > 0)
    ORDER BY overdue_deliveries DESC, name
    """)
    with _engine.connect() as conn:
        return pd.read_sql(query, conn)


@st.cache_data(ttl=300)
def _get_customers_with_deliveries(_engine, weeks_ahead=4):
    """Customers with active deliveries."""
    query = text("""
    SELECT DISTINCT
        d.customer, d.customer_code,
        COUNT(DISTINCT d.delivery_id) as active_deliveries,
        SUM(d.remaining_quantity_to_deliver) as total_quantity,
        COUNT(DISTINCT d.recipient_state_province) as provinces_count
    FROM delivery_full_view d
    WHERE d.etd >= CURDATE()
      AND d.etd <= DATE_ADD(CURDATE(), INTERVAL :weeks WEEK)
      AND d.remaining_quantity_to_deliver > 0
      AND d.shipment_status NOT IN ('DELIVERED', 'COMPLETED')
    GROUP BY d.customer, d.customer_code
    ORDER BY d.customer
    """)
    with _engine.connect() as conn:
        return pd.read_sql(query, conn, params={'weeks': weeks_ahead})


@st.cache_data(ttl=300)
def _get_customer_contacts(_engine, customer_names, weeks_ahead=4):
    """Contacts for selected customers — weeks_ahead is now dynamic."""
    if not customer_names:
        return pd.DataFrame()
    query = text("""
    SELECT DISTINCT
        CONCAT(d.customer, '_', COALESCE(d.customer_contact_email, 'no_email'), '_',
               COALESCE(d.customer_contact, 'Unknown')) as contact_id,
        d.customer,
        COALESCE(d.customer_contact, 'Unknown Contact') as contact_name,
        d.customer_contact_email as email,
        COUNT(DISTINCT d.delivery_id) as delivery_count
    FROM delivery_full_view d
    WHERE d.customer IN :customers
      AND d.etd >= CURDATE()
      AND d.etd <= DATE_ADD(CURDATE(), INTERVAL :weeks WEEK)
      AND d.remaining_quantity_to_deliver > 0
      AND d.shipment_status NOT IN ('DELIVERED', 'COMPLETED')
      AND d.customer_contact_email IS NOT NULL
      AND d.customer_contact_email != ''
    GROUP BY d.customer, d.customer_contact, d.customer_contact_email
    ORDER BY d.customer, d.customer_contact
    """)
    with _engine.connect() as conn:
        return pd.read_sql(query, conn, params={
            'customers': tuple(customer_names),
            'weeks': weeks_ahead,
        })


# ═════════════════════════════════════════════════════════════════
# UI — Recipient selection
# ═════════════════════════════════════════════════════════════════

def _validate_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is not None


def _can_proceed(notif_type, recip_type, selected, contacts, custom, customs_to):
    if notif_type == "🛃 Custom Clearance":
        return bool(customs_to)
    if recip_type == "creators" and selected:
        return True
    if recip_type == "customers" and contacts:
        return True
    if recip_type == "custom" and custom:
        return True
    return False


def _show_customs_summary(data_loader, weeks_ahead):
    customs = data_loader.get_customs_clearance_summary(weeks_ahead)
    if not customs.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("EPE Deliveries", customs['epe_deliveries'].sum())
        c2.metric("Foreign Deliveries", customs['foreign_deliveries'].sum())
        c3.metric("Total Countries", customs['countries'].sum())
    else:
        st.warning(f"No customs deliveries found for the next {weeks_ahead} weeks")


def _render_creator_selection(data_loader, notification_type, weeks_ahead):
    """Render sales/creator selection; return (sales_df, selected_names)."""
    if notification_type == "🚨 Overdue Alerts":
        sales_df = _get_sales_list_overdue(data_loader.engine)
    else:
        sales_df = _get_sales_list(data_loader.engine, weeks_ahead)

    if sales_df.empty:
        st.warning("No sales with active deliveries found")
        return pd.DataFrame(), []

    # Build O(1) lookup dict — avoids repeated DataFrame filtering
    lookup = sales_df.set_index('name').to_dict('index')

    if notification_type == "🚨 Overdue Alerts":
        def fmt(x):
            r = lookup.get(x, {})
            return f"{x} (OD:{r.get('overdue_deliveries', 0)}, DT:{r.get('due_today_deliveries', 0)})"
    else:
        def fmt(x):
            r = lookup.get(x, {})
            return f"{x} ({r.get('active_deliveries', 0)} del, {r.get('total_quantity', 0):,.0f} units)"

    selected = st.multiselect(
        "Select sales people:", options=sales_df['name'].tolist(),
        format_func=fmt, key="email_select_creators",
    )

    if selected:
        sel_df = sales_df[sales_df['name'].isin(selected)]
        if notification_type == "🚨 Overdue Alerts":
            disp = sel_df[['name', 'email', 'overdue_deliveries', 'due_today_deliveries']].copy()
            disp.columns = ['Name', 'Email', 'Overdue', 'Due Today']
        else:
            disp = sel_df[['name', 'email', 'active_deliveries', 'total_quantity']].copy()
            disp['total_quantity'] = disp['total_quantity'].apply(lambda x: f"{x:,.0f}")
            disp.columns = ['Name', 'Email', 'Deliveries', 'Pending Qty']
        st.dataframe(disp, use_container_width=True, hide_index=True)

    return sales_df, selected


def _render_customer_selection(data_loader, weeks_ahead):
    """Two-step customer → contact selection; return list of contact dicts."""
    cust_df = _get_customers_with_deliveries(data_loader.engine, weeks_ahead)
    if cust_df.empty:
        st.warning("No customers with active deliveries found")
        return []

    # O(1) lookup
    cust_lookup = cust_df.set_index('customer').to_dict('index')
    fmt_cust = lambda x: f"{x} ({cust_lookup.get(x, {}).get('active_deliveries', 0)} del)"

    selected_names = st.multiselect(
        "Step 1 — Select customers:",
        options=cust_df['customer'].tolist(),
        format_func=fmt_cust, key="email_select_customers",
    )
    if not selected_names:
        st.info("Select customers to see contacts")
        return []

    contacts_df = _get_customer_contacts(data_loader.engine, selected_names, weeks_ahead)
    if contacts_df.empty:
        st.warning("No contacts found for selected customers")
        return []

    # O(1) lookup
    ct_lookup = contacts_df.set_index('contact_id').to_dict('index')
    fmt_ct = lambda cid: (
        f"{ct_lookup[cid]['contact_name']} — {ct_lookup[cid]['customer']} "
        f"({ct_lookup[cid]['email']})"
    )

    selected_ids = st.multiselect(
        "Step 2 — Select contacts:",
        options=contacts_df['contact_id'].tolist(),
        format_func=fmt_ct, key="email_select_contacts",
    )

    contacts = contacts_df[contacts_df['contact_id'].isin(selected_ids)].to_dict('records')
    if contacts:
        st.dataframe(
            pd.DataFrame(contacts)[['customer', 'contact_name', 'email']].rename(
                columns={'customer': 'Customer', 'contact_name': 'Contact', 'email': 'Email'}),
            use_container_width=True, hide_index=True,
        )
    return contacts


def _render_custom_selection(data_loader):
    """Enhanced custom email entry: employee picker + email group + manual."""
    all_emails = []

    # ── Employee picker ──────────────────────────────────────────
    emp_df = data_loader.get_employees_for_picker()
    if not emp_df.empty:
        emp_map = {
            f"{r['name']}  ·  {r['email']}" + (f"  ·  {r['position']}" if pd.notna(r.get('position')) else ""): r['email']
            for _, r in emp_df.iterrows()
        }
        sel_emps = st.multiselect(
            "👥 Select Employees",
            options=list(emp_map.keys()),
            placeholder="Search employees…",
            key="custom_to_employees",
        )
        all_emails.extend(emp_map[s] for s in sel_emps)

    # ── Email Group picker ───────────────────────────────────────
    grp_df = data_loader.get_email_groups()
    if not grp_df.empty:
        grp_map = {
            f"{r['group_name']}  ({r['member_count']} members)": r['member_emails']
            for _, r in grp_df.iterrows()
        }
        sel_grps = st.multiselect(
            "📋 Select Email Groups",
            options=list(grp_map.keys()),
            placeholder="Select groups…",
            key="custom_to_groups",
        )
        for sg in sel_grps:
            all_emails.extend(e.strip() for e in grp_map[sg].split(',') if e.strip())

    # ── Additional manual entry ──────────────────────────────────
    txt = st.text_area(
        "✉️ Additional emails (one per line)",
        placeholder="john@company.com\njane@company.com",
        height=100, key="email_custom_text",
    )
    if txt:
        for e in txt.strip().split('\n'):
            e = e.strip()
            if e and _validate_email(e):
                all_emails.append(e)
            elif e:
                st.error(f"Invalid email: {e}")

    # Deduplicate
    all_emails = list(dict.fromkeys(all_emails))

    if all_emails:
        st.success(f"✅ {len(all_emails)} recipient(s) selected")
    return all_emails


def _render_customs_recipients(data_loader):
    """Select TO recipients for customs clearance (replaces hardcoded email)."""
    st.info("📌 Select recipients for the customs clearance email")
    all_emails = []

    # ── Email Group (primary source for customs team) ────────────
    grp_df = data_loader.get_email_groups()
    if not grp_df.empty:
        grp_map = {
            f"{r['group_name']}  ({r['member_count']} members)": r['member_emails']
            for _, r in grp_df.iterrows()
        }
        sel_grps = st.multiselect(
            "📋 Select Email Groups",
            options=list(grp_map.keys()),
            placeholder="e.g. Customs Team…",
            key="customs_to_groups",
        )
        for sg in sel_grps:
            all_emails.extend(e.strip() for e in grp_map[sg].split(',') if e.strip())

    # ── Employee picker ──────────────────────────────────────────
    emp_df = data_loader.get_employees_for_picker()
    if not emp_df.empty:
        emp_map = {
            f"{r['name']}  ·  {r['email']}": r['email']
            for _, r in emp_df.iterrows()
        }
        sel_emps = st.multiselect(
            "👥 Select Employees",
            options=list(emp_map.keys()),
            placeholder="Search employees…",
            key="customs_to_employees",
        )
        all_emails.extend(emp_map[s] for s in sel_emps)

    # ── Additional manual ────────────────────────────────────────
    extra = st.text_input(
        "✉️ Additional TO email",
        placeholder="customs@partner.com",
        key="customs_to_manual",
    )
    if extra and _validate_email(extra.strip()):
        all_emails.append(extra.strip())
    elif extra:
        st.error(f"Invalid email: {extra}")

    all_emails = list(dict.fromkeys(all_emails))

    if all_emails:
        st.success(f"✅ {len(all_emails)} recipient(s): {', '.join(all_emails)}")
    else:
        st.warning("Select at least one recipient")
    return all_emails


# ═════════════════════════════════════════════════════════════════
# UI — CC settings
# ═════════════════════════════════════════════════════════════════

def _render_cc_settings(data_loader, notification_type, recipient_type,
                        selected_recipients, sales_df):
    """Enhanced CC settings: employee picker + email group + manager + manual."""
    cc_emails = []

    # ── Employee picker for CC ───────────────────────────────────
    emp_df = data_loader.get_employees_for_picker()
    if not emp_df.empty:
        emp_map = {
            f"{r['name']}  ·  {r['email']}": r['email']
            for _, r in emp_df.iterrows()
        }
        sel_cc_emps = st.multiselect(
            "👥 CC Employees",
            options=list(emp_map.keys()),
            placeholder="Search employees…",
            key="cc_employees",
        )
        cc_emails.extend(emp_map[s] for s in sel_cc_emps)

    # ── Email Group for CC ───────────────────────────────────────
    grp_df = data_loader.get_email_groups()
    if not grp_df.empty:
        grp_map = {
            f"{r['group_name']}  ({r['member_count']} members)": r['member_emails']
            for _, r in grp_df.iterrows()
        }
        sel_cc_grps = st.multiselect(
            "📋 CC Email Groups",
            options=list(grp_map.keys()),
            placeholder="Select groups…",
            key="cc_email_groups",
        )
        for sg in sel_cc_grps:
            cc_emails.extend(e.strip() for e in grp_map[sg].split(',') if e.strip())

    # ── Auto-CC Managers (for creator type) ──────────────────────
    if recipient_type == "creators" and sales_df is not None and selected_recipients:
        if st.checkbox("CC to managers", value=True, key="email_cc_managers"):
            sel_df = sales_df[sales_df['name'].isin(selected_recipients)]
            mgr = sel_df[sel_df['manager_email'].notna()]['manager_email'].unique().tolist()
            if mgr:
                st.caption(f"Managers: {', '.join(mgr)}")
                cc_emails.extend(mgr)

    # ── Additional manual CC ─────────────────────────────────────
    additional = st.text_area(
        "✉️ Additional CC (one per line)", height=80,
        key="email_additional_cc",
        placeholder="outbound@prostech.vn",
    )
    if additional:
        for e in additional.split('\n'):
            e = e.strip()
            if e and _validate_email(e):
                cc_emails.append(e)

    # Deduplicate
    cc_emails = list(dict.fromkeys(cc_emails))
    if cc_emails:
        st.caption(f"Total CC: {len(cc_emails)}")
    return cc_emails


# ═════════════════════════════════════════════════════════════════
# PREVIEW
# ═════════════════════════════════════════════════════════════════

def _render_preview(data_loader, email_sender, notif_type, recip_type,
                    selected, contacts, custom, customs_to, sales_df, weeks):
    """Enhanced preview: metrics + actual HTML email content."""
    with st.spinner("Generating preview..."):
        try:
            df = None

            if notif_type == "🛃 Custom Clearance":
                df = data_loader.get_customs_clearance_schedule(weeks)
                if df.empty:
                    st.warning("No customs deliveries"); return
                c1, c2, c3 = st.columns(3)
                c1.metric("EPE", df[df.get('customs_type', pd.Series()) == 'EPE']['delivery_id'].nunique()
                          if 'customs_type' in df.columns else "–")
                c2.metric("Foreign", df[df.get('customs_type', pd.Series()) == 'Foreign']['delivery_id'].nunique()
                          if 'customs_type' in df.columns else "–")
                c3.metric("Pending Qty", f"{df['remaining_quantity_to_deliver'].sum():,.0f}")

            elif recip_type == "customers" and contacts:
                ct = contacts[0]
                st.markdown(f"**Preview for {ct['customer']} — {ct['contact_name']}**")
                df = data_loader.get_customer_deliveries(ct['customer'], weeks)
                if df.empty:
                    st.info("No deliveries"); return
                c1, c2, c3 = st.columns(3)
                c1.metric("Deliveries", df['delivery_id'].nunique())
                c2.metric("Products", df['product_pn'].nunique())
                c3.metric("Pending Qty", f"{df['remaining_quantity_to_deliver'].sum():,.0f}")

            elif recip_type == "creators" and selected:
                name = selected[0]
                st.markdown(f"**Preview for {name}**")
                df = (data_loader.get_sales_delivery_summary(name, weeks)
                      if notif_type == "📅 Delivery Schedule"
                      else data_loader.get_sales_urgent_deliveries(name))
                if df.empty:
                    st.info("No deliveries"); return
                c1, c2, c3 = st.columns(3)
                c1.metric("Deliveries", df['delivery_id'].nunique())
                c2.metric("Customers", df['customer'].nunique())
                c3.metric("Pending Qty", f"{df['remaining_quantity_to_deliver'].sum():,.0f}")

            elif recip_type == "custom" and custom:
                df = data_loader.get_all_deliveries_summary(weeks)
                if df.empty:
                    st.warning("No delivery data"); return
                c1, c2, c3 = st.columns(3)
                c1.metric("Deliveries", df['delivery_id'].nunique())
                c2.metric("Customers", df['customer'].nunique())
                c3.metric("Pending Qty", f"{df['remaining_quantity_to_deliver'].sum():,.0f}")

            # ── Render actual HTML preview ────────────────────────
            if df is not None and not df.empty and notif_type != "🛃 Custom Clearance":
                with st.expander("📧 Email HTML Preview", expanded=True):
                    preview_df = df.copy()
                    try:
                        if notif_type == "🚨 Overdue Alerts":
                            html = email_sender.create_overdue_alerts_html(
                                preview_df, "Preview Recipient")
                        else:
                            html = email_sender.create_delivery_schedule_html(
                                preview_df, "Preview Recipient", weeks)
                        components.html(html, height=600, scrolling=True)
                    except Exception as e:
                        st.warning(f"Could not render HTML preview: {e}")
                        logger.warning(f"HTML preview error: {e}")

        except Exception as e:
            st.error(f"Preview error: {e}")
            logger.error(f"Preview error: {e}", exc_info=True)


# ═════════════════════════════════════════════════════════════════
# SEND
# ═════════════════════════════════════════════════════════════════

def _render_send_section(data_loader, email_sender, notif_type, recip_type,
                         selected, contacts, custom, customs_to,
                         sales_df, cc_emails, weeks):
    st.subheader("📤 Send Emails")

    # ── Recipient count summary ──────────────────────────────────
    if notif_type == "🛃 Custom Clearance":
        count_str = f"{len(customs_to)} customs recipient(s)"
    elif recip_type == "creators":
        count_str = f"{len(selected)} sales people"
    elif recip_type == "customers":
        count_str = f"{len(contacts)} customer contacts"
    else:
        count_str = f"{len(custom)} custom recipient(s)"

    st.warning(f"⚠️ About to send **{notif_type}** emails to {count_str}")

    # ── Duplicate check ──────────────────────────────────────────
    db_notif_type = _NOTIF_DB_KEY.get(notif_type, notif_type)
    all_to_emails = _collect_all_to_emails(
        notif_type, recip_type, selected, contacts, custom,
        customs_to, sales_df,
    )
    duplicates = []
    for email in all_to_emails:
        sent, last_time = data_loader.check_email_sent_today(email, db_notif_type)
        if sent:
            duplicates.append(f"{email} (last: {last_time})")

    if duplicates:
        st.warning(
            f"⚠️ Already sent today to **{len(duplicates)}** recipient(s):\n"
            + ", ".join(duplicates)
            + "\n\nYou can still send again if needed."
        )

    # ── Confirm + Send ───────────────────────────────────────────
    confirm = st.checkbox("I confirm to send these emails", key="email_confirm_send")

    if confirm and st.button("🚀 Send Emails Now", type="primary", key="email_send_btn"):
        results, errors = _execute_send(
            data_loader, email_sender, notif_type, recip_type,
            selected, contacts, custom, customs_to,
            sales_df, cc_emails, weeks,
        )
        _show_results(results, errors)


def _collect_all_to_emails(notif_type, recip_type, selected, contacts,
                            custom, customs_to, sales_df):
    """Collect all TO emails for duplicate checking."""
    emails = []
    if notif_type == "🛃 Custom Clearance":
        emails = customs_to[:]
    elif recip_type == "creators" and selected and sales_df is not None and not sales_df.empty:
        for name in selected:
            rows = sales_df[sales_df['name'] == name]
            if not rows.empty:
                emails.append(rows.iloc[0]['email'])
    elif recip_type == "customers" and contacts:
        emails = [ct['email'] for ct in contacts]
    elif recip_type == "custom":
        emails = custom[:]
    return emails


def _execute_send(data_loader, email_sender, notif_type, recip_type,
                  selected, contacts, custom, customs_to,
                  sales_df, cc_emails, weeks):
    """Execute email sending with progress bar + audit logging."""
    progress = st.progress(0)
    status = st.empty()
    results = []
    errors = []
    db_notif_type = _NOTIF_DB_KEY.get(notif_type, notif_type)
    cc_str = ', '.join(cc_emails) if cc_emails else None

    try:
        # ── Customs Clearance ────────────────────────────────────
        if notif_type == "🛃 Custom Clearance":
            df = data_loader.get_customs_clearance_schedule(weeks)
            if df.empty:
                st.warning("No customs data")
                return results, errors

            total = len(customs_to)
            for i, to_email in enumerate(customs_to):
                progress.progress((i + 1) / total)
                status.text(f"Sending customs email to {to_email}... ({i+1}/{total})")
                try:
                    ok, msg = email_sender.send_customs_clearance_email(
                        to_email, df, cc_emails=cc_emails or None)
                    entry = {'Recipient': to_email, 'Email': to_email,
                             'Status': '✅' if ok else '❌', 'Message': msg}
                    results.append(entry)
                    data_loader.log_email_send(
                        db_notif_type, to_email, to_email, 'customs_team',
                        cc_str, f"Customs Clearance Schedule", df['delivery_id'].nunique(),
                        float(df['remaining_quantity_to_deliver'].sum()), weeks,
                        'SUCCESS' if ok else 'FAILED', None if ok else msg,
                    )
                except Exception as e:
                    errors.append(str(e))
                    results.append({'Recipient': to_email, 'Email': to_email,
                                    'Status': '❌', 'Message': str(e)})
                    data_loader.log_email_send(
                        db_notif_type, to_email, to_email, 'customs_team',
                        cc_str, None, 0, 0, weeks, 'FAILED', str(e),
                    )

        # ── Customers ────────────────────────────────────────────
        elif recip_type == "customers":
            for i, ct in enumerate(contacts):
                progress.progress((i + 1) / len(contacts))
                status.text(f"Sending to {ct['contact_name']}... ({i+1}/{len(contacts)})")
                try:
                    df = data_loader.get_customer_deliveries(ct['customer'], weeks)
                    if not df.empty:
                        ok, msg = email_sender.send_delivery_schedule_email(
                            ct['email'], ct['customer'], df,
                            cc_emails=cc_emails or None,
                            notification_type=notif_type, weeks_ahead=weeks,
                            contact_name=ct['contact_name'])
                        entry = {'Recipient': f"{ct['contact_name']} ({ct['customer']})",
                                 'Email': ct['email'],
                                 'Status': '✅' if ok else '❌', 'Message': msg}
                        results.append(entry)
                        data_loader.log_email_send(
                            db_notif_type, ct['email'], ct['contact_name'],
                            'customer_contact', cc_str, None,
                            df['delivery_id'].nunique(),
                            float(df['remaining_quantity_to_deliver'].sum()),
                            weeks, 'SUCCESS' if ok else 'FAILED',
                            None if ok else msg,
                        )
                    else:
                        results.append({'Recipient': ct['contact_name'],
                                        'Email': ct['email'],
                                        'Status': '⚠️ Skip', 'Message': 'No deliveries'})
                        data_loader.log_email_send(
                            db_notif_type, ct['email'], ct['contact_name'],
                            'customer_contact', cc_str, None, 0, 0, weeks, 'SKIPPED',
                        )
                except Exception as e:
                    errors.append(str(e))
                    results.append({'Recipient': ct['contact_name'],
                                    'Email': ct['email'],
                                    'Status': '❌', 'Message': str(e)})
                    data_loader.log_email_send(
                        db_notif_type, ct['email'], ct.get('contact_name', ''),
                        'customer_contact', cc_str, None, 0, 0, weeks, 'FAILED', str(e),
                    )

        # ── Custom recipients ────────────────────────────────────
        elif recip_type == "custom":
            for i, email in enumerate(custom):
                progress.progress((i + 1) / len(custom))
                status.text(f"Sending to {email}... ({i+1}/{len(custom)})")
                try:
                    name = email.split('@')[0].title()
                    df = (data_loader.get_all_deliveries_summary(weeks)
                          if notif_type == "📅 Delivery Schedule"
                          else data_loader.get_all_urgent_deliveries())
                    if not df.empty:
                        ok, msg = email_sender.send_delivery_schedule_email(
                            email, name, df, cc_emails=cc_emails or None,
                            notification_type=notif_type, weeks_ahead=weeks)
                        results.append({'Recipient': name, 'Email': email,
                                        'Status': '✅' if ok else '❌', 'Message': msg})
                        data_loader.log_email_send(
                            db_notif_type, email, name, 'custom', cc_str, None,
                            df['delivery_id'].nunique(),
                            float(df['remaining_quantity_to_deliver'].sum()),
                            weeks, 'SUCCESS' if ok else 'FAILED',
                            None if ok else msg,
                        )
                    else:
                        results.append({'Recipient': name, 'Email': email,
                                        'Status': '⚠️ Skip', 'Message': 'No deliveries'})
                        data_loader.log_email_send(
                            db_notif_type, email, name, 'custom', cc_str, None,
                            0, 0, weeks, 'SKIPPED',
                        )
                except Exception as e:
                    errors.append(str(e))
                    results.append({'Recipient': email, 'Email': email,
                                    'Status': '❌', 'Message': str(e)})
                    data_loader.log_email_send(
                        db_notif_type, email, '', 'custom', cc_str, None,
                        0, 0, weeks, 'FAILED', str(e),
                    )

        # ── Creators ─────────────────────────────────────────────
        else:
            for i, name in enumerate(selected):
                progress.progress((i + 1) / len(selected))
                status.text(f"Sending to {name}... ({i+1}/{len(selected)})")
                try:
                    info = sales_df[sales_df['name'] == name].iloc[0]
                    df = (data_loader.get_sales_delivery_summary(name, weeks)
                          if notif_type == "📅 Delivery Schedule"
                          else data_loader.get_sales_urgent_deliveries(name))
                    if not df.empty:
                        ok, msg = email_sender.send_delivery_schedule_email(
                            info['email'], name, df, cc_emails=cc_emails or None,
                            notification_type=notif_type, weeks_ahead=weeks)
                        results.append({'Recipient': name, 'Email': info['email'],
                                        'Status': '✅' if ok else '❌', 'Message': msg})
                        data_loader.log_email_send(
                            db_notif_type, info['email'], name, 'creator', cc_str,
                            None, df['delivery_id'].nunique(),
                            float(df['remaining_quantity_to_deliver'].sum()),
                            weeks, 'SUCCESS' if ok else 'FAILED',
                            None if ok else msg,
                        )
                    else:
                        results.append({'Recipient': name, 'Email': info['email'],
                                        'Status': '⚠️ Skip', 'Message': 'No deliveries'})
                        data_loader.log_email_send(
                            db_notif_type, info['email'], name, 'creator', cc_str,
                            None, 0, 0, weeks, 'SKIPPED',
                        )
                except Exception as e:
                    errors.append(str(e))
                    results.append({'Recipient': name, 'Email': 'N/A',
                                    'Status': '❌', 'Message': str(e)})
                    data_loader.log_email_send(
                        db_notif_type, '', name, 'creator', cc_str,
                        None, 0, 0, weeks, 'FAILED', str(e),
                    )

    except Exception as e:
        st.error(f"Critical error: {e}")
        logger.error(f"Send error: {e}", exc_info=True)

    progress.empty()
    status.empty()
    return results, errors


def _show_results(results, errors):
    if not results:
        return
    st.success("✅ Email process completed!")
    df = pd.DataFrame(results)
    c1, c2, c3 = st.columns(3)
    c1.metric("Success", len(df[df['Status'] == '✅']))
    c2.metric("Failed", len(df[df['Status'] == '❌']))
    c3.metric("Skipped", len(df[df['Status'].str.contains('Skip', na=False)]))
    st.dataframe(df, use_container_width=True, hide_index=True)
    if errors:
        with st.expander("❌ Error Details"):
            for e in errors:
                st.error(e)


# ═════════════════════════════════════════════════════════════════
# EMAIL HISTORY
# ═════════════════════════════════════════════════════════════════

def _render_email_history(data_loader):
    """Display recent email send history (collapsible)."""
    with st.expander("📜 Email History (recent 30)", expanded=False):
        history = data_loader.get_email_history(limit=30)

        if history.empty:
            st.info("No emails sent yet.")
            return

        # Status icons
        status_map = {'SUCCESS': '✅', 'FAILED': '❌', 'SKIPPED': '⚠️'}
        history['Status'] = history['status'].map(status_map).fillna(history['status'])

        display_cols = {
            'sent_at': 'Sent At',
            'notification_type': 'Type',
            'recipient_name': 'Recipient',
            'recipient_email': 'Email',
            'Status': 'Status',
            'sent_by_name': 'Sent By',
            'delivery_count': 'DNs',
        }
        avail = [c for c in display_cols if c in history.columns]
        disp = history[avail].rename(columns=display_cols)

        # Format datetime
        if 'Sent At' in disp.columns:
            disp['Sent At'] = pd.to_datetime(disp['Sent At']).dt.strftime('%Y-%m-%d %H:%M')

        st.dataframe(disp, use_container_width=True, hide_index=True,
                      height=min(400, 40 + len(disp) * 35))