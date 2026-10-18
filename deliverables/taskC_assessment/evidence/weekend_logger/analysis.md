# Weekend logger analysis (2026-10-16T11:10:32.810000+00:00 → 2026-10-16T12:12:20.862000+00:00, 64 polls)

## AAPL (AAPL)
- polls 64, quote errors 0, candle errors 0, latency p50 quote 0.166 s / candle 0.514 s (max 3.333 s)
- delay baseline while open (quote age): {'p10': 901.9, 'median': 907.4, 'p90': 941.1}; candle age while open: {'median': 920.9, 'p90': 980.9, 'max': 1112.8}
- max quote age 1056.9 s, max candle age 1112.8 s; closed-period: None
- freeze runs while expected open (>= 30 min without a new 1m candle): none
- session transitions observed: [{'at': '2026-10-16T11:10:32.810000+00:00', 'open_expected': True, 'last_candle_time': '2026-10-16T10:52:00.000Z', 'quote_time': '2026-10-16T10:54:46.000Z'}]

## EURUSD (EUR/USD)
- polls 64, quote errors 0, candle errors 0, latency p50 quote 0.166 s / candle 0.698 s (max 6.364 s)
- delay baseline while open (quote age): {'p10': 900.9, 'median': 900.9, 'p90': 901.6}; candle age while open: {'median': 920.9, 'p90': 920.9, 'max': 932.8}
- max quote age 901.9 s, max candle age 932.8 s; closed-period: None
- freeze runs while expected open (>= 30 min without a new 1m candle): none
- session transitions observed: [{'at': '2026-10-16T11:10:32.810000+00:00', 'open_expected': True, 'last_candle_time': '2026-10-16T10:55:00.000Z', 'quote_time': '2026-10-16T10:55:33.000Z'}]

## TSLA (TSLA)
- polls 64, quote errors 0, candle errors 0, latency p50 quote 0.166 s / candle 0.566 s (max 5.964 s)
- delay baseline while open (quote age): {'p10': 900.9, 'median': 901.9, 'p90': 904.9}; candle age while open: {'median': 920.9, 'p90': 920.9, 'max': 932.8}
- max quote age 906.9 s, max candle age 932.8 s; closed-period: None
- freeze runs while expected open (>= 30 min without a new 1m candle): none
- session transitions observed: [{'at': '2026-10-16T11:10:32.810000+00:00', 'open_expected': True, 'last_candle_time': '2026-10-16T10:55:00.000Z', 'quote_time': '2026-10-16T10:55:32.000Z'}]

## ES (/ESZ26:XCME)
- polls 64, quote errors 0, candle errors 0, latency p50 quote 0.166 s / candle 0.509 s (max 6.18 s)
- delay baseline while open (quote age): {'p10': 900.9, 'median': 900.9, 'p90': 900.9}; candle age while open: {'median': 920.9, 'p90': 920.9, 'max': 932.8}
- max quote age 901.9 s, max candle age 932.8 s; closed-period: None
- freeze runs while expected open (>= 30 min without a new 1m candle): none
- session transitions observed: [{'at': '2026-10-16T11:10:32.810000+00:00', 'open_expected': True, 'last_candle_time': '2026-10-16T10:55:00.000Z', 'quote_time': '2026-10-16T10:55:32.000Z'}]

