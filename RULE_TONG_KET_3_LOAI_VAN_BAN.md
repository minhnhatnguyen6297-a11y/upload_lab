# Rule Rut Gon Cho 3 Loai Van Ban

Ngay tong ket: 2026-04-07

## Nguyen tac chung

- Neu `tai_san` la `quyen su dung dat` thi ca 3 loai van ban deu dung chung 1 nguyen tac nhan dien.
- Khong uu tien cat tu cum mo dau dai nhu `Doi tuong cua Hop dong nay la ...`.
- Uu tien tim cum:
  - `quyen su dung dat`
  - hoac `quyen su dung dat va tai san gan lien voi dat`
- Sau cum nay phai co `co dia chi tai`.
- Co the xem day la anchor chinh cua block `tai_san`:
  - `quyen su dung dat ... co dia chi tai`

## Rule Lay `tai_san`

### Diem bat dau

- Bat dau tu cum `quyen su dung dat` khi phia sau co `co dia chi tai`.
- Ap dung chung cho:
  - Hop dong chuyen nhuong
  - Van ban cam ket tai san rieng
  - Van ban huy bo/sua doi/bo sung lien quan den hop dong chuyen nhuong

### Diem ket thuc

- Uu tien lay dung 1 block tai san, khong an sang doan sau.
- Dung truoc cac marker chuyen y, neu xuat hien:
  - `1.2`
  - `Dieu 2`
  - `Bang Hop dong nay`
  - `Bang van ban nay chung toi xac dinh`
  - `Hai vo chong chung toi cam doan`
  - `va duoc Cong chung vien`
- Neu la mau ngan, dung khi het phan thong tin:
  - Giay chung nhan
  - so vao so
  - ngay cap
  - cap nhat bien dong

## Theo Tung Loai Van Ban

### 1. Hop dong chuyen nhuong

- `tai_san` thuong la block day du.
- Van dung rule chung:
  - bat dau tu `quyen su dung dat ... co dia chi tai`
  - lay den het block thong tin dat/GCN

### 2. Van ban cam ket tai san rieng

- Mo ta `tai_san` ve cot loi khong khac voi hop dong chuyen nhuong.
- Neu noi dung la `quyen su dung dat` thi van dung cung rule:
  - bat dau tu `quyen su dung dat ... co dia chi tai`
  - lay den het block thong tin dat/GCN

### 3. Van ban huy bo / sua doi / bo sung

- Nhom nay nhan dien boi cac cum:
  - `huy bo`
  - `sua doi`
  - `bo sung`
- Co the xep vao nhom `cam ket - thoa thuan`.
- `tai_san` van theo cung nguyen tac nhan dien nhu tren, chi khac la doan lay thuong ngan hon, mang tinh tham chieu.
- Rule thuc te:
  - tim cum `quyen su dung dat ... co dia chi tai`
  - lay den het phan thong tin GCN / ngay cap / cap nhat bien dong

## Ngoai Le Ho So The Chap

- Ho so the chap ngan hang thuong khong co file Word day du cua hop dong, ma chi co 1 file tom tat / loi chung.
- Phan duong su uu tien doc theo nhan:
  - `Ben the chap`
  - `Ben nhan the chap`
- `Ben nhan the chap` co the la phap nhan, can giu du:
  - ten ngan hang / chi nhanh
  - dia chi dang ky
  - nguoi dai dien ky
- Neu file tom tat khong co block `tai_san` day du ma chi the hien ngay trong tieu de, cho phep fallback toi thieu:
  - `quyen su dung dat`
  - hoac `quyen su dung dat va tai san gan lien voi dat`
- Khi doc `.docx`, can giu dung thu tu paragraph/table; neu khong se rat de tach sai `Ben the chap` va `Ben nhan the chap`.

## Bo Sung Ho So Thua Ke

### 4. Van ban phan chia di san

- Tieu de canonical:
  - `Van ban phan chia di san`
- Khong dung cau truc `Ben A / Ben B`.
- Duong su cua mau nay la nhom nguoi ky o phan mo dau, thuong mo dau bang cum:
  - `Chung toi la nhung nguoi duoc huong di san ...`
- Rule lay `duong_su`:
  - start = dong `Chung toi la nhung nguoi duoc huong di san ...`
  - end = truoc:
    - `Chung toi tu nguyen lap Van ban nay ...`
    - hoac `Nguoi de lai di san:`
- Khong lay vao `duong_su` cac doan giai trinh o phan sau nhu:
  - `Nguoi de lai di san`
  - `Nguoi thua ke`
  - thong tin vo/chong/con duoc liet ke de xac dinh hang thua ke
- Nhan hien thi nen dung:
  - `NHUNG NGUOI HUONG DI SAN`

#### Rule lay `tai_san` cho van ban phan chia di san

- Uu tien bat dau tu dong mo ta tai san thuc te:
  - `quyen su dung dat ... co dia chi tai`
  - hoac `phan quyen su dung dat ... co dia chi tai`
- Neu mau co heading `Di san:` hoac `Di san cua ... de lai la:` thi block `tai_san` nam ngay sau heading nay.
- Dung truoc cac marker:
  - `Nguoi thua ke:`
  - `Nhung nguoi thua ke`
  - `Noi dung phan chia di san`
  - `Bang Van ban nay`
  - `Loi chung`
- Khong de block `tai_san` nuot sang phan ke khai hang thua ke, ty le huong, hoac loi cam doan.

### 5. Van ban tu choi nhan di san

- Tieu de canonical:
  - `Van ban tu choi nhan di san`
- Mau nay thuong chi co 1 nguoi lap van ban, mo dau bang cum:
  - `Toi la:`
- Khong dung cau truc `Ben A / Ben B`.
- Rule lay `duong_su`:
  - start = sau cum `Toi la:`
  - end = truoc:
    - `Nay, toi tu nguyen lap Van ban nay ...`
    - hoac `Theo quy dinh cua phap luat ...`
- Nhan hien thi nen dung:
  - `NGUOI TU CHOI NHAN DI SAN`

#### Rule lay `tai_san` cho van ban tu choi nhan di san

- Mau nay co the co nhieu tai san.
- Uu tien bat dau tu:
  - `1. Tai san thu nhat:`
  - hoac dong `quyen su dung dat ... co dia chi tai`
- Neu co `2. Tai san thu hai`, `3. Tai san thu ba` thi giu cung 1 block `tai_san`.
- Dung truoc cac marker:
  - `Bang Van ban nay, toi ... tu choi nhan ky phan thua ke`
  - `Toi xin cam doan`
  - `Nguoi tu choi huong di san`
  - `Loi chung`
- Neu trong tai san thu hai/thu ba co bang thi phai giu nguyen thu tu paragraph/table de khong mat dong thong tin thua dat.

### Rule so cong chung cho nhom thua ke

- Nhom thua ke co the dung dinh dang:
  - `2433.2025/PCDS/CCGD`
  - `2233.2025/TCDS/CCGD`
- Khi scan/raw co the giu du hau to loai van ban:
  - `2433/2025/PCDS/CCGD`
  - `2233/2025/TCDS/CCGD`
- Khi dua vao web field `so_cong_chung`, can rut gon ve:
  - `2433/2025`
  - `2233/2025`

## Ket Luan Ngan

- Rule cot loi khong nen tach qua phuc tap theo 3 loai van ban.
- Neu `tai_san` la `quyen su dung dat` thi dung 1 rule chung:
  - start = `quyen su dung dat ... co dia chi tai`
  - end = het block thong tin dat/GCN, dung truoc doan noi y khac
- Khac nhau chu yeu o do dai block:
  - chuyen nhuong: day du hon
  - cam ket: gan nhu giong chuyen nhuong
  - huy bo/sua doi/bo sung: ngan hon, mang tinh tham chieu
