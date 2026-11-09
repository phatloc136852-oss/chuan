# Chuan — Tiêu chí Fee & Volume cho Solana Meme Coin

Bộ tiêu chí chuẩn để đánh giá coin meme Solana ở giai đoạn **Accumulation + Consolidation**.

## Files
- [`fee.json`](./fee.json) — Ngưỡng chi tiết + scoring (phiên bản 1.1)
- [`SKILL.md`](./SKILL.md) — Hướng dẫn dùng skill trong Auto Filter / Auto 3V

## Ngưỡng chính (v1.1)
- **V/MC 24h**: 5% – 30% (lý tưởng)
- **Liquidity/MC**: ≥ 5%
- **Fee/Volume**: 0.25% – 1.0%
- **Pass threshold**: ≥ 70/100 điểm

Dữ liệu được điều chỉnh dựa trên nguồn thực tế Solana meme 2026.

## Cách dùng
1. Đọc `fee.json` để lấy ngưỡng.
2. Tính các tỷ lệ V/MC, Liquidity/MC, Fee/Volume, Volume/Liquidity.
3. Chấm điểm theo scoring.
4. Pass nếu ≥ 70 điểm.
