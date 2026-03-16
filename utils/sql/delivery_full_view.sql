CREATE OR REPLACE VIEW delivery_full_view AS
-- Shipment Status values:
-- DELIVERED: Đã giao hàng xong
-- PENDING: Đang chờ xử lý
-- STOCKED_OUT: Đã xuất kho
-- ON_DELIVERY: Đang giao hàng
-- DISPATCHED: Đã gửi đi
-- PARTIALLY_STOCKED_OUT: Xuất kho một phần

WITH product_total_demand AS (
    -- Tính tổng số lượng cần giao cho mỗi sản phẩm (chỉ tính những delivery chưa hoàn thành)
    -- NOTE: This is a GLOBAL calculation (all active deliveries).
    --       The UI recalculates dynamically based on filtered data.
    --       This CTE is kept for backward compatibility (email notifications, etc.)
    SELECT 
        product_id,
        SUM(IFNULL(stock_out_request_quantity, 0) - IFNULL(stock_out_quantity, 0)) AS total_remaining_demand,
        COUNT(DISTINCT delivery_id) AS active_delivery_count
    FROM stock_out_delivery_request_details sodrd
    JOIN stock_out_delivery sod ON sodrd.delivery_id = sod.id AND sod.delete_flag = 0
    WHERE sodrd.delete_flag = 0
        AND (IFNULL(sodrd.stock_out_request_quantity, 0) - IFNULL(sodrd.stock_out_quantity, 0)) > 0
        AND sod.shipment_status != 'DELIVERED'
    GROUP BY product_id
)
SELECT 
    -- 1. Delivery Info
    sod.id AS delivery_id,
    sod.dn_number,
    e.email AS created_by_email,
    CONCAT(e.first_name, ' ', e.last_name) AS created_by_name,
    DATE(sod.created_date) AS created_date,
    sod.shipment_status,
    DATE(sod.dispatch_date) AS dispatched_date,
    DATE(sod.date_delivered) AS delivered_date,
    sod.status AS sto_delivery_status,
    DATE(COALESCE(sod.adjust_etd_date, sod.etd_date)) AS sto_etd_date,
    sod.delivered AS is_delivered,
    CASE 
        WHEN sod.delivered = 1 AND sod.shipment_status != 'DELIVERED' 
            THEN 'Data Inconsistent'
        WHEN sod.delivered = 1 THEN 'Yes'
        ELSE 'No'
    END AS delivery_confirmed,
    
    -- Delivery timeline status
    CASE 
        WHEN sod.shipment_status = 'DELIVERED' THEN 'Completed'
        WHEN (IFNULL(sodrd.stock_out_request_quantity, 0) - IFNULL(sodrd.stock_out_quantity, 0)) = 0 
            AND sod.shipment_status NOT IN ('DELIVERED', 'ON_DELIVERY', 'DISPATCHED')
            THEN 'Ready to Ship'
        WHEN DATE(COALESCE(sod.adjust_etd_date, sod.etd_date)) < CURDATE() 
            AND sod.shipment_status NOT IN ('DELIVERED', 'ON_DELIVERY', 'DISPATCHED')
            AND (IFNULL(sodrd.stock_out_request_quantity, 0) - IFNULL(sodrd.stock_out_quantity, 0)) > 0
            THEN 'Overdue'
        WHEN DATE(COALESCE(sod.adjust_etd_date, sod.etd_date)) = CURDATE() 
            AND sod.shipment_status NOT IN ('DELIVERED', 'ON_DELIVERY', 'DISPATCHED')
            AND (IFNULL(sodrd.stock_out_request_quantity, 0) - IFNULL(sodrd.stock_out_quantity, 0)) > 0
            THEN 'Due Today'
        WHEN DATE(COALESCE(sod.adjust_etd_date, sod.etd_date)) > CURDATE()
            AND sod.shipment_status NOT IN ('DELIVERED', 'ON_DELIVERY', 'DISPATCHED')
            AND (IFNULL(sodrd.stock_out_request_quantity, 0) - IFNULL(sodrd.stock_out_quantity, 0)) > 0
            THEN 'On Schedule'
        WHEN sod.shipment_status IN ('ON_DELIVERY', 'DISPATCHED')
            THEN 'In Transit'
        WHEN COALESCE(sod.adjust_etd_date, sod.etd_date) IS NULL
            THEN 'No ETD'
        ELSE 'Unknown'
    END AS delivery_timeline_status,
    
    CASE 
        WHEN sod.shipment_status NOT IN ('DELIVERED', 'ON_DELIVERY', 'DISPATCHED')
            AND DATE(COALESCE(sod.adjust_etd_date, sod.etd_date)) < CURDATE()
            AND (IFNULL(sodrd.stock_out_request_quantity, 0) - IFNULL(sodrd.stock_out_quantity, 0)) > 0
            THEN DATEDIFF(CURDATE(), DATE(COALESCE(sod.adjust_etd_date, sod.etd_date)))
        ELSE NULL
    END AS days_overdue,
    sod.receiver_email_notify AS notify_email,
    sod.referencepl AS reference_packing_list,
    sod.shipping_cost,
    sod.total_weight,

    -- 2. Order Confirmation
    oc.id AS oc_id,
    oc.oc_number,
    DATE(oc.oc_date) AS oc_date,
    ocd.id AS oc_line_id,
    ocd.productpn AS oc_product_pn,
    ocd.quantity AS standard_quantity,
    ocd.selling_quantity,
    ocd.conversion AS uom_conversion,
    DATE(COALESCE(sod.adjust_etd_date, sod.etd_date)) AS etd,

    -- 3. Product Info
    p.id AS product_id,
    p.name AS product_pn,
    p.pt_code,
    p.package_size,
    b.brand_name AS brand,

    -- 4. Stock Out Request Info
    sodrd.id AS sto_dr_line_id,
    sodrd.selling_stock_out_quantity,
    sodrd.selling_stock_out_request_quantity,
    sodrd.stock_out_quantity,
    sodrd.stock_out_request_quantity,
    sodrd.stock_product_info_id AS stockin_line_id,
    sodrd.export_tax,
    
    -- Remaining quantity per line
    IFNULL(sodrd.stock_out_request_quantity, 0) - IFNULL(sodrd.stock_out_quantity, 0) AS remaining_quantity_to_deliver,

    -- 5. Warehouse & Inventory Info
    w.name AS preferred_warehouse,
    -- All inventory (including expired)
    inv_summary.total_remain AS total_instock_at_preferred_warehouse,
    inv_all_wh_summary.total_remain_all_warehouses AS total_instock_all_warehouses,
    -- Valid inventory only (excluding expired) — NEW
    inv_summary.total_remain_valid AS total_instock_at_preferred_warehouse_valid,
    inv_all_wh_summary.total_remain_all_warehouses_valid AS total_instock_all_warehouses_valid,

    -- 6. GAP Analysis — LINE-LEVEL (legacy, backward compat)
    -- NOTE: UI overrides these with dynamic calculations via fulfillment.py
    (
        IFNULL(sodrd.stock_out_request_quantity, 0) 
        - IFNULL(sodrd.stock_out_quantity, 0)
    ) - IFNULL(inv_all_wh_summary.total_remain_all_warehouses, 0) AS gap_quantity,

    ROUND(
        IFNULL(inv_all_wh_summary.total_remain_all_warehouses, 0)
        / NULLIF(
            (IFNULL(sodrd.stock_out_request_quantity, 0) - IFNULL(sodrd.stock_out_quantity, 0)), 
            0
        ) * 100,
        2
    ) AS fulfill_rate_percent,

    CASE
        WHEN sod.shipment_status = 'DELIVERED' 
            THEN 'Delivered'
        WHEN sod.shipment_status IN ('STOCKED_OUT', 'PARTIALLY_STOCKED_OUT') 
            AND (IFNULL(sodrd.stock_out_request_quantity, 0) - IFNULL(sodrd.stock_out_quantity, 0)) = 0
            THEN 'Stocked Out - Ready'
        WHEN (IFNULL(sodrd.stock_out_request_quantity, 0) - IFNULL(sodrd.stock_out_quantity, 0)) = 0 
            THEN 'No Remaining'
        WHEN inv_all_wh_summary.total_remain_all_warehouses IS NULL 
            OR inv_all_wh_summary.total_remain_all_warehouses = 0 
            THEN 'Out of Stock'
        WHEN inv_all_wh_summary.total_remain_all_warehouses 
            < (IFNULL(sodrd.stock_out_request_quantity, 0) - IFNULL(sodrd.stock_out_quantity, 0)) 
            THEN 'Partial Fulfilled'
        WHEN inv_all_wh_summary.total_remain_all_warehouses 
            >= (IFNULL(sodrd.stock_out_request_quantity, 0) - IFNULL(sodrd.stock_out_quantity, 0)) 
            THEN 'Fulfilled'
        ELSE 'Unknown'
    END AS fulfillment_status,

    -- 6.1. PRODUCT-LEVEL GAP Analysis (global, backward compat)
    -- NOTE: UI overrides these with dynamic calculations via fulfillment.py
    IFNULL(ptd.total_remaining_demand, 0) AS product_total_remaining_demand,
    IFNULL(ptd.active_delivery_count, 0) AS product_active_delivery_count,
    IFNULL(ptd.total_remaining_demand, 0) - IFNULL(inv_all_wh_summary.total_remain_all_warehouses, 0) AS product_gap_quantity,
    
    ROUND(
        IFNULL(inv_all_wh_summary.total_remain_all_warehouses, 0)
        / NULLIF(ptd.total_remaining_demand, 0) * 100,
        2
    ) AS product_fulfill_rate_percent,
    
    ROUND(
        (IFNULL(sodrd.stock_out_request_quantity, 0) - IFNULL(sodrd.stock_out_quantity, 0))
        / NULLIF(ptd.total_remaining_demand, 0) * 100,
        2
    ) AS delivery_demand_percentage,
    
    -- Shipment status Vietnamese
    CASE 
        WHEN sod.shipment_status = 'DELIVERED' THEN 'Đã giao'
        WHEN sod.shipment_status = 'ON_DELIVERY' THEN 'Đang giao'
        WHEN sod.shipment_status = 'DISPATCHED' THEN 'Đã gửi đi'
        WHEN sod.shipment_status = 'STOCKED_OUT' THEN 'Đã xuất kho'
        WHEN sod.shipment_status = 'PARTIALLY_STOCKED_OUT' THEN 'Xuất kho một phần'
        WHEN sod.shipment_status = 'PENDING' THEN 'Chờ xử lý'
        ELSE sod.shipment_status
    END AS shipment_status_vn,
    
    -- Product fulfillment status (global, backward compat)
    -- NOTE: UI overrides this with dynamic calculation via fulfillment.py
    CASE
        WHEN sod.shipment_status = 'DELIVERED' 
            THEN 'Delivered'
        WHEN (IFNULL(sodrd.stock_out_request_quantity, 0) - IFNULL(sodrd.stock_out_quantity, 0)) = 0 
            AND sod.shipment_status != 'DELIVERED'
            THEN 'Ready to Ship'
        WHEN inv_all_wh_summary.total_remain_all_warehouses IS NULL 
            OR inv_all_wh_summary.total_remain_all_warehouses = 0 
            THEN 'Out of Stock'
        WHEN inv_all_wh_summary.total_remain_all_warehouses >= IFNULL(ptd.total_remaining_demand, 0) 
            THEN 'Can Fulfill All'
        WHEN inv_all_wh_summary.total_remain_all_warehouses > 0 
            THEN 'Can Fulfill Partial'
        ELSE 'Unknown'
    END AS product_fulfillment_status,

    -- 7. Customer Info
    buyer.english_name AS customer,
    buyer.company_code AS customer_code,
    buyer.street AS customer_street,
    buyer.zip_code AS customer_zip_code,
    buyer_state.name AS customer_state_province,
    buyer_country.code AS customer_country_code,
    buyer_country.name AS customer_country_name,
    CONCAT(buyer_contact.first_name, ' ', buyer_contact.last_name) AS customer_contact,
    buyer_contact.email AS customer_contact_email,
    buyer_contact.phone AS customer_contact_phone,
    
    -- 8. Recipient Info
    ship_to_company.english_name AS recipient_company,
    ship_to_company.company_code AS recipient_company_code,
    CONCAT(ship_to_contact.first_name, ' ', ship_to_contact.last_name) AS recipient_contact,
    ship_to_contact.email AS recipient_contact_email,
    ship_to_contact.phone AS recipient_contact_phone,
    sod.ship_to AS recipient_address,
    ship_to_state.name AS recipient_state_province,
    ship_to_country.code AS recipient_country_code,
    ship_to_country.name AS recipient_country_name,
    
    -- EPE check
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM companies_company_types cct
            JOIN company_types ct ON cct.company_type_id = ct.id
            WHERE cct.companies_id = buyer.id 
              AND ct.name = 'EPE Company'
        ) THEN 'Yes'
        ELSE 'No'
    END AS is_epe_company,

    -- 9. Financial Info
    CONCAT(sod.intl_charge, ' ', ic.code) AS intl_charge,
    CONCAT(sod.local_charge, ' ', lc.code) AS local_charge,

    -- 10. Legal Entity
    seller.english_name AS legal_entity,
    seller.company_code AS legal_entity_code,
    seller_state.name AS legal_entity_state_province,
    seller_country.code AS legal_entity_country_code,
    seller_country.name AS legal_entity_country_name

FROM stock_out_delivery_request_details sodrd

LEFT JOIN stock_out_delivery sod 
    ON sodrd.delivery_id = sod.id AND sod.delete_flag = 0

LEFT JOIN order_confirmations oc 
    ON sodrd.order_confirmation_id = oc.id AND oc.delete_flag = 0

LEFT JOIN order_comfirmation_details ocd 
    ON sodrd.oc_detail_id = ocd.id AND ocd.delete_flag = 0

LEFT JOIN products p ON sodrd.product_id = p.id
LEFT JOIN brands b ON p.brand_id = b.id

LEFT JOIN product_total_demand ptd ON ptd.product_id = sodrd.product_id

-- ── Inventory subqueries (with valid/expired split) ─────────────

LEFT JOIN (
    SELECT 
        warehouse_id, 
        product_id, 
        SUM(remain) AS total_remain,
        SUM(CASE 
            WHEN expired_date IS NULL OR expired_date > CURDATE() 
            THEN remain ELSE 0 
        END) AS total_remain_valid
    FROM inventory_histories
    WHERE delete_flag = 0
    GROUP BY warehouse_id, product_id
) inv_summary 
    ON inv_summary.warehouse_id = sod.preference_warehouse_id
    AND inv_summary.product_id = sodrd.product_id

LEFT JOIN (
    SELECT 
        product_id, 
        SUM(remain) AS total_remain_all_warehouses,
        SUM(CASE 
            WHEN expired_date IS NULL OR expired_date > CURDATE() 
            THEN remain ELSE 0 
        END) AS total_remain_all_warehouses_valid
    FROM inventory_histories
    WHERE delete_flag = 0
    GROUP BY product_id
) inv_all_wh_summary 
    ON inv_all_wh_summary.product_id = sodrd.product_id

-- Warehouse
LEFT JOIN warehouses w ON sod.preference_warehouse_id = w.id

-- Buyer/Customer
LEFT JOIN companies buyer ON sod.buyer_company_id = buyer.id
LEFT JOIN states buyer_state ON buyer.state_province_id = buyer_state.id
LEFT JOIN countries buyer_country ON buyer.country_id = buyer_country.id
LEFT JOIN contacts buyer_contact ON sod.buyer_recipient_id = buyer_contact.id

-- Ship-To/Recipient
LEFT JOIN companies ship_to_company ON sod.ship_to_company_id = ship_to_company.id
LEFT JOIN states ship_to_state ON ship_to_company.state_province_id = ship_to_state.id
LEFT JOIN countries ship_to_country ON ship_to_company.country_id = ship_to_country.id
LEFT JOIN contacts ship_to_contact ON sod.ship_to_contact_id = ship_to_contact.id

-- Other
LEFT JOIN employees e ON sod.created_by = e.keycloak_id
LEFT JOIN currencies ic ON sod.intl_currency_id = ic.id
LEFT JOIN currencies lc ON sod.local_currency_id = lc.id

-- Legal Entity (Seller)
LEFT JOIN companies seller ON sod.seller_company_id = seller.id
LEFT JOIN states seller_state ON seller.state_province_id = seller_state.id
LEFT JOIN countries seller_country ON seller.country_id = seller_country.id

WHERE sodrd.delete_flag = 0

ORDER BY sodrd.id DESC;
