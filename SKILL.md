---
name: sol-meme-fee
description: "Đánh giá coin meme Solana theo tiêu chí Fee và Volume 24h cho giai đoạn Accumulation + Consolidation. Dùng khi lọc coin, auto filter, check V/MC, hoặc phân tích potential meme trên Sol."
type: workflow
lifecycle: active
---

# Sol Meme Fee — Tiêu chí Fee & Volume cho Accumulation

Skill dùng để áp dụng bộ tiêu chí chuẩn Fee / Volume / V/MC khi lọc hoặc đánh giá coin meme Solana đang ở giai đoạn Accumulation và Consolidation.

## Khi nào dùng
- User yêu cầu lọc coin theo fee, volume, V/MC.
- Phân tích potential meme coin cho Auto Grok / auto trade.
- Kiểm tra coin có phù hợp giai đoạn tích lũy không.
- Tích hợp vào phần Auto 3V / Auto Filter.

## Workflow chính
1. Đọc file `fee.json` trong thư mục skill để lấy ngưỡng chính xác.
2. Thu thập dữ liệu coin: Market Cap, Volume 24h, Liquidity, Fee 24h (nếu có), Holder.
3. Tính các tỷ lệ:
   - Fee/Volume 24h
   - Volume/Market Cap (V/MC)
   - Volume/Liquidity
   - Liquidity/MC
4. So sánh với ngưỡng trong `fee.json`.
5. Tính điểm theo scoring (tối đa 100, pass ≥ 70).
6. Trả về kết luận: Pass / Fail / Cảnh báo + lý do chi tiết.

## Ngưỡng quan trọng (tóm tắt từ fee.json v1.1)
- **V/MC 24h**: **5% – 30%** (lý tưởng cho Accumulation). <2% hoặc >80% → loại.
- **Fee/Volume**: 0.25% – 1.0% (đúng fee tier pool).
- **Volume/Liquidity**: 0.5x – 2.0x.
- **Liquidity/MC**: ≥ 5% (tốt ≥ 8–10%).
- Fee phải ổn định nhiều ngày, không spike rồi im.

## Tích hợp Auto 3V
Khi chạy Auto Filter / Auto 3V:
- Ưu tiên áp dụng scoring từ `fee.json`.
- Kết hợp với các tiêu chí khác (Larpcheck, holder, price action) nếu có.
- Ưu tiên coin có volume ổn định 3–7 ngày hơn volume spike một lần.
- Luôn kiểm tra fee tier thực tế của pool thay vì hardcode.

## Nguồn dữ liệu ưu tiên
- Birdeye, DexScreener (volume, liquidity, MC)
- DefiLlama / MemeFees (tham khảo fee structure)
- Solscan / Bubblemaps (holder)

## Output mẫu
- Điểm số /100
- Các tỷ lệ đã tính
- Kết luận Pass/Fail
- Ghi chú cảnh báo (nếu có)

Xem chi tiết đầy đủ trong `fee.json`.
