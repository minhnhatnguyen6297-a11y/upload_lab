# Regex Rule Catalog

Catalog nay ghi co he thong cac quy tac trich xuat dang dung trong `extract_contract.py`.
Khong dua hop dong that vao day. Chi ghi mau rut gon, mau an danh, hoac mo ta de de cap nhat khi co template moi.

## Nguyen tac chung

### Doc du lieu

- Nguon du lieu goc nam trong file Word `.doc` va `.docx`.
- He thong da co san luong code de doc noi dung file Word, khong can mo file bang Microsoft Word de trich xuat.
- Tang regex/rule chi tap trung vao nhan dien va tach truong sau khi da doc duoc text.

### So cong chung

Dang raw co the gap:

- `428/2026/CCGD`
- `428.2026/CCGD`
- `2433.2025/PCDS/CCGD`
- `2233.2025/TCDS/CCGD`
- `428/2026`
- `428`

Nguyen tac:

- Gia tri scan/raw co the giu cac hau to nhu `PCDS`, `TCDS`, `CCGD`.
- Gia tri doi chieu tren web can dua ve dang ngan `xxx/yyyy`.
- Khi so sanh, uu tien normalize de bo khoang trang, dau `.` va cac hau to khong anh huong.

## Truong can trich xuat

Nhung nhom truong duoc uu tien theo doi khi review regex:

- `so_cong_chung`
- `ten_hop_dong`
- `nguoi_yeu_cau`
- `duong_su`
- `tai_san`
- `missing_fields`

## Document Type: Hop dong chuyen nhuong

### Tieu de nhan dien

- `hop dong chuyen nhuong`

### Truong quan tam

- `so_cong_chung`
- `ten_hop_dong`
- `duong_su`
- `tai_san`

### `tai_san` - diem bat dau thuong gap

- `quyen su dung dat ... co dia chi tai`
- `quyen su dung dat va tai san gan lien voi dat ... co dia chi tai`

### `tai_san` - diem ket thuc thuong gap

- `1.2`
- `Dieu 2`
- `Bang Hop dong nay`
- `va duoc Cong chung vien`

### Ghi chu review

- Phai bat dung khoi mo ta tai san chuyen nhuong, khong lay nham doan giai thich hay dieu khoan chung.

## Document Type: Van ban phan chia di san

### Tieu de nhan dien

- `van ban phan chia di san`

### `duong_su` - diem bat dau

- `Chung toi la nhung nguoi duoc huong di san`

### `duong_su` - diem ket thuc

- `Chung toi tu nguyen lap Van ban nay`
- `Nguoi de lai di san:`

### `tai_san` - diem bat dau

- `Di san:`
- `Di san cua ... de lai la:`
- `quyen su dung dat ... co dia chi tai`

### `tai_san` - diem ket thuc

- `Nguoi thua ke:`
- `Noi dung phan chia di san`
- `Bang Van ban nay`
- `Loi chung`

## Document Type: Van ban tu choi nhan di san

### Tieu de nhan dien

- `van ban tu choi nhan di san`

### `duong_su` - diem bat dau

- `Toi la:`

### `duong_su` - diem ket thuc

- `Nay, toi tu nguyen lap Van ban nay`
- `Theo quy dinh cua phap luat`

### `tai_san` - diem bat dau

- `1. Tai san thu nhat:`
- `quyen su dung dat ... co dia chi tai`

### `tai_san` - diem ket thuc

- `Bang Van ban nay, toi`
- `Toi xin cam doan`
- `Nguoi tu choi huong di san`
- `Loi chung`

## Cach cap nhat khi co mau moi

1. Them ten loai van ban moi vao file nay.
2. Ghi ro marker nhan dien tieu de.
3. Liet ke diem bat dau/ket thuc cho `duong_su`, `tai_san`, hoac truong dac thu.
4. Bo sung sample review vao `regex_review_samples/input/` de chay doi chieu.
5. Cap nhat test/review de tranh sua 1 mau lam vo mau cu.
