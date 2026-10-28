// Vòng 11: logic thuần của trang Hướng dẫn + banner "Mới dùng?" (tách khỏi component để test, giống theme.ts).
export const HELP_SEEN_KEY = "hnag_help_seen";
export const DEFAULT_SECTION = "start";

/** Banner hiện khi chưa đóng lần nào. Storage lỗi/bị chặn ⇒ vẫn hiện (đóng được trong phiên). */
export function shouldShowHelpBanner(): boolean {
  try {
    return !localStorage.getItem(HELP_SEEN_KEY);
  } catch {
    return true;
  }
}

export function dismissHelpBanner(): void {
  try {
    localStorage.setItem(HELP_SEEN_KEY, "1");
  } catch {
    /* trình duyệt chặn storage: chỉ ẩn trong phiên hiện tại */
  }
}

/** Mục được mở sẵn: id trong hash (`#chat`) nếu có, không thì mục mặc định. */
export function openSectionId(hash: string, ids: string[]): string {
  const id = decodeURIComponent(hash.replace(/^#/, ""));
  return ids.includes(id) ? id : DEFAULT_SECTION;
}

/** "Bấm **Tạo thực đơn**" ⇒ đoạn chữ thường/đậm (tên nút). Không dùng markdown hay innerHTML. */
export function rich(text: string): { text: string; strong: boolean }[] {
  return text.split(/\*\*(.+?)\*\*/).map((s, i) => ({ text: s, strong: i % 2 === 1 })).filter((p) => p.text);
}
