"""Chatbot hiểu ý người dùng ("tôi muốn ăn gà", "tôi muốn ăn kem").

- parser: hiểu câu (LLM có schema + parser quy tắc dự phòng). LLM KHÔNG quyết định vai trò món hay số liệu.
- engine: logic xác định — phân loại món chính/phụ/ăn vặt từ catalog, gọi planner, đề xuất cheat day có giới hạn.
Mọi thay đổi thực đơn chỉ được áp dụng khi người dùng xác nhận một đề xuất.
"""
