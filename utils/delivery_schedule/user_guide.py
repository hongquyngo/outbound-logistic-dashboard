# utils/delivery_schedule/user_guide.py
"""User guide popover for Delivery Schedule module.

Renders a ❓ button next to the page title that opens a multi-tab
guide dialog covering:
  1. Hướng dẫn sử dụng (Getting Started)
  2. Tài liệu tra cứu (Reference)
  3. Thuật ngữ & Công thức (Glossary)
  4. Câu hỏi thường gặp (FAQ)
"""

import streamlit as st


def render_user_guide():
    """Render the ❓ help button + popover guide next to the page title.

    Call this immediately after st.title().
    """

    @st.dialog("📖 Hướng dẫn sử dụng — Delivery Schedule", width="large")
    def _guide_dialog():
        tab1, tab2, tab3, tab4 = st.tabs([
            "🚀 Bắt đầu",
            "📚 Tra cứu",
            "📐 Thuật ngữ & Công thức",
            "❓ Câu hỏi thường gặp",
        ])

        with tab1:
            _tab_getting_started()
        with tab2:
            _tab_reference()
        with tab3:
            _tab_glossary()
        with tab4:
            _tab_faq()

    if st.button("❓ Hướng dẫn", key="_user_guide_btn", type="tertiary"):
        _guide_dialog()


# ═════════════════════════════════════════════════════════════════
# TAB 1 — Bắt đầu (Getting Started)
# ═════════════════════════════════════════════════════════════════

def _tab_getting_started():
    st.markdown("""
### 👋 Chào mừng đến Delivery Schedule

Module này giúp bạn **theo dõi toàn bộ tiến trình giao hàng** — từ lúc tạo Delivery Note (DN)
đến khi hàng được giao đến khách hàng.

---

### 🔄 Quy trình giao hàng tổng quan

```
Tạo DN → Xuất kho (Stock Out) → Gửi hàng (Dispatch) → Giao hàng (Deliver) → Hoàn tất
```

Mỗi DN chứa nhiều **dòng sản phẩm** (line items). Mỗi dòng có số lượng
yêu cầu xuất kho riêng, và hệ thống theo dõi tiến độ xuất kho theo từng dòng.

---

### ⚡ Bắt đầu nhanh trong 3 bước

**Bước 1 — Chọn khoảng thời gian**

Chọn preset ở ô **📅 Date Range** (mặc định: This Week). Chọn "Custom" để nhập ngày tùy ý.

**Bước 2 — Lọc dữ liệu**

Điền các bộ lọc trong form (Customer, Product, Brand…) rồi nhấn **🔄 Apply Filters**.

> 💡 **Mẹo:** Mỗi bộ lọc có checkbox **Excl** bên phải — tick vào để **loại trừ** các mục đã chọn
> thay vì chỉ hiện chúng.

**Bước 3 — Xem kết quả**

Kết quả hiển thị qua 3 tab:

| Tab | Mô tả |
|-----|-------|
| 📊 **Pivot Table** | Bảng tổng hợp linh hoạt — chọn trục hàng/cột/giá trị tùy ý |
| 📋 **Detailed List** | Danh sách chi tiết từng dòng sản phẩm, có thể sửa ETD trực tiếp |
| 📧 **Email Notifications** | Gửi email thông báo lịch giao hàng cho Sales/Khách hàng/Nhóm email |

---

### ✏️ Cách sửa ETD (Ngày giao dự kiến)

Trong tab **📋 Detailed List**:

1. **Inline Edit** — Click vào ô ETD của bất kỳ dòng nào → chọn ngày mới → tất cả dòng cùng DN sẽ tự động cập nhật vào vùng staging bên dưới → nhấn **💾 Save & Notify**

2. **Bulk Update** — Chọn nhiều DN cùng lúc → đặt 1 ngày ETD chung → nhấn **💾 Apply Bulk Update**

3. **ETD History** — Xem lịch sử thay đổi ETD: chọn DN hoặc tick "Show all" → hiện bảng (ai sửa, lúc nào, ETD cũ → mới, lý do)

> 💡 Khi staging thay đổi ETD (cả inline lẫn bulk), hệ thống cũng hiện lịch sử thay đổi trước đó cho DN đang sửa — giúp bạn biết DN này đã bị đổi ETD bao nhiêu lần.

> ⚠️ Khi lưu, hệ thống sẽ tự động gửi email thông báo đến người tạo DN (Creator/Sales).

---

### 📧 Cách gửi Email Notifications

Trong tab **📧 Email Notifications**:

**Bước 1 — Chọn loại thông báo:** Delivery Schedule / Overdue Alerts / Custom Clearance

**Bước 2 — Chọn người nhận (TO):**

| Loại | Cách chọn |
|------|-----------|
| **Sales/Creators** | Chọn từ danh sách sales có DN active |
| **Customers** | Chọn công ty → chọn contact person |
| **Custom** | Chọn từ danh sách nhân viên, nhóm email, hoặc nhập email thủ công |
| **Customs Clearance** | Chọn từ nhóm email / nhân viên / nhập thủ công |

**Bước 3 — Chọn CC:** Chọn nhân viên, nhóm email, hoặc nhập thủ công. Manager có thể tự động CC.

**Bước 4 — Preview:** Nhấn **👁️ Preview** để xem nội dung email thực tế trước khi gửi.

**Bước 5 — Gửi:** Tick xác nhận → nhấn **🚀 Send Now** (hoặc nhấn **👁️ Preview** để xem trước)

> 💡 **Email History:** Mục **📜 Email History** ở đầu tab hiển thị 30 email gần nhất đã gửi.
> Hệ thống cũng cảnh báo nếu bạn gửi trùng cho cùng người nhận trong ngày.
""")

    st.info(
        "💡 **Filter Presets:** Bạn có thể lưu bộ lọc hiện tại thành file JSON "
        "để import lại sau — xem mục **💾 Filter Presets** bên dưới form lọc."
    )


# ═════════════════════════════════════════════════════════════════
# TAB 2 — Tra cứu (Reference)
# ═════════════════════════════════════════════════════════════════

def _tab_reference():
    st.markdown("### 📚 Tài liệu tra cứu")

    # ── KPI Cards ────────────────────────────────────────────────
    st.markdown("#### 📊 Các chỉ số KPI (thanh số liệu phía trên)")
    st.markdown("""
| Chỉ số | Nguồn dữ liệu | Ý nghĩa |
|--------|---------------|---------|
| **Deliveries** | Dữ liệu đã lọc | Số DN duy nhất trong kết quả lọc |
| **Line Items** | Dữ liệu đã lọc | Tổng số dòng sản phẩm |
| **Pending Qty** | Dữ liệu đã lọc | Tổng số lượng chờ xuất kho |
| **⚠️ Overdue** | **Toàn bộ** dữ liệu active | Số DN đã quá hạn (không bị ảnh hưởng bởi filter) |
| **Avg Fulfill %** | Dữ liệu đã lọc | Trung bình tỷ lệ đáp ứng tồn kho theo sản phẩm |
| **Out of Stock** | Dữ liệu đã lọc | Số sản phẩm hết hàng hoàn toàn |

> 📌 **Lưu ý:** Chỉ số **Overdue** luôn phản ánh toàn bộ DN active, không bị ảnh hưởng bởi
> bộ lọc hiện tại. Click vào "⚠️ View overdue details" để xem chi tiết.
""")

    # ── Column definitions ───────────────────────────────────────
    st.markdown("#### 📋 Các cột dữ liệu chính")

    st.markdown("**Thông tin giao hàng:**")
    st.markdown("""
| Cột | Ý nghĩa |
|-----|---------|
| **DN Number** | Mã phiếu giao hàng (Delivery Note) |
| **Customer** | Công ty mua hàng (Sold-To) |
| **Ship-To Company** | Công ty nhận hàng (có thể khác Customer) |
| **ETD** | Ngày giao hàng dự kiến (Estimated Time of Delivery) |
| **Creator/Sales** | Nhân viên tạo DN / phụ trách bán hàng |
| **Shipment Status** | Trạng thái vận chuyển hiện tại |
| **Timeline Status** | Trạng thái tiến độ so với ETD |
| **Days Overdue** | Số ngày quá hạn (chỉ hiện khi Overdue) |
""")

    st.markdown("**Tiến độ xuất kho:**")
    st.markdown("""
| Cột | Ý nghĩa |
|-----|---------|
| **Requested Qty** | Số lượng yêu cầu xuất kho cho dòng này |
| **Issued Qty** | Số lượng đã xuất kho thực tế |
| **Pending Qty** | Số lượng chờ xuất = Requested − Issued |
| **Issued %** | Tiến độ xuất kho = Issued ÷ Requested × 100% |
""")

    st.markdown("**Tồn kho & Đáp ứng:**")
    st.markdown("""
| Cột | Ý nghĩa |
|-----|---------|
| **In-Stock (Preferred WH)** | Tồn kho tại kho ưu tiên của DN |
| **In-Stock (All WH)** | Tồn kho tại tất cả kho |
| **Gap Qty** | Thiếu hụt = Pending Qty − Tồn kho (dương = thiếu) |
| **Fulfill Rate %** | Tỷ lệ đáp ứng = Tồn kho ÷ Tổng nhu cầu × 100% |
| **Fulfillment Status** | Trạng thái đáp ứng của sản phẩm |
""")

    # ── Status definitions ───────────────────────────────────────
    st.markdown("#### 🚦 Giải thích trạng thái")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Shipment Status (Trạng thái vận chuyển):**")
        st.markdown("""
| Trạng thái | Tiếng Việt | Mô tả |
|-----------|-----------|-------|
| `PENDING` | Chờ xử lý | DN mới tạo, chưa xử lý |
| `PARTIALLY_STOCKED_OUT` | Xuất kho một phần | Đã xuất một số dòng |
| `STOCKED_OUT` | Đã xuất kho | Tất cả dòng đã xuất xong |
| `DISPATCHED` | Đã gửi đi | Hàng đã rời kho |
| `ON_DELIVERY` | Đang giao | Hàng đang trên đường |
| `DELIVERED` | Đã giao | Giao hàng hoàn tất |
""")

    with col2:
        st.markdown("**Timeline Status (Trạng thái tiến độ):**")
        st.markdown("""
| Trạng thái | Điều kiện |
|-----------|----------|
| 🟢 `On Schedule` | ETD > Hôm nay, còn hàng chờ xuất |
| 🟡 `Due Today` | ETD = Hôm nay, còn hàng chờ xuất |
| 🔴 `Overdue` | ETD < Hôm nay, còn hàng chờ xuất |
| 🔵 `In Transit` | Đang giao / đã gửi đi |
| ✅ `Ready to Ship` | Xuất kho xong, chờ gửi |
| ⬜ `Completed` | Đã giao xong |
| ⚫ `No ETD` | Chưa có ngày ETD |
""")

    st.markdown("**Fulfillment Status (Trạng thái đáp ứng):**")
    st.markdown("""
| Trạng thái | Điều kiện |
|-----------|----------|
| 🟢 `Can Fulfill All` | Tồn kho ≥ Tổng nhu cầu sản phẩm |
| 🟡 `Can Fulfill Partial` | Tồn kho > 0 nhưng < Tổng nhu cầu |
| 🔴 `Out of Stock` | Tồn kho = 0 |
""")

    # ── Filter reference ─────────────────────────────────────────
    st.markdown("#### 🔍 Bộ lọc")
    st.markdown("""
| Bộ lọc | Include mode (mặc định) | Exclude mode (tick Excl) |
|--------|------------------------|-------------------------|
| **Timeline Status** | Chỉ hiện trạng thái đã chọn | Ẩn trạng thái đã chọn |
| **Customer** | Chỉ hiện khách hàng đã chọn | Ẩn khách hàng đã chọn |
| **Product** | Chỉ hiện sản phẩm đã chọn | Ẩn sản phẩm đã chọn |
| *Các bộ lọc khác* | *Tương tự...* | *Tương tự...* |
| **EPE Company** | Radio: All / EPE Only / Non-EPE | — |
| **Customer Type** | Radio: All / Foreign / Domestic | — |
| **📦 Include expired stock** | Tính cả hàng hết hạn vào tồn kho | Chỉ tính hàng còn hạn |

> ⚠️ Mặc định, bộ lọc **Timeline Status** đã chọn sẵn "Completed" ở chế độ **Exclude**
> → tức là ẩn các DN đã hoàn tất, chỉ hiện DN active.
""")

    # ── Permissions ──────────────────────────────────────────────
    st.markdown("#### 🔐 Phân quyền")
    st.markdown("""
| Chức năng | Role được phép |
|-----------|---------------|
| **Xem dữ liệu** | Tất cả role đã đăng nhập |
| **Sửa ETD** | `admin`, `supply_chain_manager`, `outbound_manager`, `supply_chain` |
| **Gửi email** | `admin`, `supply_chain_manager`, `outbound_manager`, `supply_chain`, `sales_manager`, `GM`, `MD` |
| **Export CSV** | `admin`, `supply_chain_manager`, `outbound_manager`, `supply_chain`, `sales_manager`, `sales`, `inbound_manager`, `warehouse_manager`, `GM`, `MD` |
| **Ghi dữ liệu (DB)** | `admin`, `supply_chain_manager`, `outbound_manager`, `supply_chain` |

> 📌 Role **admin** có toàn quyền — không bị hạn chế bởi bất kỳ rule nào.
""")

    # ── Email Features ───────────────────────────────────────────
    st.markdown("#### 📧 Tính năng Email")
    st.markdown("""
| Tính năng | Mô tả |
|-----------|-------|
| **Email History** | Xem 30 email gần nhất đã gửi (📜 phía trên tab Email) |
| **Duplicate Warning** | Cảnh báo khi gửi trùng cho cùng người nhận + cùng loại trong ngày |
| **HTML Preview** | Xem nội dung email thực tế trước khi gửi |
| **Employee Picker** | Chọn TO/CC từ danh sách nhân viên (có tìm kiếm) |
| **Email Group** | Chọn TO/CC từ nhóm email đã tạo sẵn (VD: Customs Team, Outbound Team) |
| **Additional Manual** | Nhập thêm email thủ công cho TO/CC |
| **Manager Auto-CC** | Tự động CC manager khi gửi cho Sales/Creator |
| **Audit Log** | Mỗi email gửi đều ghi log vào DB (ai gửi, gửi cho ai, khi nào, kết quả) |
""")

    # ── Email types ──────────────────────────────────────────────
    st.markdown("#### 📨 Các loại email")
    st.markdown("""
| Loại | Nội dung | Attachment |
|------|---------|-----------|
| **📅 Delivery Schedule** | Lịch giao hàng theo tuần, fulfillment status | Excel + ICS Calendar |
| **🚨 Overdue Alerts** | DN quá hạn + due today, yêu cầu hành động khẩn | Excel |
| **🛃 Custom Clearance** | Lịch thông quan EPE + nước ngoài, checklist giấy tờ | Excel |
| **📅 ETD Update** | Thông báo ETD đã thay đổi (tự động khi sửa ETD) | — |
""")


# ═════════════════════════════════════════════════════════════════
# TAB 3 — Thuật ngữ & Công thức (Glossary)
# ═════════════════════════════════════════════════════════════════

def _tab_glossary():
    st.markdown("### 📐 Thuật ngữ & Công thức")

    # ── Core terms ───────────────────────────────────────────────
    st.markdown("#### 📦 Quy trình xuất kho")
    st.markdown("""
```
┌──────────────────────────────────────────────────────────────┐
│  Requested Qty          Issued Qty          Pending Qty      │
│  (Yêu cầu xuất)   →   (Đã xuất)      →   (Chờ xuất)       │
│                                                              │
│  stock_out_request      stock_out           remaining        │
│  _quantity              _quantity            _quantity        │
│                                             _to_deliver      │
│                                                              │
│  Pending Qty = Requested Qty − Issued Qty                    │
│  Issued %    = Issued Qty ÷ Requested Qty × 100%            │
└──────────────────────────────────────────────────────────────┘
```

| Ý nghĩa | Khi nào = 0? |
|----------|-------------|
| **Pending Qty = 0** | Đã xuất kho **đủ** số lượng yêu cầu → sẵn sàng gửi hàng |
| **Issued Qty = 0** | Chưa xuất kho dòng nào → cần xử lý |
| **Issued % = 100%** | Hoàn tất xuất kho cho dòng này |
""")

    # ── Fulfillment formulas ─────────────────────────────────────
    st.markdown("#### 📊 Công thức Fulfillment (Đáp ứng tồn kho)")
    st.markdown("""
Fulfillment đo lường khả năng đáp ứng nhu cầu giao hàng **bằng hàng tồn kho hiện có**.

**Cấp dòng (Line-level):**
```
Gap Qty         = Pending Qty − Tồn kho (All WH)
Fulfill Rate %  = Tồn kho (All WH) ÷ Pending Qty × 100%
```

**Cấp sản phẩm (Product-level):**
```
Total Demand         = Tổng Pending Qty của TẤT CẢ DN active cho sản phẩm này
Product Gap Qty      = Total Demand − Tồn kho (All WH)
Product Fulfill %    = Tồn kho (All WH) ÷ Total Demand × 100%
Demand %             = Pending Qty dòng này ÷ Total Demand × 100%
```

> 📌 **Lưu ý quan trọng:** Product-level fulfillment được tính **động** dựa trên dữ liệu
> đã lọc. Khi bạn lọc theo Customer A, Total Demand chỉ bao gồm nhu cầu của Customer A
> (không phải toàn bộ hệ thống).
""")

    # ── Inventory terms ──────────────────────────────────────────
    st.markdown("#### 🏭 Tồn kho")
    st.markdown("""
| Thuật ngữ | Ý nghĩa |
|-----------|---------|
| **In-Stock (Preferred WH)** | Tồn kho tại kho ưu tiên được chỉ định trên DN |
| **In-Stock (All WH)** | Tổng tồn kho tại **tất cả** kho |
| **Include expired stock** ✅ | Tính cả lô hàng đã quá hạn sử dụng |
| **Include expired stock** ☐ | Chỉ tính lô hàng còn hạn (`expired_date > today` hoặc không có hạn) |

> Khi tắt "Include expired stock", hệ thống dùng cột `_valid` — chỉ gồm hàng còn hạn.
> Điều này ảnh hưởng đến **tất cả** chỉ số fulfillment (Gap, Fulfill %, Status).
""")

    # ── Timeline terms ───────────────────────────────────────────
    st.markdown("#### 📅 Ngày tháng")
    st.markdown("""
| Thuật ngữ | Ý nghĩa |
|-----------|---------|
| **ETD** | Estimated Time of Delivery — Ngày giao hàng dự kiến |
| **Adjusted ETD** | ETD đã được điều chỉnh (ưu tiên hơn ETD gốc) |
| **Days Overdue** | Số ngày quá hạn = Hôm nay − ETD (chỉ khi Overdue) |
| **Created Date** | Ngày tạo DN |
| **Dispatched Date** | Ngày gửi hàng |
| **Delivered Date** | Ngày giao hàng thực tế |

```
ETD hiệu lực = COALESCE(Adjusted ETD, ETD gốc)
```
Khi sửa ETD trên giao diện, hệ thống lưu vào **Adjusted ETD** — ETD gốc được giữ nguyên.
""")

    # ── Other terms ──────────────────────────────────────────────
    st.markdown("#### 🏢 Đối tác & Phân loại")
    st.markdown("""
| Thuật ngữ | Ý nghĩa |
|-----------|---------|
| **Customer (Sold-To)** | Công ty mua hàng — đối tác thương mại |
| **Ship-To Company** | Công ty nhận hàng — địa chỉ giao thực tế (có thể khác Customer) |
| **Legal Entity** | Pháp nhân bán hàng (Prostech VN, Prostech Asia…) |
| **EPE Company** | Doanh nghiệp chế xuất (Export Processing Enterprise) — hưởng ưu đãi thuế |
| **Foreign / Domestic** | Khách nước ngoài / nội địa — so sánh mã quốc gia Customer vs Legal Entity |
| **DN (Delivery Note)** | Phiếu giao hàng — 1 DN gồm nhiều dòng sản phẩm |
| **OC (Order Confirmation)** | Xác nhận đơn hàng — liên kết với DN |
""")


# ═════════════════════════════════════════════════════════════════
# TAB 4 — FAQ
# ═════════════════════════════════════════════════════════════════

def _tab_faq():
    st.markdown("### ❓ Câu hỏi thường gặp")

    # ── Q1 ───────────────────────────────────────────────────────
    with st.expander("**Pending Qty = 0 có nghĩa là đã giao hàng xong chưa?**"):
        st.markdown("""
**Chưa chắc.** Pending Qty = 0 chỉ có nghĩa là đã **xuất kho đủ** số lượng yêu cầu.
Hàng có thể vẫn đang trên đường giao.

Để biết đã giao xong hay chưa, kiểm tra **Shipment Status**:
- `STOCKED_OUT` → Đã xuất kho nhưng chưa gửi đi
- `DISPATCHED` → Đã gửi đi, đang trên đường
- `ON_DELIVERY` → Đang giao
- `DELIVERED` → ✅ Đã giao hàng xong

**Tóm tắt flow:**
```
Pending Qty = 0  →  Xuất kho xong  →  Dispatch  →  On Delivery  →  Delivered
```
""")

    # ── Q2 ───────────────────────────────────────────────────────
    with st.expander("**Tại sao Overdue không thay đổi khi tôi filter?**"):
        st.markdown("""
**Đây là thiết kế có chủ đích.** Chỉ số Overdue (⚠️) luôn phản ánh
**toàn bộ DN active trong hệ thống**, không bị ảnh hưởng bởi bộ lọc.

Lý do: Overdue là cảnh báo **toàn cục** — dù bạn đang xem dữ liệu của
1 khách hàng cụ thể, bạn vẫn cần biết tổng số DN quá hạn trên toàn hệ thống.

Các chỉ số khác (Deliveries, Line Items, Pending Qty, Avg Fulfill %, Out of Stock)
**có** thay đổi theo filter.
""")

    # ── Q3 ───────────────────────────────────────────────────────
    with st.expander("**Fulfill Rate % khác nhau giữa Pivot và Detailed List?**"):
        st.markdown("""
Có thể xảy ra vì **Pivot Table hiển thị trung bình** (mean) của Fulfill Rate %,
còn **Detailed List hiển thị giá trị từng dòng**.

Fulfill Rate % được tính lại **động** dựa trên dữ liệu đã lọc:
- Khi bạn lọc theo 1 Customer, Total Demand chỉ gồm nhu cầu của Customer đó
- Khi xem All Data, Total Demand gồm nhu cầu toàn bộ hệ thống

→ Cùng 1 sản phẩm nhưng Fulfill Rate % sẽ khác nhau tùy phạm vi lọc.
""")

    # ── Q4 ───────────────────────────────────────────────────────
    with st.expander("**Checkbox 'Include expired stock' ảnh hưởng gì?**"):
        st.markdown("""
Khi **bật** (mặc định): Tồn kho bao gồm cả lô hàng đã hết hạn sử dụng.
Khi **tắt**: Chỉ tính lô hàng còn hạn (expired_date > hôm nay hoặc không có hạn).

Ảnh hưởng đến:
- **In-Stock (Preferred WH)** và **In-Stock (All WH)**
- **Gap Qty** — thiếu hụt sẽ lớn hơn khi tắt (ít hàng hơn)
- **Fulfill Rate %** — sẽ thấp hơn khi tắt
- **Fulfillment Status** — có thể chuyển từ "Can Fulfill" sang "Out of Stock"

> 💡 **Khi nào nên tắt?** Khi cần đánh giá khả năng giao hàng thực tế — hàng hết hạn
> thường không thể giao cho khách.
""")

    # ── Q5 ───────────────────────────────────────────────────────
    with st.expander("**Exclude mode hoạt động thế nào?**"):
        st.markdown("""
Mỗi bộ lọc multiselect có checkbox **Excl** bên phải:

- **Excl tắt** (mặc định): Chỉ hiện các mục đã chọn
- **Excl bật**: Hiện tất cả **trừ** các mục đã chọn

**Ví dụ — Timeline Status:**

Mặc định đã chọn "Completed" + Excl bật → ẩn DN đã hoàn tất → chỉ hiện DN active.

Nếu bạn muốn xem **chỉ** DN Overdue: chọn "Overdue" + **tắt** Excl.
""")

    # ── Q6 ───────────────────────────────────────────────────────
    with st.expander("**Khi sửa ETD, ai sẽ nhận email thông báo?**"):
        st.markdown("""
Khi bạn sửa ETD và nhấn Save:

- **TO (Người nhận):** Creator/Sales — người đã tạo DN
- **CC:** Bạn (người sửa) + `dn_update@prostech.vn`

Nội dung email gồm: DN number, Customer, Ship-To, ETD cũ → ETD mới, lý do thay đổi.

Email được gửi **theo nhóm**: nếu bạn sửa 5 DN của cùng 1 Creator, chỉ gửi 1 email
chứa tất cả thay đổi.

> 📌 Mỗi lần gửi email ETD Update đều được ghi vào **Audit Log** (bảng `email_send_log`).
""")

    # ── Q7 ───────────────────────────────────────────────────────
    with st.expander("**Filter Presets là gì? Dùng thế nào?**"):
        st.markdown("""
Filter Presets cho phép bạn **lưu và tái sử dụng** bộ lọc:

1. **Export:** Thiết lập bộ lọc mong muốn → mở **💾 Filter Presets** → nhấn **📥 Export** → lưu file JSON
2. **Import:** Mở **💾 Filter Presets** → upload file JSON đã lưu → bộ lọc tự động áp dụng

Hữu ích khi bạn thường xuyên xem cùng 1 bộ lọc (VD: DN overdue của Customer A, sản phẩm Brand X…).
""")

    # ── Q8 ───────────────────────────────────────────────────────
    with st.expander("**Pivot Table — Cách đọc và tùy chỉnh?**"):
        st.markdown("""
Pivot Table cho phép bạn nhóm và tổng hợp dữ liệu linh hoạt:

- **Rows:** Chọn 1+ trường để nhóm (VD: Customer, Product)
- **Columns:** Chọn "Time Period" (ngày/tuần/tháng) hoặc "Category" (trường phân loại)
- **Value:** Chọn giá trị cần tổng hợp (VD: Pending Qty, Delivery Count)
- **Aggregation:** Cách tổng hợp (sum, mean, count…)

**Ví dụ thực tế:**
- *"Pending Qty theo Customer theo tuần"* → Rows: Customer, Columns: Weekly, Value: Pending Qty
- *"Số DN theo Brand và Fulfillment Status"* → Rows: Brand, Columns: Fulfillment Status, Value: Delivery Count
""")

    # ── Q9 ───────────────────────────────────────────────────────
    with st.expander("**Gap Qty âm có phải là lỗi?**"):
        st.markdown("""
**Không.** Gap Qty âm (hiển thị số âm) có nghĩa là tồn kho **dư** so với nhu cầu.

```
Gap Qty = Pending Qty − Tồn kho
```

- **Gap > 0:** Thiếu hàng — cần nhập thêm
- **Gap = 0:** Vừa đủ
- **Gap < 0:** Dư hàng — tồn kho nhiều hơn nhu cầu

Tương tự, Fulfill Rate % > 100% nghĩa là tồn kho gấp nhiều lần nhu cầu.
""")

    # ── Q10 ──────────────────────────────────────────────────────
    with st.expander("**Tôi cần gửi email nhưng không thấy nút gửi?**"):
        st.markdown("""
Tab **📧 Email Notifications** luôn hiển thị, nhưng chức năng gửi email chỉ khả dụng
cho các role:

| Chức năng | Role |
|-----------|------|
| **Gửi email** | `admin`, `supply_chain_manager`, `outbound_manager`, `supply_chain`, `sales_manager`, `GM`, `MD` |
| **Sửa ETD** | `admin`, `supply_chain_manager`, `outbound_manager`, `supply_chain` |
| **Export CSV** | Các role trên + `sales`, `inbound_manager`, `warehouse_manager` |

Role **admin** có toàn quyền. Liên hệ quản trị viên nếu cần nâng quyền.
""")

    # ── Q11 ──────────────────────────────────────────────────────
    with st.expander("**Email History là gì? Tìm ở đâu?**"):
        st.markdown("""
**📜 Email History** nằm ở đầu tab **📧 Email Notifications** (mục đóng mở).

Hiển thị **30 email gần nhất** đã gửi từ hệ thống, bao gồm:
thời gian gửi, loại email, người nhận, trạng thái (✅/❌/⚠️), người gửi, số DN.

Tất cả email gửi ra đều được ghi vào bảng `email_send_log` trong DB — không thể thất lạc.
""")

    # ── Q12 ──────────────────────────────────────────────────────
    with st.expander("**Hệ thống cảnh báo 'Already sent today' nghĩa là gì?**"):
        st.markdown("""
Khi bạn nhấn **🚀 Send Now**, hệ thống kiểm tra bảng `email_send_log`:

Nếu đã gửi **cùng loại email** cho **cùng người nhận** trong **cùng ngày hôm nay**,
hệ thống hiện cảnh báo kèm giờ gửi lần trước.

**Đây chỉ là cảnh báo, không chặn.** Bạn vẫn có thể gửi lại nếu cần
(ví dụ: dữ liệu đã thay đổi kể từ lần gửi trước).
""")

    # ── Q13 ──────────────────────────────────────────────────────
    with st.expander("**Cách chọn người nhận TO/CC từ danh sách nhân viên?**"):
        st.markdown("""
Khi chọn **Custom Recipients** hoặc cấu hình **CC**, bạn có 3 nguồn:

1. **👥 Employee Picker** — chọn từ danh sách nhân viên active (có tìm kiếm theo tên/email)
2. **📋 Email Group** — chọn theo nhóm (VD: "Customs Team", "Outbound Team")
   → tự động thêm tất cả email trong nhóm
3. **✉️ Additional Manual** — nhập thêm email bằng tay (cho người ngoài hệ thống)

Có thể kết hợp cả 3 nguồn. Hệ thống tự động loại bỏ email trùng lặp.
""")

    # ── Q14 ──────────────────────────────────────────────────────
    with st.expander("**Tính năng Preview Email hoạt động thế nào?**"):
        st.markdown("""
Nhấn **👁️ Preview Email Content** để xem trước:

1. **Metrics:** Số DN, số sản phẩm, tổng số lượng chờ giao
2. **HTML Preview:** Nội dung email **thực tế** sẽ gửi (hiển thị trong khung cuộn)

Dữ liệu preview dùng người nhận đầu tiên làm mẫu. Nội dung thực sẽ khác nhau
cho từng người nhận (mỗi Sales/Customer có data riêng).
""")

    # ── Q15 ──────────────────────────────────────────────────────
    with st.expander("**Customs Clearance email — không còn hardcode email?**"):
        st.markdown("""
Đúng. Trước đây email customs luôn gửi đến `custom.clearance@prostech.vn` cố định.

Bây giờ bạn tự chọn người nhận cho Customs Clearance từ:
- **📋 Email Group** — chọn nhóm "Customs Team" (khuyến nghị)
- **👥 Employee** — chọn từng nhân viên customs
- **✉️ Manual** — nhập email bên ngoài

CC cũng tương tự — chọn từ employee/group/manual.
""")