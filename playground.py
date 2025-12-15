# 2025/08/22
"""
playground.py - Non-pytest testing
"""


from pathlib import Path

from mwx import Wallet

TESTING_DB_PATH = Path(__file__).parent / "tests" / "data" / "Sep_10_2025_ExpensoDB"


if __name__ == "__main__":
    wallet = Wallet(TESTING_DB_PATH)

    til_march = wallet.budget("@Personales", "2025-03")
    march_pos = wallet.sum("@Personales", "2025-03", flow=+1)
    march_neg = wallet.sum("@Personales", "2025-03", flow=-1)

    print("Presupuesto hasta marzo: ", til_march)
    print("Total de gastos en marzo: ", march_neg)
    print("Total de ingresos en marzo: ", march_pos)
    print("Presupuesto en abril: ", til_march + march_pos + march_neg)
