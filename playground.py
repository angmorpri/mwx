# 2025/08/22
"""
playground.py - Non-pytest testing
"""


from mwx.util import Money

if __name__ == "__main__":
    m = Money(12343.891)
    print(10 <= m < 30)
