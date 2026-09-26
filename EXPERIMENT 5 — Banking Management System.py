from abc import ABC, abstractmethod


class BankAccount(ABC):

    def __init__(
        self,
        account_number: int,
        name: str,
        balance: float
    ):
        self.account_number = account_number
        self.name = name
        self.balance = balance

    def deposit(self, amount: float) -> None:
        if amount > 0:
            self.balance += amount
            print("Amount deposited:", amount)
        else:
            print("Invalid deposit amount")

    @abstractmethod
    def withdraw(self, amount: float) -> None:
        pass

    def display(self) -> None:
        print("Account Number:", self.account_number)
        print("Account Holder:", self.name)
        print("Balance:", self.balance)


class SavingsAccount(BankAccount):

    def withdraw(self, amount: float) -> None:

        if amount <= self.balance:
            self.balance -= amount
            print("Amount withdrawn:", amount)
        else:
            print("Insufficient balance")


class CurrentAccount(BankAccount):

    def withdraw(self, amount: float) -> None:

        overdraft_limit = 5000

        if amount <= self.balance + overdraft_limit:
            self.balance -= amount
            print("Amount withdrawn:", amount)
        else:
            print("Withdrawal limit exceeded")


# -------------------------------
# SAVINGS ACCOUNT
# -------------------------------

print("----- SAVINGS ACCOUNT -----")

savings = SavingsAccount(
    1001,
    "Murari",
    10000
)

savings.display()

savings.deposit(2000)
savings.withdraw(3000)

print("\nAfter Transactions:")
savings.display()


# -------------------------------
# CURRENT ACCOUNT
# -------------------------------

print("\n----- CURRENT ACCOUNT -----")

current = CurrentAccount(
    1002,
    "Hema",
    15000
)

current.display()

current.deposit(5000)
current.withdraw(18000)

print("\nAfter Transactions:")
current.display()