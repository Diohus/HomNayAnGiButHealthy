# Vòng 11 — Trang Hướng dẫn sử dụng trong app

Nội dung do PO viết sẵn: `docs/USER_GUIDE.md`. Dev **không viết lại nội dung**, chỉ đưa vào app. Bản `en` dịch sát nghĩa từ bản vi.
Làm sau vòng 10. Quy ước báo cáo như vòng 10.

## G1 — Trang `/help`
- `frontend/src/pages/Help.tsx`: hiển thị các mục trong `USER_GUIDE.md` theo đúng thứ tự. Mỗi mục là `<details>` với `id` cố định để liên kết thẳng tới mục đó: `start`, `today`, `log`, `week`, `chat`, `pantry`, `shopping`, `profile`, `settings`, `tips`, `faq`. Mở sẵn mục ghi trong hash (`/help#chat`), mặc định mở `start`.
- Nội dung đặt trong `i18n/vi.ts` + `en.ts` dưới khóa `help` (dạng `{ title, sections: [{ id, title, paragraphs: string[], bullets?: string[] }] }` hoặc tương đương). Không dùng thư viện markdown và không dùng `dangerouslySetInnerHTML`. Chữ đậm như **Tạo thực đơn** chỉ là tên nút, có thể bỏ định dạng đậm hoặc dùng `<strong>` qua cấu trúc dữ liệu.
- `/help` xem được **khi chưa đăng nhập**: route nằm ngoài `Shell`. Đã đăng nhập thì có nút quay lại; chưa đăng nhập thì có link "Đăng nhập".
- Style dùng lại `card`/`small muted` hiện có, đọc tốt ở chiều rộng 360 px, cả sáng lẫn tối.

## G2 — Lối vào
1. Trang đăng nhập (`Auth.tsx`): link "Hướng dẫn sử dụng" dưới form.
2. Cài đặt: mục "Hướng dẫn sử dụng" ở đầu trang, trỏ tới `/help`.
3. Lần đầu vào **Hôm nay** sau khi xong onboarding: banner nhỏ "Mới dùng? Xem hướng dẫn 1 phút", có nút ✕ để đóng. Đã đóng thì lưu `localStorage` key `hnag_help_seen`; bọc try/catch, nếu storage lỗi thì vẫn hiện banner và đóng được trong phiên.
4. Liên kết theo ngữ cảnh (link nhỏ "?" hoặc "Xem hướng dẫn"):
   - Trạng thái trống của Hôm nay ("Chưa có thực đơn…") → `/help#today`
   - Trang Trò chuyện, cạnh ô nhập → `/help#chat`
   - Trang Có sẵn → `/help#pantry`
   - Mục Giới hạn sức khỏe trong Cài đặt → `/help#settings`
- Thanh tab dưới cùng **không** thêm tab mới.

## G3 — PWA
- Service worker hiện có phải phục vụ được `/help` (SPA fallback) khi offline nếu trước đó đã tải app. Kiểm tra `pwa.ts`/`sw.js` hiện xử lý navigation request thế nào và báo lại. Chỉ sửa nếu `/help` offline bị trắng trang.

## Test
- `i18n.test.ts`: `vi.help` và `en.help` có cùng danh sách `id` mục, cùng số đoạn mỗi mục, không có chuỗi rỗng.
- Test logic banner: đã có `hnag_help_seen` thì không hiện; `localStorage` ném lỗi thì không crash. Tách ra hàm thuần nếu cần, giống `theme.ts`.
- `npm test`, `npm run build` pass. Backend không đổi.

## Tiêu chí nghiệm thu
- Nội dung trang `/help` (vi) khớp `docs/USER_GUIDE.md` từng ý. PO sẽ đối chiếu.
- Tất cả lối vào ở G2 trỏ đúng mục.
- Cập nhật `docs/CODEMAP.md` (route + component mới) và `README.md` (một dòng trỏ tới `docs/USER_GUIDE.md`).
