---
name: sol-meme-fee
description: "Đánh giá snapshot meme coin Solana theo tiêu chí Fee, Volume và thanh khoản. Dùng khi lọc coin, check V/MC hoặc phân tích phase tích lũy/đi ngang."
type: workflow
lifecycle: active
---

# Sol Meme Fee — workflow đánh giá snapshot

Dùng scorer offline để áp dụng thống nhất các ngưỡng trong `fee.json`. Đây là bộ lọc heuristic, không phải khuyến nghị giao dịch.

## Cách dùng
1. Thu thập snapshot có timestamp và nguồn: `age_hours`, `market_cap_usd`, `volume_24h_usd`, `liquidity_usd`, `fee_24h_usd`, `cr10_pct`, `holder_growth_24h_pct`, `price_action`.
2. Đồng bộ cửa sổ 24h, quote currency và phạm vi pool giữa volume, liquidity, fee. Đừng coi fee tier danh nghĩa là fee/volume thực tế.
3. Chạy `python scripts/evaluate_token.py --input token.json` (JSON fields được mô tả trong README); dùng `--config` nếu config không nằm ở root.
4. Đọc `status`, `score`, `components`, `missing_fields`, `reject_reasons`, `warnings`. `incomplete` không phải pass; không tự điền giá trị thiếu.
5. Nếu dùng để đánh giá ngưỡng, tạo CSV có feature tại snapshot và forward return tách biệt, rồi chạy `python -m chuan.backtest --input snapshots.csv`. Đưa token rugged/delisted vào dữ liệu và dùng đánh giá walk-forward ngoài mẫu.

## Ý nghĩa trạng thái
- `reject`: vi phạm ít nhất một hard filter; điểm số không thể override.
- `incomplete`: thiếu input cần thiết hoặc price_action không nhận diện được.
- `pass`: không vi phạm hard filter và đạt ngưỡng 70/100.
- `warn`: 60–69.99; `fail`: dưới 60.

Scoring chi tiết và các vùng biên được cấu hình trong `fee.json`. Backtest hiện là thống kê mô tả, không tự động tối ưu threshold hoặc fetch dữ liệu. Tham khảo README về giới hạn, chất lượng dữ liệu và risk controls.
