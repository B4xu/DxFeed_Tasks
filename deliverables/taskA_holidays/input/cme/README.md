# CME manual input

cmegroup.com returns HTTP 403 to automated clients and its Data Terms of Use prohibit
scraping, so the CME adapter reads files you download by hand into this folder.

Either drop the per-holiday PDFs from
https://www.cmegroup.com/tools-information/holiday-calendar.html (Equity Index section) here,
or write a CSV with this header (times are Chicago local, HH:MM):

```
date,holiday_name,status,close_time_local,product_scope,source_url
2026-11-26,Thanksgiving Day,early_close,12:00,CME Globex US Equity Index futures,https://www.cmegroup.com/...pdf
```

`status` is `closed` or `early_close`. Nothing in this folder except this README is committed.
