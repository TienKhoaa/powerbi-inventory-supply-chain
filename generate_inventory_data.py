"""
generate_inventory_data.py
--------------------------
Sinh dữ liệu MÔ PHỎNG tồn kho và mua hàng cho một công ty phân phối vật tư thiết bị điện.
Đây là dữ liệu giả, không phải dữ liệu của doanh nghiệp thật.

Cách chạy:  python generate_inventory_data.py
Kết quả:    thư mục data/ gồm 5 file CSV
              dim_item.csv, dim_warehouse.csv, dim_supplier.csv,
              fact_purchase_order.csv, fact_stock_ledger.csv

Các mẫu hình được cài sẵn trong dữ liệu (để dashboard có thứ để phát hiện):
  - Khoảng 10% mã hàng ngừng bán sau một thời điểm, trong đó có một đơn mua dư ngay
    trước khi ngừng bán  -> hàng tồn đọng (dead stock).
  - Khoảng 15% mã hàng bán rất chậm.
  - Khoảng 8% mã hàng bị đặt dư (số lượng đặt mỗi lần gấp 4 lần bình thường).
  - 2 nhà cung cấp hay giao trễ, 2 nhà cung cấp tăng giá dần theo thời gian.
  - Nhu cầu có tính mùa vụ (thấp dịp Tết, cao vào mùa xây dựng cuối năm).
"""
import os
from datetime import date, timedelta

import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)

START = date(2024, 10, 1)
END = date(2026, 9, 30)
N_DAYS = (END - START).days + 1
OUT_DIR = "data"
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------- Kho
warehouses = pd.DataFrame({
    "warehouse_id": ["WH01", "WH02", "WH03"],
    "warehouse_name": ["Kho Hà Nội", "Kho Đà Nẵng", "Kho TP.HCM"],
    "region": ["Miền Bắc", "Miền Trung", "Miền Nam"],
})
WH_WEIGHT = np.array([0.35, 0.15, 0.50])  # tỷ trọng nhu cầu theo kho

# ---------------------------------------------------------------- Nhà cung cấp
sup_names = [
    "Công ty TNHH Điện Việt Phát", "Công ty CP Thiết bị Điện Hoàng Long",
    "Công ty TNHH Cáp điện Đông Á Phát", "Công ty CP Chiếu sáng Minh Quang",
    "Công ty TNHH Vật tư Điện Bắc Hà", "Công ty CP Cơ điện Nam Thành",
    "Công ty TNHH Thiết bị Đo Tân Phong", "Công ty CP Tủ bảng điện An Khang",
    "Công ty TNHH Phụ kiện Điện Sao Mai", "Công ty CP Dụng cụ Kim Long",
    "Công ty TNHH Điện Dân dụng Hưng Thịnh", "Công ty CP Vật liệu Điện Đại Dương",
]
sup_region = ["Miền Bắc", "Miền Nam", "Miền Bắc", "Miền Trung", "Miền Bắc", "Miền Nam",
              "Nhập khẩu", "Miền Nam", "Miền Trung", "Nhập khẩu", "Miền Nam", "Miền Bắc"]
LEAD = np.array([7, 5, 10, 6, 8, 5, 21, 7, 6, 18, 6, 9])  # số ngày hứa giao
N_SUP = len(sup_names)
SUP_IDS = np.array([f"SUP{i:02d}" for i in range(1, N_SUP + 1)])

# Độ trễ giao hàng thực tế = chuẩn hứa + độ lệch ngẫu nhiên (trung bình, độ lệch chuẩn)
delay_mu = np.full(N_SUP, -0.5)
delay_sd = np.full(N_SUP, 1.2)
for s in (1, 3, 5, 8):          # nhóm trung bình
    delay_mu[s], delay_sd[s] = 1.0, 2.0
for s in (4, 10):               # nhóm hay giao trễ
    delay_mu[s], delay_sd[s] = 6.0, 4.0

# Tốc độ tăng giá mỗi tháng của nhà cung cấp
creep = np.full(N_SUP, 0.002)
for s in (7, 11):               # nhóm tăng giá dần
    creep[s] = 0.015

suppliers = pd.DataFrame({
    "supplier_id": SUP_IDS,
    "supplier_name": sup_names,
    "region": sup_region,
    "promised_lead_days": LEAD,
})

# ---------------------------------------------------------------- Mã hàng
SERIES = ["Eco", "Std", "Pro", "Plus"]
CATEGORIES = {
    "Cáp điện": dict(
        bases=["Cáp đồng 1 lõi", "Cáp đồng 2 lõi", "Cáp điều khiển", "Cáp nhôm vặn xoắn"],
        specs=["1.5mm²", "2.5mm²", "4mm²", "6mm²", "10mm²"],
        unit="mét", price=(8_000, 90_000), n=45, demand=3.0, sup=[2, 0, 10]),
    "Aptomat & Cầu dao": dict(
        bases=["Aptomat 1P", "Aptomat 2P", "Aptomat 3P", "Cầu dao 2P"],
        specs=["10A", "16A", "20A", "32A", "40A", "63A"],
        unit="cái", price=(45_000, 650_000), n=50, demand=1.2, sup=[1, 0, 5]),
    "Ổ cắm & Công tắc": dict(
        bases=["Ổ cắm đôi", "Ổ cắm ba", "Công tắc 1 chiều", "Công tắc 2 chiều"],
        specs=["trắng", "đen", "ghi", "vàng đồng", "bạc"],
        unit="cái", price=(15_000, 250_000), n=45, demand=1.5, sup=[8, 1, 10]),
    "Đèn LED": dict(
        bases=["Bóng LED bulb", "Đèn LED panel", "Đèn LED tuýp", "Đèn pha LED"],
        specs=["9W", "12W", "18W", "24W", "36W", "50W"],
        unit="cái", price=(20_000, 900_000), n=45, demand=2.0, sup=[3, 11, 5]),
    "Ống & Phụ kiện": dict(
        bases=["Ống luồn dây", "Ống ruột gà", "Máng cáp", "Co nối"],
        specs=["D16", "D20", "D25", "D32", "D40"],
        unit="cây", price=(5_000, 180_000), n=40, demand=1.5, sup=[8, 4, 11]),
    "Thiết bị đo": dict(
        bases=["Ampe kìm", "Đồng hồ vạn năng", "Công tơ điện", "Bút thử điện"],
        specs=["Model A", "Model B", "Model C"],
        unit="cái", price=(120_000, 3_500_000), n=25, demand=0.4, sup=[6, 9]),
    "Tủ điện": dict(
        bases=["Tủ điện âm tường", "Tủ điện nổi", "Tủ điện ngoài trời"],
        specs=["6 module", "12 module", "18 module", "24 module"],
        unit="cái", price=(150_000, 1_800_000), n=20, demand=0.3, sup=[7, 5, 4]),
    "Dụng cụ": dict(
        bases=["Kìm điện", "Tua vít", "Mỏ lết", "Máy khoan"],
        specs=["Loại nhỏ", "Loại vừa", "Loại lớn"],
        unit="cái", price=(30_000, 1_200_000), n=30, demand=0.6, sup=[9, 6, 11]),
}

items = []
for cat, cfg in CATEGORIES.items():
    combos = [(b, s, ser) for b in cfg["bases"] for s in cfg["specs"] for ser in SERIES]
    pick = rng.choice(len(combos), size=cfg["n"], replace=False)
    lo, hi = cfg["price"]
    for k in pick:
        b, s, ser = combos[k]
        price = float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
        u = rng.random()
        items.append(dict(
            category=cat,
            item_name=f"{b} {s} {ser}",
            unit=cfg["unit"],
            standard_cost=max(int(round(price, -2)), 1000),
            sup=int(rng.choice(cfg["sup"])),
            daily=float(rng.lognormal(0.2, 1.2)) * cfg["demand"],
            dead=u < 0.10,
            slow=(0.10 <= u < 0.25),
            over=bool(rng.random() < 0.08),
        ))
rng.shuffle(items)
N_ITEMS = len(items)
ITEM_IDS = np.array([f"ITM{i + 1:03d}" for i in range(N_ITEMS)])

dim_item = pd.DataFrame({
    "item_id": ITEM_IDS,
    "item_name": [it["item_name"] for it in items],
    "category": [it["category"] for it in items],
    "unit": [it["unit"] for it in items],
    "standard_cost": [it["standard_cost"] for it in items],
    "main_supplier_id": [SUP_IDS[it["sup"]] for it in items],
})

# ---------------------------------------------------------------- Cặp (mã hàng, kho)
pair_item, pair_wh, lam_base, rop, rqty = [], [], [], [], []
pair_sup, std_cost, cutoff = [], [], []
for i, it in enumerate(items):
    k = int(rng.choice([1, 2, 3], p=[0.3, 0.4, 0.3]))
    whs = rng.choice(3, size=k, replace=False, p=WH_WEIGHT)
    share = WH_WEIGHT[whs] / WH_WEIGHT[whs].sum()
    cut = int(rng.integers(N_DAYS - 540, N_DAYS - 200)) if it["dead"] else N_DAYS + 10
    for w, sh in zip(whs, share):
        lam = it["daily"] * sh * (0.15 if it["slow"] else 1.0)
        lead = LEAD[it["sup"]]
        r_point = max(2, int(np.ceil(lam * (lead + 7))))
        r_qty = max(5, int(np.ceil(lam * 30)))
        if it["over"]:
            r_qty *= 4
        pair_item.append(i)
        pair_wh.append(int(w))
        lam_base.append(lam)
        rop.append(r_point)
        rqty.append(r_qty)
        pair_sup.append(it["sup"])
        std_cost.append(it["standard_cost"])
        cutoff.append(cut)

pair_item = np.array(pair_item)
pair_wh = np.array(pair_wh)
lam_base = np.array(lam_base)
rop = np.array(rop)
rqty = np.array(rqty)
pair_sup = np.array(pair_sup)
std_cost = np.array(std_cost, dtype=float)
cutoff = np.array(cutoff)
P = len(pair_item)

# Mùa vụ theo tháng
MONTH_FACTOR = {1: .8, 2: .7, 3: 1.0, 4: 1.05, 5: 1.1, 6: 1.1,
                7: 1.1, 8: 1.1, 9: 1.15, 10: 1.2, 11: 1.2, 12: 1.1}
season = np.array([MONTH_FACTOR[(START + timedelta(days=i)).month] for i in range(N_DAYS)])

# ---------------------------------------------------------------- Mô phỏng từng ngày
stock = (rop + rqty // 2).astype(np.int64)   # tồn đầu kỳ
open_stock = stock.copy()
on_order = np.zeros(P, dtype=np.int64)
avg_cost = std_cost.copy()
pending = {}      # ngày nhận hàng -> danh sách chỉ số đơn mua
po_rows = []

L_day, L_pair, L_type, L_qty, L_cost = [], [], [], [], []


def add(day, pair, tcode, qty, cost):
    pair = np.atleast_1d(pair)
    n = len(pair)
    L_day.append(np.full(n, day))
    L_pair.append(pair)
    L_type.append(np.full(n, tcode))
    L_qty.append(np.atleast_1d(qty))
    L_cost.append(np.atleast_1d(cost).astype(float))


def create_po(p, t, qty):
    s = pair_sup[p]
    order_day = START + timedelta(days=t)
    expected = order_day + timedelta(days=int(LEAD[s]))
    delay = max(int(round(rng.normal(delay_mu[s], delay_sd[s]))), -2)
    received = expected + timedelta(days=delay)
    price = std_cost[p] * (1 + creep[s]) ** (t / 30.4) * (1 + rng.normal(0, 0.02))
    price = max(round(price, -2), 1000)
    qty_recv = qty if rng.random() > 0.06 else max(1, int(qty * rng.uniform(0.8, 0.98)))
    recv_idx = (received - START).days
    row = dict(pair=p, s=s, order_date=order_day, expected_date=expected,
               qty_ordered=int(qty), unit_price=price)
    if recv_idx <= N_DAYS - 1:
        row.update(received_date=received, qty_received=int(qty_recv),
                   status="Received" if qty_recv == qty else "Partially Received")
        pending.setdefault(recv_idx, []).append(len(po_rows))
    else:
        row.update(received_date=None, qty_received=0, status="Open")
    po_rows.append(row)
    on_order[p] += qty


# Đơn mua dư trước khi mã hàng ngừng bán
extra = {}
for p in range(P):
    if cutoff[p] < N_DAYS:
        extra.setdefault(int(cutoff[p]) - 20, []).append(p)

add(0, np.arange(P), 0, open_stock, std_cost)

for t in range(N_DAYS):
    # 1. Nhận hàng
    for po_i in pending.pop(t, []):
        po = po_rows[po_i]
        p, q, price = po["pair"], po["qty_received"], po["unit_price"]
        if q > 0:
            avg_cost[p] = (stock[p] * avg_cost[p] + q * price) / (stock[p] + q)
            stock[p] += q
            add(t, p, 1, q, price)
        on_order[p] -= po["qty_ordered"]

    # 2. Xuất bán
    active = t < cutoff
    demand = rng.poisson(lam_base * season[t] * active)
    issued = np.minimum(demand, stock)
    idx = np.nonzero(issued > 0)[0]
    if len(idx):
        add(t, idx, 2, -issued[idx], avg_cost[idx])
        stock[idx] -= issued[idx]

    # 3. Điều chỉnh kho (hao hụt, hỏng)
    adj = np.nonzero((rng.random(P) < 0.0004) & (stock > 5))[0]
    if len(adj):
        q = rng.integers(1, 4, len(adj))
        add(t, adj, 3, -q, avg_cost[adj])
        stock[adj] -= q

    # 4. Đặt hàng khi tồn chạm điểm đặt lại
    for p in np.nonzero((stock + on_order <= rop) & (t < cutoff))[0]:
        create_po(int(p), t, int(rqty[p]))
    for p in extra.get(t, []):
        create_po(int(p), t, int(rqty[p]) * 3)

# ---------------------------------------------------------------- Xuất file
VOUCHER = np.array(["Opening Stock", "Purchase Receipt", "Sales Issue", "Stock Adjustment"])
PREFIX = np.array(["OB", "PR", "SI", "SA"])

led = pd.DataFrame({
    "day": np.concatenate(L_day),
    "pair": np.concatenate(L_pair),
    "tcode": np.concatenate(L_type),
    "qty_change": np.concatenate(L_qty).astype(int),
    "unit_cost": np.concatenate(L_cost),
})
led = led.sort_values(["day", "tcode", "pair"], kind="stable").reset_index(drop=True)
led.insert(0, "entry_id", np.arange(1, len(led) + 1))
led["posting_date"] = (pd.Timestamp(START) + pd.to_timedelta(led["day"], unit="D")).dt.strftime("%Y-%m-%d")
led["item_id"] = ITEM_IDS[pair_item[led["pair"].values]]
led["warehouse_id"] = warehouses["warehouse_id"].values[pair_wh[led["pair"].values]]
led["voucher_type"] = VOUCHER[led["tcode"].values]
led["voucher_no"] = [f"{PREFIX[c]}-{e:07d}" for c, e in zip(led["tcode"], led["entry_id"])]
led["unit_cost"] = led["unit_cost"].round(2)
led["value_change"] = (led["qty_change"] * led["unit_cost"]).round(0).astype(np.int64)
stock_ledger = led[["entry_id", "posting_date", "item_id", "warehouse_id", "voucher_type",
                    "voucher_no", "qty_change", "unit_cost", "value_change"]]

# Kiểm tra: tồn kho không bao giờ âm
check = stock_ledger.groupby(["item_id", "warehouse_id"])["qty_change"].cumsum().min()
assert check >= 0, "Có tồn kho âm, kiểm tra lại logic mô phỏng"

po = pd.DataFrame(po_rows)
po_out = pd.DataFrame({
    "po_id": [f"PO-{i + 1:06d}" for i in range(len(po))],
    "item_id": ITEM_IDS[pair_item[po["pair"].values]],
    "supplier_id": SUP_IDS[po["s"].values],
    "warehouse_id": warehouses["warehouse_id"].values[pair_wh[po["pair"].values]],
    "order_date": [d.strftime("%Y-%m-%d") for d in po["order_date"]],
    "expected_date": [d.strftime("%Y-%m-%d") for d in po["expected_date"]],
    "received_date": [d.strftime("%Y-%m-%d") if d is not None else "" for d in po["received_date"]],
    "qty_ordered": po["qty_ordered"],
    "qty_received": po["qty_received"],
    "unit_price": po["unit_price"],
    "status": po["status"],
})

enc = "utf-8-sig"
dim_item.to_csv(f"{OUT_DIR}/dim_item.csv", index=False, encoding=enc)
warehouses.to_csv(f"{OUT_DIR}/dim_warehouse.csv", index=False, encoding=enc)
suppliers.to_csv(f"{OUT_DIR}/dim_supplier.csv", index=False, encoding=enc)
po_out.to_csv(f"{OUT_DIR}/fact_purchase_order.csv", index=False, encoding=enc)
stock_ledger.to_csv(f"{OUT_DIR}/fact_stock_ledger.csv", index=False, encoding=enc)

# ---------------------------------------------------------------- Tóm tắt
issues = stock_ledger[stock_ledger["voucher_type"] == "Sales Issue"]
last_issue = issues.groupby("item_id")["posting_date"].max()
cut_str = (pd.Timestamp(END) - pd.Timedelta(days=180)).strftime("%Y-%m-%d")
n_dead = int((last_issue < cut_str).sum() + (N_ITEMS - len(last_issue)))

print("Đã tạo xong dữ liệu mô phỏng trong thư mục:", os.path.abspath(OUT_DIR))
print(f"  dim_item            : {len(dim_item):>8,} dòng")
print(f"  dim_warehouse       : {len(warehouses):>8,} dòng")
print(f"  dim_supplier        : {len(suppliers):>8,} dòng")
print(f"  fact_purchase_order : {len(po_out):>8,} dòng")
print(f"  fact_stock_ledger   : {len(stock_ledger):>8,} dòng")
print(f"Giai đoạn: {START} đến {END}")
print(f"Giá trị tồn kho cuối kỳ: {stock_ledger['value_change'].sum():,} VND")
print(f"Số mã không xuất kho trong 180 ngày cuối: {n_dead} / {N_ITEMS}")
print("Tồn kho không âm:", check >= 0)
