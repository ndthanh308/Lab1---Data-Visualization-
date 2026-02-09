# Phân tích dữ liệu TMĐT Việt Nam (Shopee/Lazada/Tiki)

## Thành viên nhóm
- 23127256 - Trần Thị Xuân Tài — Đóng góp: __%  
- 23127315 - Nguyễn Trần Thiên An — Đóng góp: __%  
- 23127351 - Lê Minh Đức — Đóng góp: __%  
- 23127398 - Đinh Xuân Khương — Đóng góp: __%  
- 23127538 - Nguyễn Đồng Thanh — Đóng góp: __%  

## Bài toán chung
Phân tích dữ liệu thương mại điện tử tại Việt Nam từ các sàn như Shopee, Lazada, Tiki nhằm khám phá xu hướng giá, mức độ phổ biến, và các yếu tố ảnh hưởng đến hiệu suất sản phẩm.

## Mục tiêu SMART (cho từng thành viên)
> Điền mục tiêu SMART cho từng thành viên (Cụ thể - Đo lường được - Khả thi - Liên quan - Có thời hạn)

- **Trần Thị Xuân Tài**: (Specific) …; (Measurable) …; (Achievable) …; (Relevant) …; (Time-bound) …
- **Nguyễn Trần Thiên An**: (Specific) …; (Measurable) …; (Achievable) …; (Relevant) …; (Time-bound) …
- **Lê Minh Đức**: (Specific) …; (Measurable) …; (Achievable) …; (Relevant) …; (Time-bound) …
- **Đinh Xuân Khương**: (Specific) …; (Measurable) …; (Achievable) …; (Relevant) …; (Time-bound) …
- **Nguyễn Đồng Thanh**: (Specific) …; (Measurable) …; (Achievable) …; (Relevant) …; (Time-bound) …

## Cấu trúc thư mục
```
.
├── data/
│   ├── raw/                # Dữ liệu thô (crawled)
│   └── processed/          # Dữ liệu đã xử lý
├── notebooks/
│   ├── 01_crawling.ipynb
│   ├── 02_preprocessing.ipynb
│   ├── member_Tai/
│   ├── member_An/
│   ├── member_Duc/
│   ├── member_Khuong/
│   └── member_Thanh/
├── reports/
│   └── figures/            # Biểu đồ/ảnh
├── src/
│   ├── scrapers/           # Mã thu thập dữ liệu
│   └── utils/              # Hàm tiện ích
└── requirements.txt 
```

## Thiết lập môi trường
1. Tạo môi trường ảo (khuyến nghị):
```
python -m venv .venv
```
2. Kích hoạt môi trường:
- Windows:
```
.venv\Scripts\activate
```
- macOS/Linux:
```
source .venv/bin/activate
```
3. Cài đặt thư viện:
```
pip install -r requirements.txt
```

## Chạy notebooks
- Mở thư mục dự án trong VS Code hoặc Jupyter.
- Chạy lần lượt:
  - notebooks/01_crawling.ipynb
  - notebooks/02_preprocessing.ipynb
- Các notebook cá nhân đặt trong thư mục notebooks/member_*/

## Ghi chú bắt buộc (Lab 01)
- **Không sử dụng dataset có sẵn (Kaggle, v.v.)**.
- Dữ liệu phải **tự thu thập** bằng Web Scraping hoặc API.
- Lưu dữ liệu thô và dữ liệu đã xử lý vào đúng thư mục.
- Giữ nguyên **output của notebook** khi nộp bài.
- Nộp kèm **báo cáo PDF** trong thư mục reports/.
