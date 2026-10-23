# Công thức DAX và Power Query (project tồn kho và chuỗi cung ứng)

Tài liệu tổng hợp mọi công thức dùng trong `Inventory_Dashboard.pbix`.
Nếu máy dùng cài đặt khu vực tiếng Việt, đổi dấu `,` giữa các tham số thành `;` khi dán vào Power BI.

## 1. Power Query

5 file CSV nạp bằng **Get data** → **Text/CSV** (UTF-8, dấu phẩy), đổi tên thành `Fact_StockLedger`, `Fact_PurchaseOrder`, `Dim_Item`, `Dim_Supplier`, `Dim_Warehouse`. Với file nhỏ như `dim_warehouse.csv`, nếu tên cột hiện là `Column1`, `Column2`... thì bấm **Home** → **Use First Row as Headers**.

Kiểu dữ liệu:

| Bảng | Cột và kiểu |
|---|---|
| Fact_StockLedger | `entry_id` Whole number, `posting_date` Date, `qty_change` Whole number, `unit_cost` Fixed decimal number, `value_change` Whole number, các cột còn lại Text |
| Fact_PurchaseOrder | `order_date`, `expected_date`, `received_date` Date (ô trống của đơn chưa nhận giữ nguyên là null), `qty_ordered`, `qty_received` Whole number, `unit_price` Fixed decimal number, các cột còn lại Text |
| Dim_Item | `standard_cost` Whole number, các cột còn lại Text |
| Dim_Supplier | `promised_lead_days` Whole number, các cột còn lại Text |
| Dim_Warehouse | 3 cột Text |

Đã tắt **Auto date/time** vì dùng bảng lịch riêng.

## 2. Bảng tính toán

### Dim_Date

```
Dim_Date =
ADDCOLUMNS(
    CALENDAR(
        DATE(YEAR(MIN(Fact_StockLedger[posting_date])), 1, 1),
        DATE(YEAR(MAX(Fact_PurchaseOrder[expected_date])), 12, 31)
    ),
    "Year", YEAR([Date]),
    "MonthNo", MONTH([Date]),
    "Month", FORMAT([Date], "MMM"),
    "YearMonth", FORMAT([Date], "YYYY-MM")
)
```

Cột `Month` sắp xếp theo `MonthNo`. Bảng được đánh dấu là **Date table**.

## 3. Quan hệ

| Từ (phía 1) | Sang (phía nhiều) | Trạng thái |
|---|---|---|
| `Dim_Item[item_id]` | `Fact_StockLedger[item_id]` | Active |
| `Dim_Item[item_id]` | `Fact_PurchaseOrder[item_id]` | Active |
| `Dim_Warehouse[warehouse_id]` | `Fact_StockLedger[warehouse_id]` | Active |
| `Dim_Warehouse[warehouse_id]` | `Fact_PurchaseOrder[warehouse_id]` | Active |
| `Dim_Supplier[supplier_id]` | `Fact_PurchaseOrder[supplier_id]` | Active |
| `Dim_Date[Date]` | `Fact_StockLedger[posting_date]` | Active |
| `Dim_Date[Date]` | `Fact_PurchaseOrder[order_date]` | Active |
| `Dim_Date[Date]` | `Fact_PurchaseOrder[expected_date]` | Inactive |
| `Dim_Date[Date]` | `Fact_PurchaseOrder[received_date]` | Inactive |

Không nối `Dim_Item[main_supplier_id]` với `Dim_Supplier`, để tránh hai đường lọc đến cùng một bảng Fact.

## 4. Cột tính toán

### Dim_Supplier

```
Supplier Short =
TRIM(
    SUBSTITUTE(
        SUBSTITUTE(
            SUBSTITUTE(Dim_Supplier[supplier_name], "Công ty TNHH ", ""),
            "Công ty CP ", ""
        ),
        "Công ty ", ""
    )
)
```

### Dim_Item (phân loại ABC)

```
Item COGS =
COALESCE(
    -CALCULATE(
        SUM(Fact_StockLedger[value_change]),
        Fact_StockLedger[voucher_type] = "Sales Issue"
    ),
    0
)
```

```
ABC Cum % =
VAR Cur = Dim_Item[Item COGS]
VAR TotalCOGS = SUM(Dim_Item[Item COGS])
RETURN
DIVIDE(
    SUMX(FILTER(Dim_Item, Dim_Item[Item COGS] >= Cur), Dim_Item[Item COGS]),
    TotalCOGS
)
```

```
ABC Class =
VAR Share = DIVIDE(Dim_Item[Item COGS], SUM(Dim_Item[Item COGS]))
VAR CumBefore = Dim_Item[ABC Cum %] - Share
RETURN
SWITCH(
    TRUE(),
    CumBefore < 0.8, "A",
    CumBefore < 0.95, "B",
    "C"
)
```

```
ABC Rank = RANKX(ALL(Dim_Item), Dim_Item[Item COGS], , DESC, DENSE)
```

`ABC Rank` dùng làm trục ngang của biểu đồ Pareto (kiểu Continuous).

## 5. Measures: ngày dữ liệu

```
Data Start Date = CALCULATE(MIN(Fact_StockLedger[posting_date]), REMOVEFILTERS())
```

```
Data End Date = CALCULATE(MAX(Fact_StockLedger[posting_date]), REMOVEFILTERS())
```

## 6. Measures: tồn kho

Tồn kho là số dư cộng dồn, nên cộng mọi giao dịch từ đầu đến hết kỳ đang xét. Dòng `IF` trả về trống cho các tháng sau khi dữ liệu kết thúc.

```
Closing Stock Qty =
VAR PeriodStart = MIN(Dim_Date[Date])
VAR PeriodEnd = MIN(MAX(Dim_Date[Date]), [Data End Date])
RETURN
IF(
    PeriodStart > [Data End Date],
    BLANK(),
    CALCULATE(
        SUM(Fact_StockLedger[qty_change]),
        FILTER(ALL(Dim_Date), Dim_Date[Date] <= PeriodEnd)
    )
)
```

```
Closing Stock Value =
VAR PeriodStart = MIN(Dim_Date[Date])
VAR PeriodEnd = MIN(MAX(Dim_Date[Date]), [Data End Date])
RETURN
IF(
    PeriodStart > [Data End Date],
    BLANK(),
    CALCULATE(
        SUM(Fact_StockLedger[value_change]),
        FILTER(ALL(Dim_Date), Dim_Date[Date] <= PeriodEnd)
    )
)
```

```
COGS =
-CALCULATE(
    SUM(Fact_StockLedger[value_change]),
    Fact_StockLedger[voucher_type] = "Sales Issue"
)
```

```
Avg Inventory Value =
AVERAGEX(VALUES(Dim_Date[YearMonth]), [Closing Stock Value])
```

```
Inventory Turnover = DIVIDE([COGS], [Avg Inventory Value])
```

```
Days in Period =
COUNTROWS(
    FILTER(
        Dim_Date,
        Dim_Date[Date] >= [Data Start Date] && Dim_Date[Date] <= [Data End Date]
    )
)
```

```
Inventory Turnover (Annualized) =
DIVIDE([COGS] * 365, [Days in Period] * [Avg Inventory Value])
```

```
Days of Inventory =
DIVIDE([Avg Inventory Value], DIVIDE([COGS], [Days in Period]))
```

```
Units Sold =
-CALCULATE(
    SUM(Fact_StockLedger[qty_change]),
    Fact_StockLedger[voucher_type] = "Sales Issue"
)
```

```
Units Received =
CALCULATE(
    SUM(Fact_StockLedger[qty_change]),
    Fact_StockLedger[voucher_type] = "Purchase Receipt"
)
```

## 7. Measures: hàng tồn đọng

Quy ước: mã còn tồn kho và không có lần bán nào trong 180 ngày trước ngày cuối của dữ liệu.

```
Last Sales Date =
CALCULATE(
    MAX(Fact_StockLedger[posting_date]),
    Fact_StockLedger[voucher_type] = "Sales Issue",
    REMOVEFILTERS(Dim_Date)
)
```

```
Days Since Last Sale =
IF(
    ISBLANK([Last Sales Date]),
    BLANK(),
    DATEDIFF([Last Sales Date], [Data End Date], DAY)
)
```

```
Is Dead Stock =
IF(
    [Closing Stock Qty] > 0
        && ( ISBLANK([Last Sales Date]) || [Days Since Last Sale] > 180 ),
    1,
    0
)
```

```
Dead Stock Items =
SUMX(VALUES(Dim_Item[item_id]), [Is Dead Stock])
```

```
Dead Stock Value =
SUMX(
    VALUES(Dim_Item[item_id]),
    IF([Is Dead Stock] = 1, [Closing Stock Value], 0)
)
```

```
Dead Stock % = DIVIDE([Dead Stock Value], [Closing Stock Value])
```

```
Dead Stock Status = IF([Is Dead Stock] = 1, "Dead stock", "Active")
```

## 8. Measures: ABC

```
Item Count = DISTINCTCOUNT(Dim_Item[item_id])
```

```
Item % (ABC) =
DIVIDE([Item Count], CALCULATE([Item Count], ALL(Dim_Item[ABC Class])))
```

```
COGS % (ABC) =
DIVIDE([COGS], CALCULATE([COGS], ALL(Dim_Item[ABC Class])))
```

```
Stock Value % (ABC) =
DIVIDE([Closing Stock Value], CALCULATE([Closing Stock Value], ALL(Dim_Item[ABC Class])))
```

```
ABC 80% Line = 0.8
```

## 9. Measures: đơn mua và nhà cung cấp

```
PO Lines = COUNTROWS(Fact_PurchaseOrder)
```

```
Received Lines = CALCULATE([PO Lines], Fact_PurchaseOrder[status] <> "Open")
```

```
On-Time Lines =
COUNTROWS(
    FILTER(
        Fact_PurchaseOrder,
        Fact_PurchaseOrder[status] <> "Open"
            && Fact_PurchaseOrder[received_date] <= Fact_PurchaseOrder[expected_date]
    )
)
```

```
On-Time % = DIVIDE([On-Time Lines], [Received Lines])
```

```
Late Lines = [Received Lines] - [On-Time Lines]
```

```
Avg Lead Time (days) =
AVERAGEX(
    FILTER(Fact_PurchaseOrder, Fact_PurchaseOrder[status] <> "Open"),
    DATEDIFF(Fact_PurchaseOrder[order_date], Fact_PurchaseOrder[received_date], DAY)
)
```

```
Avg Delay (days) =
AVERAGEX(
    FILTER(Fact_PurchaseOrder, Fact_PurchaseOrder[status] <> "Open"),
    DATEDIFF(Fact_PurchaseOrder[expected_date], Fact_PurchaseOrder[received_date], DAY)
)
```

```
PO Spend =
SUMX(Fact_PurchaseOrder, Fact_PurchaseOrder[qty_ordered] * Fact_PurchaseOrder[unit_price])
```

```
PO Standard Cost =
SUMX(Fact_PurchaseOrder, Fact_PurchaseOrder[qty_ordered] * RELATED(Dim_Item[standard_cost]))
```

```
Price Variance Amount = [PO Spend] - [PO Standard Cost]
```

```
Purchase Price Variance % = DIVIDE([Price Variance Amount], [PO Standard Cost])
```

```
Overdue Open Lines =
VAR EndDate = [Data End Date]
RETURN
CALCULATE(
    [PO Lines],
    Fact_PurchaseOrder[status] = "Open",
    Fact_PurchaseOrder[expected_date] < EndDate
)
```

```
Avg Paid Unit Price =
DIVIDE([PO Spend], SUM(Fact_PurchaseOrder[qty_ordered]))
```

```
Avg Standard Unit Cost =
DIVIDE([PO Standard Cost], SUM(Fact_PurchaseOrder[qty_ordered]))
```

### USERELATIONSHIP

Quan hệ mặc định nối bảng lịch với `order_date`. Measure thứ hai tạm đổi sang quan hệ `received_date`.

```
Qty Ordered by Order Date = SUM(Fact_PurchaseOrder[qty_ordered])
```

```
Qty Received by Receipt Date =
CALCULATE(
    SUM(Fact_PurchaseOrder[qty_received]),
    USERELATIONSHIP(Dim_Date[Date], Fact_PurchaseOrder[received_date])
)
```

### Nhãn cảnh báo nhà cung cấp

```
Supplier Flag =
SWITCH(
    TRUE(),
    [Received Lines] = 0, BLANK(),
    [On-Time %] < 0.2, "Late delivery",
    [Purchase Price Variance %] > 0.1, "Price creep",
    [On-Time %] < 0.5, "Watch",
    "OK"
)
```

```
Supplier Flag Color =
SWITCH(
    [Supplier Flag],
    "Late delivery", "#F8D7DA",
    "Price creep", "#FFE5CC",
    "Watch", "#FFF3CD",
    "OK", "#D4EDDA",
    BLANK()
)
```

`Supplier Flag Color` dùng để tô màu nền cột cảnh báo (**Cell elements** → **Background color** → **Field value**).

## 10. Measures hiển thị (cho Card và trục biểu đồ)

Card kiểu mới của Power BI tự rút gọn số lớn (K, M, bn), nên dùng measure dạng chữ để hiển thị đủ số, và measure chia cho một tỷ để trục biểu đồ hiện số gọn.

```
Closing Stock Value (Display) =
IF(
    ISBLANK([Closing Stock Value]),
    BLANK(),
    FORMAT([Closing Stock Value] / 1000000000, "#,0.00") & " tỷ ₫"
)
```

```
COGS (Display) =
IF(
    ISBLANK([COGS]),
    BLANK(),
    FORMAT([COGS] / 1000000000, "#,0.00") & " tỷ ₫"
)
```

```
Dead Stock Value (Display) =
IF(
    ISBLANK([Dead Stock Value]),
    BLANK(),
    FORMAT([Dead Stock Value] / 1000000000, "#,0.00") & " tỷ ₫"
)
```

```
Price Variance Amount (Display) =
IF(
    ISBLANK([Price Variance Amount]),
    BLANK(),
    FORMAT([Price Variance Amount] / 1000000000, "#,0.00") & " tỷ ₫"
)
```

```
Closing Stock Qty (Display) =
IF(ISBLANK([Closing Stock Qty]), BLANK(), FORMAT([Closing Stock Qty], "#,0"))
```

```
COGS (tỷ) = DIVIDE([COGS], 1000000000)
```

```
Closing Stock Value (tỷ) = DIVIDE([Closing Stock Value], 1000000000)
```

```
Price Variance Amount (tỷ) = DIVIDE([Price Variance Amount], 1000000000)
```

Các measure dạng chữ (`(Display)`) chỉ dùng cho Card, không dùng cho tính toán.

## 11. Ghi chú thiết kế

- Dùng **cột tính sẵn** cho phân loại ABC vì cần đưa nhóm lên trục biểu đồ. Đổi lại, nhóm ABC không đổi theo bộ lọc năm.
- Hàng tồn đọng dùng **measure** nên đúng ở mọi cấp (theo nhóm hàng, theo kho), nhưng cờ tính tại ngày cuối dữ liệu.
- Dùng `DIVIDE` thay cho dấu `/` để tránh lỗi chia cho 0.
- Giá vốn xuất kho trong dữ liệu mô phỏng tính theo bình quân gia quyền di động, nên giá trị tồn kho là tổng `value_change` cộng dồn.
