# Chuan — Tiêu chí Fee & Volume cho Solana Meme Coin

Bộ tiêu chí heuristic để đánh giá snapshot meme coin Solana trong giai đoạn tích lũy/đi ngang. `fee.json` là cấu hình duy nhất cho hard filter và rubric; `src/chuan/scorer.py` tính điểm xác định, không gọi API và không thực hiện giao dịch.

## Thành phần
- [`fee.json`](./fee.json): đầu vào, ngưỡng reject, trọng số và các khoảng điểm v1.2.
- [`src/chuan/scorer.py`](./src/chuan/scorer.py): tính tỷ lệ từ số USD gốc, kiểm tra dữ liệu, hard filter và breakdown điểm.
- [`scripts/evaluate_token.py`](./scripts/evaluate_token.py): CLI chấm một snapshot JSON.
- [`src/chuan/backtest.py`](./src/chuan/backtest.py): đánh giá CSV snapshot với forward return đã biết, báo cáo theo tháng.
- [`tests/test_scorer.py`](./tests/test_scorer.py): kiểm thử ngưỡng, dữ liệu thiếu và trường hợp biên.

## Scoring
Tổng tối đa 100 điểm: V/MC 30, Liquidity/MC 20, Fee/Volume 15, Volume/Liquidity 15, CR10 + tăng trưởng holder 10, cấu trúc giá 10. Các dải điểm và giới hạn đều đọc từ `fee.json`.

Hard filter được áp dụng trước kết luận: tuổi <48h, MC ngoài $50k–$5m, liquidity <$20k, Liquidity/MC <5%, V/MC <2% hoặc >80%, Fee/Volume <0.15% hoặc >1.5%, Volume/Liquidity >5x sẽ bị `reject`. Nếu thiếu dữ liệu, kết quả là `incomplete` (không tự thay bằng 0). Trạng thái còn lại: `pass` ≥70; `warn` 60–69.99; `fail` <60. Các điểm ngoài vùng lý tưởng vẫn được tính theo rubric; xem `components`, `warnings` và `reject_reasons` trong kết quả.

Tỷ lệ được tính thống nhất: `V/MC = volume_24h_usd / market_cap_usd * 100`; `Liquidity/MC = liquidity_usd / market_cap_usd * 100`; `Fee/Volume = fee_24h_usd / volume_24h_usd * 100`; `Volume/Liquidity = volume_24h_usd / liquidity_usd`. USD, cửa sổ 24h và phạm vi pool phải nhất quán. CR10 cần loại trừ pool/LP, burn, treasury và ví sàn đã biết nếu nguồn dữ liệu hỗ trợ.

## Cài đặt và kiểm thử
Python 3.10+; không cần thư viện runtime ngoài Python chuẩn.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
pytest
```

## Chấm một snapshot
Tạo JSON với các trường dưới đây (tỷ lệ holder growth và CR10 dùng đơn vị phần trăm; nhập USD cho tiền; `pool_fee_tier_pct` là tùy chọn):

```json
{
  "age_hours": 72,
  "market_cap_usd": 800000,
  "volume_24h_usd": 144000,
  "liquidity_usd": 96000,
  "fee_24h_usd": 792,
  "cr10_pct": 28,
  "holder_growth_24h_pct": 1.5,
  "price_action": "consolidation"
}
```

```bash
python scripts/evaluate_token.py --input token.json
# Hoặc sau khi cài: chuan-evaluate --input token.json
cat token.json | python scripts/evaluate_token.py --input -
```

## Backtest
Mỗi hàng CSV là một snapshot tại `timestamp`; các feature chỉ được lấy tại/thời điểm đó. `forward_7d_return_pct` là kết quả sau snapshot, không được dùng làm feature. Bao gồm cả token đã chết/mất thanh khoản với kết quả phù hợp (thường là mất vốn), tránh survivorship bias.

Cột bắt buộc: `token,timestamp,age_hours,market_cap_usd,volume_24h_usd,liquidity_usd,fee_24h_usd,cr10_pct,holder_growth_24h_pct,price_action,forward_7d_return_pct`.

```bash
python -m chuan.backtest --input snapshots.csv --output report.json
# hoặc: chuan-backtest --input snapshots.csv --return-column forward_7d_return_pct
```

Báo cáo có cohort pass/non-pass, hit rate theo ngưỡng forward return (+20% mặc định, đổi với `--positive-return-pct`) và thống kê theo tháng snapshot. Đây là đánh giá mô tả của rubric cố định, không tự tối ưu ngưỡng hay tạo dự báo. Để kiểm định nghiêm túc, dùng walk-forward theo thời gian: chốt ngưỡng trên giai đoạn cũ, đánh giá trên giai đoạn tương lai chưa dùng; tách các mẫu cùng token để tránh rò rỉ; tính phí, slippage và outcome rug/delist. Cần đủ nhiều token và các chế độ thị trường trước khi tin vào kết quả.

## Giới hạn và nguồn tham khảo
Ngưỡng là heuristic, chưa được chứng minh tạo lợi nhuận. Fee/volume quan sát được không nhất thiết bằng fee tier danh nghĩa, nên khác biệt chỉ cảnh báo. Scorer hiện không chấm độ ổn định fee ba ngày vì cần chuỗi dữ liệu lịch sử. Kiểm tra thêm quyền mint/freeze, thanh khoản có thể rút, phân phối ví và rủi ro hợp đồng trước mọi quyết định; đây không phải lời khuyên tài chính.

Tham khảo cấu trúc/ý tưởng tổ chức analytics (không sao chép code hay ngưỡng): [0xdariel/solana-token-scanner](https://github.com/0xdariel/solana-token-scanner) cho tách module và heuristic có caveat; [Purfecto/Solana-Token-Mapper](https://github.com/Purfecto/Solana-Token-Mapper) cho phân tích holder/flow và giới hạn rate/API. Bộ repo tham khảo không phải nguồn xác nhận các ngưỡng này.
