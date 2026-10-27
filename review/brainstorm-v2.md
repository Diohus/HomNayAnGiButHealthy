# Brainstorm v2 — Vấn đề, giải pháp, ưu tiên (PO)

## Định hướng mới của chủ sản phẩm (2026-10-28)
- App **không chuyên về y tế**: không có bác sĩ can thiệp. App chỉ **đề xuất**, chấp nhận có sai số và nói rõ điều đó.
- Nếu người dùng có chỉ định của bác sĩ ⇒ **họ tự nhập**, hoặc **đưa ảnh/văn bản** để app trích xuất vào dữ liệu người dùng.
- Xử lý ngôn ngữ ưu tiên **LLM** thay vì rule-based đơn giản: người dùng viết tiếng địa phương, sai chính tả, không dấu. Rule-based chỉ còn là lưới an toàn và fallback.
- Nguyên tắc giữ nguyên: số liệu dinh dưỡng do bộ tính toán/DB đưa ra. LLM chỉ được ra số ở những chỗ ghi rõ "AI ước tính" và người dùng sửa được.

## Vấn đề hiện tại (PO quan sát từ code và E2E)
| # | Vấn đề | Hệ quả với người dùng |
|---|---|---|
| V1 | Có bệnh nền nhạy cảm (thận, tim, gan, mang thai, cho con bú) ⇒ **bị chặn sinh thực đơn** cho tới khi "chuyên gia xác nhận" | Trái với định hướng mới; người dùng bị kẹt ngay từ đầu |
| V2 | Chatbot dò món bằng alias cứng (`foods/matching.py`). "ga ran", "trứg", "bún bò huế", "xôi gà", từ địa phương ("trái thơm", "củ sắn") ⇒ không nhận ra ⇒ bắt nhập nhãn | Chatbot tỏ ra "ngu", người dùng bỏ dùng |
| V3 | Không có chỗ ghi nhận "đã ăn". Vòng tiến độ chỉ phản ánh **kế hoạch**, không phản ánh **thực tế** | Không giống YAZIO; người dùng không biết hôm nay mình đã ăn bao nhiêu |
| V4 | Chỉ có "Tạo lại" cả ngày; không đổi được **một món**, không nói được "tôi không thích cá" | Ghét một món thì phải đổi cả ngày |
| V5 | Không có danh sách đi chợ, dù planner đã dùng chung nguyên liệu giữa các bữa | Mất giá trị thực tế lớn nhất của thực đơn tuần |
| V6 | Chỉ 80 nguyên liệu / 26 món, thiếu nhiều món Việt phổ biến (phở, bún, xôi, canh chua…) | Thực đơn lặp, thiếu "chất Việt" |
| V7 | Pantry gắn theo **ngày**, không phải kho tồn liên tục; không có khẩu phần cho cả gia đình | Phải nhập lại mỗi ngày; nấu cho 3 người thì tự nhân |
| V8 | Mỗi lần bấm công thức là một lần gọi LLM (5–8 s), không có cache | Chậm, tốn tiền |

## Danh sách tính năng — xếp ưu tiên 1 (cần nhất) → 10

| Ưu tiên | Tính năng | Giải quyết | Cải thiện trải nghiệm | Hướng kỹ thuật (LLM-first) |
|---|---|---|---|---|
| **1** | **Giới hạn sức khỏe do người dùng tự cung cấp** (nhập tay / ảnh / văn bản) và bỏ chặn y tế | V1 | Người bệnh nền dùng được ngay; có đơn bác sĩ thì chụp ảnh là xong, không phải gõ | LLM vision (đã thử: gpt-6-luna đọc ảnh đơn, trích đúng natri/đạm/kali) ⇒ JSON có schema + trích dẫn nguyên văn ⇒ quy đổi đơn vị và kiểm tra khoảng bằng code ⇒ **người dùng duyệt/sửa rồi mới lưu**. Không lưu ảnh. Thiếu giới hạn ⇒ dùng mức chung, hiện cảnh báo sai số |
| **2** | **Hiểu món ăn bằng LLM** (sai chính tả, địa phương, không dấu, món ghép) | V2 | Nói sao cũng hiểu, không bị bắt nhập nhãn vô lý | Tìm ứng viên (fuzzy + alias) top-k từ catalog ⇒ LLM chọn mã **trong danh sách cho sẵn** (enum, không bịa mã) + độ tin cậy. Món ghép (phở bò) ⇒ LLM phân rã thành nguyên liệu catalog + khối lượng, gắn nhãn "AI ước tính, sai số cao", người dùng sửa được. Rule-based làm fallback |
| **3** | **Nhật ký "đã ăn"** (tick bữa theo kế hoạch, ghi món ngoài kế hoạch) | V3 | Vòng tiến độ phản ánh thực tế; tự cân bằng các bữa còn lại | Tick ⇒ ghi log; ăn ngoài kế hoạch qua chat (dùng #2) ⇒ đề xuất cân lại các bữa **chưa ăn** (solver giữ cố định bữa đã ăn) |
| **4** | **Đổi một món / một bữa + món không thích** | V4 | Đổi nhanh 1 chạm; app "nhớ khẩu vị" | Solver sinh lại 1 slot, cấm món cũ; danh sách "không thích" là ràng buộc mềm (khác dị ứng là ràng buộc cứng); LLM hiểu "tôi không ăn được hành" ⇒ cập nhật preference sau khi người dùng xác nhận |
| **5** | **Danh sách đi chợ** cho N ngày | V5 | Đi chợ một lần cho cả tuần, đã trừ phần có sẵn | Thuần tính toán: gộp nguyên liệu theo nhóm, quy về đơn vị mua (quả trứng, bó rau) bằng `portion` có sẵn; tick đã mua; xuất văn bản để chia sẻ |
| 6 | Mở rộng CSDL món Việt | V6 | Thực đơn đa dạng, quen thuộc | Pipeline: LLM gợi ý FDC ID/thành phần cho món mới ⇒ **người duyệt** ⇒ seed; món chưa duyệt gắn "chưa xác minh" |
| 7 | Chụp ảnh bữa ăn để ghi nhật ký | V3 | Ghi nhận nhanh nhất có thể | Vision ⇒ danh sách món + ước lượng khẩu phần ⇒ map catalog (dùng #2) ⇒ người dùng xác nhận |
| 8 | Nấu cho cả nhà (số người) + kho có sẵn liên tục | V7 | Thực tế với gia đình Việt | Hệ số khẩu phần khi hiển thị/đi chợ; pantry tồn kho có trừ dần |
| 9 | Cache công thức + chọn model nhẹ cho parse + đo độ trễ/chi phí (không chứa dữ liệu sức khỏe) | V8 | Nhanh hơn, rẻ hơn | Cache theo (món, tập nguyên liệu, dị ứng, ngôn ngữ) |
| 10 | Onboarding hội thoại + PWA cài lên điện thoại | — | Đăng ký nhanh, dùng như app | LLM hỏi đáp điền hồ sơ, form vẫn là nguồn sự thật |

## Kế hoạch chu kỳ v2 (3 vòng dev)
- **Vòng 4:** #1 (giới hạn sức khỏe tự cung cấp + trích xuất ảnh/văn bản, bỏ chặn y tế).
- **Vòng 5:** #2 (hiểu món bằng LLM) + #4 (đổi món, không thích).
- **Vòng 6:** #3 (nhật ký đã ăn) + #5 (danh sách đi chợ).
- Mục 6–10 để brainstorm v3 xếp lại ưu tiên.
