# Hướng dẫn sử dụng Hôm Nay Ăn Gì

> Nội dung gốc của trang **Hướng dẫn** trong app (`/help`). Sửa ở đây thì cập nhật cả `frontend/src/i18n/vi.ts` + `en.ts` (khóa `help.*`).

## Ứng dụng làm gì
Hôm Nay Ăn Gì gợi ý thực đơn mỗi ngày theo cơ thể, mục tiêu, dị ứng và khẩu vị của bạn. Số liệu dinh dưỡng lấy từ cơ sở dữ liệu USDA. Chỗ nào AI ước tính, app gắn nhãn **"AI ước tính"**.

**Lưu ý:** app không thay thế bác sĩ hay chuyên gia dinh dưỡng. Thực đơn chỉ để tham khảo và có sai số.

## Bắt đầu trong 3 bước
1. **Đăng ký** bằng email và mật khẩu (từ 8 ký tự).
2. **Nhập hồ sơ:** giới tính, tuổi, chiều cao, cân nặng, mức vận động, mục tiêu (giảm cân, giữ cân, tăng cơ). Thêm bệnh nền, dị ứng, chế độ ăn nếu có. App tính nhu cầu năng lượng và chất dinh dưỡng mỗi ngày.
3. Vào tab **Hôm nay** và bấm **Tạo thực đơn**.

## Tab Hôm nay: thực đơn trong ngày
- Mỗi bữa ghi tên món, nguyên liệu và khối lượng (gram, tính khi còn sống/khô). Vòng tròn trên cùng cho biết bạn đã ăn bao nhiêu so với mục tiêu.
- **+ / −** cạnh nguyên liệu: tăng hoặc giảm khối lượng. App giữ đúng phần bạn chỉnh và tự cân lại phần còn lại. Bấm **Bỏ cố định** để app tự chọn lại khối lượng đó.
- **Đổi món:** không thích bữa này thì bấm để đổi sang món khác. Các bữa còn lại giữ nguyên.
- **Cách chế biến:** AI gợi ý cách nấu. Gợi ý luôn tránh nguyên liệu bạn dị ứng.
- **Ngày trước / Ngày sau:** xem hoặc tạo thực đơn cho ngày khác.
- Một món chính không lặp lại quá 3 ngày liên tiếp.

## Ghi lại những gì đã ăn
- **Đã ăn:** ăn đúng như thực đơn thì bấm nút này ở bữa đó.
- **+ Thêm món đã ăn:** ăn món ngoài thực đơn thì tìm tên món, nhập số gram rồi ghi vào nhật ký.
- **📷 Chụp bữa ăn:** chụp hoặc chọn ảnh, đồng ý gửi ảnh cho AI, rồi bấm **Phân tích ảnh**. App tạo bản nháp gồm các món và số gram ước tính. Kiểm tra và sửa lại trước khi ghi. App không lưu ảnh.
- **Cân lại các bữa còn lại:** ăn nhiều hoặc ít hơn dự định thì bấm nút này. App điều chỉnh các bữa chưa ăn, mỗi bữa vẫn giữ một lượng tối thiểu. App không bắt bạn bù sang ngày hôm sau.

## Tab Tuần: tổng quan 7 ngày
Bấm **Tuần** trong tab Hôm nay để xem năng lượng 7 ngày so với mục tiêu và mức trung bình mỗi ngày. App liệt kê những chất bạn hay ăn thiếu (chất xơ, canxi, sắt…) và gợi ý thực phẩm để bổ sung. Tuần nào chưa ghi nhật ký thì app tính theo thực đơn.

## Tab Trò chuyện: nói chuyện như với người thật
Gõ tự nhiên, có dấu hay không dấu đều được. Ví dụ:
- "trưa nay ăn phở bò rồi" → ghi vào nhật ký và cân lại các bữa sau.
- "tối nay muốn ăn cá hồi" → đề xuất thực đơn có cá hồi.
- "hôm nay ăn 2 cây kem" → tính phần kem vào ngày và đề xuất cách cân đối.
- "tôi không thích ăn mướp đắng" → thêm vào danh sách không thích.

Mọi thay đổi chỉ áp dụng khi bạn bấm **Áp dụng**. Nếu chatbot hỏi lại "ý bạn là món nào?", hãy chọn món đúng.
Món không có trong dữ liệu (ví dụ một sản phẩm đóng gói) thì nhập theo **nhãn sản phẩm**: tên và số kcal, đạm, carb, béo trên 100 g.

## Tab Có sẵn: nguyên liệu trong nhà
Thêm những gì đã có trong tủ lạnh, kèm ngày và số gram. Sau đó **tạo lại thực đơn** của ngày đó để app ưu tiên dùng các nguyên liệu này.

## Tab Đi chợ
Chọn ngày bắt đầu, số ngày và số người ăn. App cộng nguyên liệu của các thực đơn đã tạo và trừ đồ có sẵn. Bấm **Sao chép** hoặc **Chia sẻ** để gửi danh sách cho người đi chợ.

## Tab Hồ sơ
- Sửa thông tin cơ thể, mục tiêu, dị ứng, chế độ ăn. App tính lại nhu cầu ngay khi bạn lưu.
- **Không thích:** món hoặc nguyên liệu bạn không muốn ăn. App sẽ hạn chế dùng nhưng không loại hẳn. Dị ứng thì khác: app loại hẳn.

## Cài đặt (⚙)
- **Giới hạn sức khỏe:** nếu bác sĩ đã cho giới hạn (natri, đạm, kali…), hãy nhập tay, chụp ảnh hoặc dán văn bản chỉ định. AI đọc tài liệu và tạo bản nháp. AI có thể đọc sai, nên hãy so với bản gốc rồi mới lưu.
- **Giao diện** (sáng/tối) và **Ngôn ngữ** (Tiếng Việt/English).
- **Tải dữ liệu của tôi:** tải về tệp JSON chứa toàn bộ dữ liệu. Tệp có dữ liệu sức khỏe, hãy cất giữ cẩn thận.
- **Xóa toàn bộ dữ liệu:** xóa vĩnh viễn, không khôi phục được.
- **Đăng xuất.**

## Mẹo
- Có thể cài app lên điện thoại: mở trên trình duyệt rồi chọn **Thêm vào màn hình chính**.
- Khi mất mạng, app vẫn hiện dữ liệu đã tải nhưng không cho sửa.
- Thực đơn chưa đạt mục tiêu thì app ghi rõ thiếu hoặc vượt chất nào và gợi ý thực phẩm bổ sung.

## Câu hỏi thường gặp
- **Vì sao không thấy món X?** Có thể món đó chứa thứ bạn dị ứng, không hợp chế độ ăn, hoặc chưa có trong dữ liệu. Hãy thử nhập theo nhãn sản phẩm trong tab Trò chuyện.
- **Số liệu chính xác đến đâu?** Đây là ước tính từ dữ liệu chuẩn. Món nấu thực tế có thể khác. Phần muối và nước mắm nêm thêm chưa được tính.
- **Dữ liệu sức khỏe có an toàn không?** Hồ sơ, giới hạn và tin nhắn chat đều được mã hóa. Ảnh gửi cho AI không được lưu.
