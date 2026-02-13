# Hướng dẫn crawl và merge dữ liệu (Batdongsan)

Tài liệu này hướng dẫn nhóm chạy 2 notebook:
- notebooks/01_crawling.ipynb
- notebooks/merge_data.ipynb

## 1) Cấu hình chung

1. Cài thư viện
   - Mở terminal tại thư mục gốc project (Lab1---Data-Visualization-)
   - Cài đặt:
     ```powershell
     pip install -r requirements.txt
     ```

2. Cookie truy cập
   - Mỗi người tự lấy cookie của mình (không chia sẻ)
   - Set biến môi trường:
     ```powershell
     $env:BDS_COOKIE = "<cookie_cua_ban>"
     ```

3. Chạy notebook từ thư mục gốc
   - Nếu mở notebook, đảm bảo `project_root` trỏ đúng thư mục có `src/` và `data/`

## 2) Notebook 01_crawling.ipynb

### Cell 1: Lấy link chi tiết
- Mục tiêu: crawl link href của các tin đăng từ trang listing.
- Đầu vào:
  - `pages`: danh sách số trang cần crawl (vd: `list(range(2, 501))`).
  - `headless`: `True`/`False` (False nếu cần mở trình duyệt để xác thực).
  - `max_links`: giới hạn số link mỗi trang (None = lấy hết).
- Đầu ra:
  - Lưu file: `data/processed/links_p{page}.csv`
  - Cột chính: `detail_url`

### Cell 2: Lấy chi tiết từng link
- Mục tiêu: đọc các file links và crawl chi tiết từng bất động sản.
- Cấu hình:
  - `Xs`: danh sách số trang cần xử lý (vd: `list(range(2, 501))`).
  - Mỗi `X` sẽ đọc file: `data/processed/links_p{X}.csv`
- Đầu ra:
  - Lưu file: `data/raw/scraped/scraped_results_p{X}.csv`
  - File đã bao gồm các trường như: ID, Giá (tỷ đồng), Diện tích, Số phòng, Hướng nhà, Địa chỉ, Giá đã tăng 1 năm qua (%), ...

## 3) Notebook merge_data.ipynb

- Mục tiêu: merge các file `scraped_results_pX.csv` thành 1 file tổng.
- Cấu hình:
  - `X`: trang bắt đầu (vd: 2)
  - `Y`: trang kết thúc (vd: 50)
- Đầu vào:
  - Thư mục `data/raw/scraped/`
  - Các file: `scraped_results_p{X}.csv` ... `scraped_results_p{Y}.csv`
- Đầu ra:
  - Lưu file: `data/raw/merge/scraped_results_{X}to{Y}.csv`
  - Nếu thiếu file trong khoảng, notebook sẽ in danh sách file bị thiếu.

## 4) Thứ tự chạy đề nghị

1. Chạy Cell 1 của 01_crawling.ipynb để tạo links_pX.csv
2. Chạy Cell 2 của 01_crawling.ipynb để tạo scraped_results_pX.csv
3. Chạy merge_data.ipynb để gộp file tổng

## 5) Lưu ý

- Tránh chạy nhiều session song song để giảm rủi ro bị chặn.
- CSV đã được ignore trong .gitignore cho lần phát sinh mới.
