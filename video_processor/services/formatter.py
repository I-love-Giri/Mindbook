def format_timestamp(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

'''
Visual Flow

7265 seconds
      │
      ▼
divmod(7265, 3600)
      │
      ├── Hours = 2
      └── Remaining = 65
                    │
                    ▼
           divmod(65, 60)
                    │
           ├── Minutes = 1
           └── Seconds = 5
                    │
                    ▼
             "02:01:05"
What is divmod()?

Think of it as division + remainder at the same time.

divmod(17, 5)

returns

(3, 2)

because:

17 ÷ 5 = 3
remainder = 2

It's equivalent to writing:

quotient = 17 // 5   # 3
remainder = 17 % 5   # 2

but divmod() gives you both values in one call, making the code shorter and cleaner.

'''