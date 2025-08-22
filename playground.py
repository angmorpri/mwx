# 2025/08/22
"""
playground.py - Non-pytest testing
"""

from datetime import datetime

from mwx.model import Account, Category, Entry

if __name__ == "__main__":
    acc = Account(17, "Básicos", 10, "#998866")
    icat = Category(10, "A50. Ingresos generales", +1, "#668800")
    ocat = Category(20, "B50. Gastos generales", -1, "#886600")
    tcat = Category(30, "T50. Reajustes", 0, "#101010")
    income = Entry(10, 100.00, datetime.today(), +1, "Cliente", acc, icat, "Paga")
    expense = Entry(20, 100.00, datetime.today(), -1, acc, "Proveedor", ocat, "Compra")
    transfer = Entry(30, 100.00, datetime.today(), 0, acc, acc, tcat)

    print(acc)
    print(icat)
    print(ocat)
    print(tcat)
    print(income)
    print(expense)
    print(transfer)
