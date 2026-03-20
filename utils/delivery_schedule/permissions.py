# utils/delivery_schedule/permissions.py
"""Centralized permission definitions for Delivery Schedule module.

All role checks across the module import from here.
To add a new role or change access rules, edit ONLY this file.

Known roles (from users.role column):
  admin, GM, MD, sales_manager, sales, supply_chain_manager,
  outbound_manager, inbound_manager, supply_chain, warehouse_manager,
  buyer, allocator, customer, vendor, viewer
"""

import streamlit as st

# ── Super role — bypasses all permission checks ─────────────────
ROLE_ADMIN = 'admin'

# ── Role groups ──────────────────────────────────────────────────
# Each set lists the roles that have a specific capability.
# Note: 'admin' is NOT listed here — it bypasses via _is_admin().

ROLES_EDIT_ETD = {
    'supply_chain_manager',
    'outbound_manager',
    'supply_chain',
}

ROLES_SEND_EMAIL = {
    'supply_chain_manager',
    'outbound_manager',
    'supply_chain',
    'sales_manager',
    'GM',
    'MD',
}

ROLES_EXPORT = {
    'supply_chain_manager',
    'outbound_manager',
    'supply_chain',
    'sales_manager',
    'sales',
    'inbound_manager',
    'warehouse_manager',
    'GM',
    'MD',
}

ROLES_WRITE_DB = {
    'supply_chain_manager',
    'outbound_manager',
    'supply_chain',
}


# ── Helpers ──────────────────────────────────────────────────────

def get_user_role() -> str:
    """Return the current user's role from session state."""
    return st.session_state.get('user_role', '')


def _is_admin() -> bool:
    """Admin role bypasses all permission checks."""
    return get_user_role() == ROLE_ADMIN


def can_edit_etd() -> bool:
    """Can the current user edit ETD dates?"""
    return _is_admin() or get_user_role() in ROLES_EDIT_ETD


def can_send_email() -> bool:
    """Can the current user send email notifications?"""
    return _is_admin() or get_user_role() in ROLES_SEND_EMAIL


def can_export() -> bool:
    """Can the current user download / export data?"""
    return _is_admin() or get_user_role() in ROLES_EXPORT


def can_write_db() -> bool:
    """Can the current user perform write operations (update/delete)?"""
    return _is_admin() or get_user_role() in ROLES_WRITE_DB