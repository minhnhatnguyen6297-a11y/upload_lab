# Tab 1 Excel Audit Redesign

## Muc tieu

Thiet ke lai Tab 1 de phuc vu dung nghiep vu doi chieu so cong chung tu file Excel xuat tu web:

- User nhin vao biet ngay danh sach so hop le.
- User nhin vao biet ngay so nao con thieu trong chuoi lien tuc.
- User nhin vao biet ngay cac dong loi, trung, sai nam, sai format, ngay bat thuong de tu xu ly thu cong.

Tab nay khong duoc suy dien ho so bi thieu o folder nao, khong can sua du lieu tu dong, chi phan loai de user ra soat.

## Pham vi

Ap dung cho nhanh Qt dang phat trien tai `ui_qt/`.

Tac dong chinh:

- `ui/services/contract_book_audit.py`
- `tests/test_contract_book_audit.py`
- `ui_qt/forms/main_window.ui`
- `ui_qt/main_window.py`
- `tests/test_qt_ui_structure.py`
- co the can chinh nhe `ui/services/web_list_service.py` neu dang phu thuoc vao cau truc cu

Khong sua flow scan folder, upload, regex review trong dot nay.

## Flow nghiep vu dung

1. User chon hoac tai file Excel.
2. Tab 1 doc cot A va cot B.
3. He thong loc cac dong hop le theo khoang ngay user dang chon tren UI.
4. He thong hien 3 vung:
   - `Danh sach Excel`
   - `So con thieu`
   - `So loi, trung`
5. `So con thieu` chi duoc tinh tu tap du lieu sach sau khi da loai tat ca dong loi/trung/ngay bat thuong.

## Dau vao nghiep vu

Service phan tich Excel phai nhan:

- `export_path`
- `from_date`
- `to_date`

Khoang ngay hop le lay theo gia tri user nhap tren UI, khong suy tu noi dung file Excel.

Voi case hien tai `01/01/2026 -> 18/06/2026`, nam hop le chi la `2026`.

Neu sau nay khoang ngay vach qua 2 nam, cac nam hop le la toan bo nam nam trong khoang `from_date..to_date`.

## Cau truc du lieu service

Service `analyze_contract_book(...)` can tra ve it nhat:

- `display_rows`: cac dong sach de hien o vung `Danh sach Excel`
- `missing_numbers`: cac so thieu, chi tinh tu `display_rows`
- `issue_rows`: cac dong loi/trung/bat thuong
- `summary`
  - `excel_total`
  - `valid_count`
  - `missing_count`
  - `issue_count`
  - `duplicate_count`

`display_rows` la tap cuoi cung da qua tat ca rule nghiep vu. Khong dung lai ten `valid_rows` theo nghia parse duoc mot phan, vi de gay nham voi dong canh bao nhung van lot vao tap tinh missing.

## Rule parse so cong chung

Chi nhan 2 dang:

- `xxx/yyyy`
- `xxx/yyyy/CCGD`

Trong do:

- `xxx` la so thu tu hop dong
- `yyyy` la nam

Normalize:

- bo `/CCGD`
- bo so `0` o dau phan `xxx`
- dua ve dang chuan `xxx/yyyy`

Vi du hop le:

- `1/2026`
- `001/2026`
- `15/2026/CCGD`

Vi du khong hop le:

- `66.2026`
- `2047.2025`
- `344/2006`
- ``
- ten nguoi, chu mo ta, text rac

Tat ca gia tri khong khop 2 dang hop le deu vao `issue_rows` voi loai `sai_format`, tru khi khop dang nhung nam khong hop le thi vao `sai_nam`.

## Rule xac dinh nam hop le

Nam trong so cong chung phai thuoc tap nam cua khoang `from_date..to_date`.

Vi du:

- UI dang chon `01/01/2026 -> 18/06/2026`
- So `296/2025`, `2047/2025`, `344/2006` deu vao loi `sai_nam`
- Tuyet doi khong dua cac dong nay vao tap tinh missing

## Rule trung so

Sau khi normalize ve `xxx/yyyy`, neu nhieu dong cung ra cung mot so:

- tat ca dong trung deu vao `issue_rows`
- loai loi: `trung_so`
- khong giu dong dau o `Danh sach Excel`
- khong dua bat ky dong trung nao vao tap tinh missing

Ly do: user can thay tron cum trung de doi chieu, va tap missing can duoc tinh tren tap sach that su.

## Rule ngay bat thuong

Sau khi co tap dong dung format va dung nam:

1. Sort theo `so cong chung` tang dan.
2. Ngay cong chung phai tang dan hoac dung yen.
3. Neu mot dong co so lon hon nhung ngay lai som hon mot so nho hon truoc do, dong do vao `issue_rows`.

Loai loi:

- `ngay_bat_thuong`

Dong bi danh dau loi ngay bat thuong phai bi loai khoi tap tinh missing.

## Rule nhay bat thuong cung ngay

Ap dung theo nhom `cung ngay cong chung`.

Trong moi nhom ngay:

1. Sort theo `so cong chung` tang dan.
2. Tinh khoang cach giua moi cap so lien ke.
3. Neu khoang nhay vuot `10`, xem dong sau la `nhay_bat_thuong_cung_ngay`.

Vi du:

- Cung ngay `01/01/2026` co day `1, 2, 3, 20`
- `20` cach `3` la `17` > `10`
- `20` vao `issue_rows`

Dong bi loi nay bi loai khoi tap tinh missing de tranh lam phong danh sach so thieu.

Rule nay chi ap dung trong cung ngay, khong ap dung xuyen ngay.

## Rule tinh so con thieu

Tap tinh missing la tap sau khi da loai:

- sai format
- sai nam
- trung so
- ngay bat thuong
- nhay bat thuong cung ngay

Buoc tinh:

1. Lay `display_rows`
2. Sort theo `STT`
3. Tinh tu `min(STT)` den `max(STT)`
4. So nao khong co trong tap sach thi dua vao `missing_numbers`

Rule bat buoc:

- khong sinh missing cho nam ngoai khoang UI
- khong sinh missing tu dong loi
- khong dung cac dong loi de lam phong range tinh missing

## UI Qt can sua

Tab Excel doi thanh 3 vung nghiep vu:

### Vung 1 - Danh sach Excel

Cot hien:

- `Ngay`
- `So cong chung`
- `Dong Excel`

Co the giu `Gia tri goc` neu can debug, nhung khong dua len cot chinh mac dinh.

### Vung 2 - So con thieu

Cot hien:

- `So thieu`
- `Nam`
- `STT`

### Vung 3 - So loi, trung

Cot hien:

- `Loai loi`
- `Dong`
- `Ngay`
- `So goc`
- `So chuan`
- `Ly do`

## Scrollbar va kha nang xem danh sach dai

Ca 3 bang phai co:

- scrollbar doc hien ro o canh phai

Bang loi phai co them:

- scrollbar ngang

Muc tieu la user khong phai phu thuoc vao lan chuot de di chuyen trong danh sach dai.

## Status line

Status/log cua tab doi thanh:

`Excel=... | hop_le=... | thieu=... | loi=... | trung=...`

`Excel` la tong dong du lieu da doc.

`hop_le` la so dong trong `display_rows`.

`thieu` la so luong `missing_numbers`.

`loi` la tong dong trong `issue_rows`.

`trung` la so dong mang loai `trung_so`.

## Test bat buoc

### Service tests

- File co `1/2026`, `3/2026` thi missing la `2/2026`
- File co `296/2025`, `2047.2025`, `344/2006` trong khoang ngay 2026 thi khong sinh missing 2025/2006, chi vao loi
- Duplicate `60/2026` thi tat ca dong trung hien trong loi `trung_so`
- `66.2026` vao loi `sai_format`
- Dong so lon nhung ngay lui ve truoc vao loi `ngay_bat_thuong`
- Cung ngay co buoc nhay vuot `10` vao loi `nhay_bat_thuong_cung_ngay`

### UI tests

- Tab Excel co du 3 bang nghiep vu
- Moi bang co scrollbar doc
- Bang loi co scrollbar ngang
- Header cot dung theo spec moi
- Status line hien `Excel | hop_le | thieu | loi | trung`

## Anh xa tu plan cu sang plan moi

Plan Qt workflow hien tai can duoc cap nhat o cac task Excel:

- Task 1: doi tu parse rong sang parse nghiep vu chat theo nam va format
- Task 2: neu `web_list_service.py` con phu thuoc vao contract row cu thi phai dong bo lai
- Task 8: thay 4 bang `parsed/missing/warnings/parse errors` bang 3 vung nghiep vu moi

Folder scan, upload selection, selected upload API, regex catalog khong can lam lai.

## Ranh gioi khong lam trong dot nay

- Khong tu dong sua dong loi
- Khong mo rong sang scan folder
- Khong them thong ke nang cao ngoai cac nhom loi da chot
- Khong thay doi quy tac trich xuat Word/regex

## Tieu chi hoan thanh

Dot sua Tab 1 duoc xem la xong khi:

1. File Excel nam 2026 khong con sinh missing cho 2025/2006
2. User nhin vao thay ro 3 nhom du lieu:
   - danh sach sach
   - so con thieu
   - so loi, trung
3. Tap missing khong bi phong len boi dong loi
4. Test service va test UI moi deu pass
