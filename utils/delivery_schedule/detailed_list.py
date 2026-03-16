# utils/delivery_schedule/detailed_list.py
"""Detailed delivery list with inline ETD editing (single & bulk).

Features:
  • Read-only dataframe with native column visibility (unchanged).
  • Single ETD edit via st.data_editor — user clicks the ETD cell.
  • Bulk ETD update — select multiple DNs, set one new date.
  • On save → DB update → email notification → cache invalidation.

Email notification:
  TO  : creator (created_by_email of each affected DN)
  CC  : current user + dn_update@prostech.vn
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


# ── User-friendly column labels ──────────────────────────────────

COLUMN_LABELS = {
    'dn_number':                          'DN Number',
    'delivery_id':                        'Delivery ID',
    'customer':                           'Customer',
    'recipient_company':                  'Ship-To Company',
    'recipient_state_province':           'State/Province',
    'recipient_country_name':             'Country',
    'etd':                                'ETD',
    'pt_code':                            'PT Code',
    'product_pn':                         'Product Name',
    'product_id':                         'Product ID',
    'brand':                              'Brand',
    'package_size':                       'Package Size',
    'standard_quantity':                  'Std Qty',
    'selling_quantity':                   'Selling Qty',
    'remaining_quantity_to_deliver':      'Remaining Qty',
    'stock_out_quantity':                 'Stock Out Qty',
    'stock_out_request_quantity':         'Stock Out Request Qty',
    'total_instock_at_preferred_warehouse': 'In-Stock (Preferred WH)',
    'total_instock_all_warehouses':       'In-Stock (All WH)',
    'gap_quantity':                       'Gap Qty',
    'product_gap_quantity':               'Product Gap Qty',
    'product_total_remaining_demand':     'Total Remaining Demand',
    'product_fulfill_rate_percent':       'Fulfill Rate %',
    'fulfill_rate_percent':               'Line Fulfill %',
    'delivery_demand_percentage':         'Demand %',
    'delivery_timeline_status':           'Timeline Status',
    'days_overdue':                       'Days Overdue',
    'shipment_status':                    'Shipment Status',
    'product_fulfillment_status':         'Fulfillment Status',
    'is_epe_company':                     'EPE Company',
    'legal_entity':                       'Legal Entity',
    'created_by_name':                    'Creator/Sales',
    'created_date':                       'Created Date',
    'delivered_date':                     'Delivered Date',
    'dispatched_date':                    'Dispatched Date',
    'preferred_warehouse':                'Preferred WH',
    'shipping_cost':                      'Shipping Cost',
    'export_tax':                         'Export Tax',
    'customer_country_code':              'Customer Country',
    'legal_entity_country_code':          'Entity Country',
}

# Columns visible by default (order matters)
DEFAULT_COLUMNS = [
    'dn_number', 'customer', 'recipient_company', 'etd',
    'pt_code', 'product_pn', 'brand', 'standard_quantity',
    'remaining_quantity_to_deliver', 'product_fulfill_rate_percent',
    'delivery_timeline_status', 'days_overdue', 'shipment_status',
    'product_fulfillment_status', 'is_epe_company',
]


@st.fragment
def display_detailed_list(df, data_loader=None, email_sender=None):
    """Display detailed delivery list with ETD editing capability.

    Parameters
    ----------
    df : DataFrame
        Filtered delivery data.
    data_loader : DeliveryDataLoader, optional
        Needed for ETD update DB operations.
    email_sender : EmailSender, optional
        Needed for sending ETD change notifications.
    """
    st.subheader("📋 Detailed Delivery List")

    # ── Prepare display data ─────────────────────────────────────
    display_df = df.copy()

    # Keep etd as date for the editor
    if 'etd' in display_df.columns:
        display_df['etd'] = pd.to_datetime(display_df['etd'], errors='coerce').dt.date

    # Format other date columns to string
    other_date_cols = ['created_date', 'delivered_date', 'dispatched_date']
    for col in other_date_cols:
        if col in display_df.columns:
            display_df[col] = pd.to_datetime(
                display_df[col], errors='coerce'
            ).dt.strftime('%Y-%m-%d')

    # ── Check if editing is allowed ──────────────────────────────
    can_edit = (
        data_loader is not None
        and email_sender is not None
        and st.session_state.get('user_role', '') in (
            'admin', 'manager', 'logistics_manager', 'supply_chain', 'sales',
        )
    )

    if can_edit:
        _display_editable_table(display_df, data_loader, email_sender)
    else:
        _display_readonly_table(display_df)


# ── Read-only table (original behaviour) ─────────────────────────

def _display_readonly_table(display_df):
    """Render the table without editing capability."""
    if 'etd' in display_df.columns:
        display_df = display_df.copy()
        display_df['etd'] = display_df['etd'].astype(str)

    column_config = _build_column_config(display_df, editable=False)
    col_order = [c for c in DEFAULT_COLUMNS if c in display_df.columns]

    st.dataframe(
        display_df,
        column_order=col_order,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=min(700, 50 + len(display_df) * 35),
    )


# ── Editable table + bulk update ─────────────────────────────────

def _display_editable_table(display_df, data_loader, email_sender):
    """Render the table with editable ETD + bulk update section."""

    edit_tab, bulk_tab = st.tabs(["✏️ Inline Edit", "📦 Bulk Update ETD"])

    # ━━━━ Tab 1: Inline Edit via data_editor ━━━━━━━━━━━━━━━━━━━━
    with edit_tab:
        st.caption(
            "Click any **ETD** cell to change the date, then press "
            "**💾 Save ETD Changes** below."
        )

        original_etd = display_df[['delivery_id', 'dn_number', 'etd']].copy()

        column_config = _build_column_config(display_df, editable=True)
        col_order = [c for c in DEFAULT_COLUMNS if c in display_df.columns]

        edited_df = st.data_editor(
            display_df,
            column_order=col_order,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            height=min(700, 50 + len(display_df) * 35),
            key="etd_editor",
            num_rows="fixed",
        )

        changes = _detect_etd_changes(original_etd, edited_df)

        if changes:
            st.info(f"📝 **{len(changes)}** ETD change(s) detected")
            _show_changes_preview(changes)

            if st.button(
                "💾 Save ETD Changes & Send Notification",
                type="primary",
                key="save_inline_etd",
            ):
                _execute_etd_updates(changes, display_df, data_loader, email_sender)

    # ━━━━ Tab 2: Bulk Update ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with bulk_tab:
        _display_bulk_update(display_df, data_loader, email_sender)


def _display_bulk_update(display_df, data_loader, email_sender):
    """Bulk ETD update — select multiple DNs, set one new date."""

    st.caption("Select deliveries and set a new ETD for all of them at once.")

    dn_options = (
        display_df[['dn_number', 'delivery_id', 'customer', 'etd']]
        .drop_duplicates(subset='delivery_id')
        .sort_values('dn_number')
    )
    dn_display_map = {}
    for _, row in dn_options.iterrows():
        label = f"{row['dn_number']}  ·  {row['customer']}  ·  ETD: {row['etd']}"
        dn_display_map[label] = row['delivery_id']

    col1, col2 = st.columns([3, 1])

    with col1:
        selected_labels = st.multiselect(
            "Select Deliveries",
            options=list(dn_display_map.keys()),
            placeholder="Choose DNs to update…",
            key="bulk_dn_select",
        )

    with col2:
        new_etd = st.date_input(
            "New ETD",
            value=datetime.now().date(),
            key="bulk_new_etd",
        )

    if not selected_labels:
        return

    selected_ids = [dn_display_map[lbl] for lbl in selected_labels]
    changes = []
    for did in selected_ids:
        rows = display_df[display_df['delivery_id'] == did]
        if rows.empty:
            continue
        row = rows.iloc[0]
        old_etd = row['etd']
        if old_etd == new_etd:
            continue
        changes.append({
            'delivery_id': did,
            'dn_number': row['dn_number'],
            'customer': row.get('customer', ''),
            'recipient_company': row.get('recipient_company', ''),
            'old_etd': old_etd,
            'new_etd': new_etd,
        })

    if not changes:
        st.warning("No ETD changes — the selected DNs already have this date.")
        return

    st.info(f"📝 **{len(changes)}** delivery(ies) will be updated to **{new_etd}**")
    _show_changes_preview(changes)

    col_btn, col_reason = st.columns([1, 2])
    with col_reason:
        reason = st.text_input(
            "Reason for change (optional)",
            placeholder="e.g. Customer requested reschedule",
            key="bulk_etd_reason",
        )
    with col_btn:
        st.markdown("")  # spacer
        if st.button(
            "💾 Apply Bulk Update & Notify",
            type="primary",
            key="save_bulk_etd",
        ):
            _execute_etd_updates(
                changes, display_df, data_loader, email_sender, reason=reason,
            )


# ── Helpers ──────────────────────────────────────────────────────

def _detect_etd_changes(original_etd, edited_df):
    """Compare original ETD with edited DataFrame, return list of dicts."""
    changes = []
    for idx in original_etd.index:
        if idx not in edited_df.index:
            continue
        old = original_etd.at[idx, 'etd']
        new = edited_df.at[idx, 'etd']
        if isinstance(new, datetime):
            new = new.date()
        if isinstance(old, datetime):
            old = old.date()
        if pd.isna(old) and pd.isna(new):
            continue
        if old != new:
            changes.append({
                'delivery_id': edited_df.at[idx, 'delivery_id'],
                'dn_number': edited_df.at[idx, 'dn_number'],
                'customer': edited_df.at[idx, 'customer'] if 'customer' in edited_df.columns else '',
                'recipient_company': edited_df.at[idx, 'recipient_company'] if 'recipient_company' in edited_df.columns else '',
                'old_etd': old,
                'new_etd': new,
            })
    # Deduplicate by delivery_id (multiple lines per DN)
    seen = set()
    unique_changes = []
    for c in changes:
        if c['delivery_id'] not in seen:
            seen.add(c['delivery_id'])
            unique_changes.append(c)
    return unique_changes


def _show_changes_preview(changes):
    """Display a compact preview table of pending ETD changes."""
    preview = pd.DataFrame(changes)
    preview = preview.rename(columns={
        'dn_number': 'DN Number',
        'customer': 'Customer',
        'recipient_company': 'Ship To',
        'old_etd': 'Current ETD',
        'new_etd': 'New ETD',
    })
    display_cols = [c for c in ['DN Number', 'Customer', 'Ship To', 'Current ETD', 'New ETD']
                    if c in preview.columns]
    st.dataframe(
        preview[display_cols],
        use_container_width=True,
        hide_index=True,
    )


def _execute_etd_updates(changes, display_df, data_loader, email_sender, reason=""):
    """Write ETD changes to DB, send email, clear cache."""
    current_user = st.session_state.get('user_fullname', 'System')
    current_email = st.session_state.get('user_email', '')

    success_count = 0
    errors = []

    with st.spinner("Updating ETD in database…"):
        for ch in changes:
            ok, msg = data_loader.update_delivery_etd(
                delivery_id=ch['delivery_id'],
                new_etd=ch['new_etd'],
                updated_by=current_user,
                reason=reason,
            )
            if ok:
                success_count += 1
            else:
                errors.append(f"{ch['dn_number']}: {msg}")

    if success_count > 0:
        st.success(f"✅ Updated ETD for {success_count}/{len(changes)} deliveries")

        with st.spinner("Sending email notifications…"):
            _send_etd_notifications(
                changes, display_df, email_sender,
                current_user, current_email, reason,
            )

        # Clear cache so next load picks up new ETD
        data_loader.load_base_data.clear()

    if errors:
        st.error("Some updates failed:\n" + "\n".join(errors))

    # Auto-rerun only when ALL succeeded — otherwise let user see errors
    if success_count > 0 and not errors:
        st.rerun()


def _send_etd_notifications(changes, display_df, email_sender,
                             updated_by_name, updated_by_email, reason):
    """Send ETD change email grouped by creator.

    TO  : creator (created_by_email)
    CC  : user who made the change + dn_update@prostech.vn
    """
    GROUP_CC = "dn_update@prostech.vn"

    creator_groups = {}
    for ch in changes:
        rows = display_df[display_df['delivery_id'] == ch['delivery_id']]
        if rows.empty:
            continue
        creator_email = rows.iloc[0].get('created_by_email', '')
        creator_name = rows.iloc[0].get('created_by_name', 'Team')
        if not creator_email:
            continue
        creator_groups.setdefault(creator_email, {
            'name': creator_name,
            'changes': [],
        })['changes'].append(ch)

    for creator_email, info in creator_groups.items():
        cc_list = [GROUP_CC]
        if updated_by_email and updated_by_email != creator_email:
            cc_list.append(updated_by_email)

        try:
            ok, msg = email_sender.send_etd_update_notification(
                to_email=creator_email,
                to_name=info['name'],
                changes=info['changes'],
                updated_by_name=updated_by_name,
                updated_by_email=updated_by_email,
                cc_emails=cc_list,
                reason=reason,
            )
            if ok:
                st.toast(f"📧 Notified {info['name']} ({creator_email})")
            else:
                st.warning(f"Failed to email {creator_email}: {msg}")
        except Exception as e:
            logger.error(f"ETD notification error for {creator_email}: {e}")
            st.warning(f"Email error for {creator_email}: {e}")


# ── Column config builder ────────────────────────────────────────

def _build_column_config(df, editable=False):
    """Build st.column_config dict with proper types, labels, and formats."""

    quantity_cols = {
        'standard_quantity', 'selling_quantity', 'remaining_quantity_to_deliver',
        'stock_out_quantity', 'stock_out_request_quantity',
        'total_instock_at_preferred_warehouse', 'total_instock_all_warehouses',
        'gap_quantity', 'product_gap_quantity', 'product_total_remaining_demand',
    }
    rate_cols = {
        'product_fulfill_rate_percent', 'fulfill_rate_percent',
        'delivery_demand_percentage',
    }
    currency_cols = {'shipping_cost', 'export_tax'}

    config = {}

    for col in df.columns:
        label = COLUMN_LABELS.get(col, col.replace('_', ' ').title())

        if col == 'etd' and editable:
            config[col] = st.column_config.DateColumn(
                label,
                help="Click to change ETD",
            )
            continue

        if col in quantity_cols:
            config[col] = st.column_config.NumberColumn(
                label, format="%,.0f", disabled=True,
            )
        elif col in rate_cols:
            config[col] = st.column_config.ProgressColumn(
                label, format="%.1f%%", min_value=0, max_value=100,
            )
        elif col in currency_cols:
            config[col] = st.column_config.NumberColumn(
                label, format="%,.2f", disabled=True,
            )
        elif col == 'days_overdue':
            config[col] = st.column_config.NumberColumn(
                label, format="%,.0f", disabled=True,
            )
        else:
            config[col] = st.column_config.TextColumn(label, disabled=True)

    return config