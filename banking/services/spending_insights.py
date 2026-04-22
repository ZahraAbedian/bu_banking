from collections import defaultdict
from decimal import Decimal
from django.utils import timezone

from banking.models import Account, Transaction


CATEGORY_MAP = {
    "food": "Food & Drink",
    "restaurant": "Food & Drink",
    "cafe": "Food & Drink",
    "coffee": "Food & Drink",
    "groceries": "Food & Drink",
    "retail": "Shopping",
    "shopping": "Shopping",
    "clothes": "Shopping",
    "fashion": "Shopping",
    "transport": "Transport",
    "travel": "Transport",
    "taxi": "Transport",
    "fuel": "Transport",
    "petrol": "Transport",
    "gas": "Transport",
    "entertainment": "Entertainment",
    "cinema": "Entertainment",
    "movies": "Entertainment",
    "streaming": "Entertainment",
    "music": "Entertainment",
    "bills": "Bills",
    "utilities": "Bills",
    "electricity": "Bills",
    "water": "Bills",
    "internet": "Bills",
    "phone": "Bills",
}


def categorize_transaction(transaction: Transaction) -> str:
    """
    Assign a spending category to a transaction.
    First version uses simple rule-based categorisation.
    """
    transaction_type = transaction.transaction_type

    if transaction_type == "withdrawal":
        return "Cash / Withdrawals"

    if transaction_type == "transfer":
        return "Transfers"

    if transaction_type == "deposit":
        return "Income / Deposits"

    if transaction_type == "collect_roundup":
        return "Savings / Round Up"

    if transaction_type == "roundup_reclaim":
        return "Savings / Round Up"

    if transaction.business:
        # Try business.category first
        if transaction.business.category:
            business_category = transaction.business.category.lower()
            for key, label in CATEGORY_MAP.items():
                if key in business_category:
                    return label

        # Fall back to business name if category is not useful
        if transaction.business.name:
            business_name = transaction.business.name.lower()
            for key, label in CATEGORY_MAP.items():
                if key in business_name:
                    return label

    return "Other"


def get_user_transactions_for_month(user, month: int | None = None, year: int | None = None):
    """
    Return transactions for all accounts owned by the user in a given month/year.
    Defaults to the current month.
    """
    now = timezone.now()

    if month is None:
        month = now.month
    if year is None:
        year = now.year

    user_accounts = Account.objects.filter(user=user)

    return Transaction.objects.filter(
        from_account__in=user_accounts,
        timestamp__year=year,
        timestamp__month=month,
    ).select_related("business", "from_account", "to_account")


def monthly_spending_summary(user, month: int | None = None, year: int | None = None) -> dict:
    """
    Build a monthly spending summary grouped by category.
    This first version treats payment and withdrawal as 'spending'.
    """
    transactions = get_user_transactions_for_month(user=user, month=month, year=year)

    category_totals = defaultdict(lambda: Decimal("0.00"))
    total_spent = Decimal("0.00")

    # First version: only count payment and withdrawal as spending
    spending_transactions = transactions.filter(
        transaction_type__in=["payment", "withdrawal"]
    )

    for transaction in spending_transactions:
        category = categorize_transaction(transaction)
        amount = transaction.amount or Decimal("0.00")

        category_totals[category] += amount
        total_spent += amount

    sorted_categories = sorted(
        category_totals.items(),
        key=lambda item: item[1],
        reverse=True
    )

    categories = []
    for category, total in sorted_categories:
        percentage = Decimal("0.00")
        if total_spent > Decimal("0.00"):
            percentage = (total / total_spent) * Decimal("100")

        categories.append({
            "category": category,
            "total": str(total),
            "percentage": f"{percentage:.2f}"
        })

    if month is None or year is None:
        now = timezone.now()
        if month is None:
            month = now.month
        if year is None:
            year = now.year

    return {
        "month": f"{year}-{month:02d}",
        "total_spent": str(total_spent),
        "categories": categories,
        "transaction_count": spending_transactions.count(),
    }


def generate_insights(summary_data: dict) -> list[str]:
    """
    Generate simple human-readable insight messages from the monthly summary.
    First version is rule-based text generation.
    """
    insights = []
    categories = summary_data.get("categories", [])
    total_spent = Decimal(summary_data.get("total_spent", "0.00"))

    if total_spent == Decimal("0.00"):
        return ["No spending activity found for this month yet."]

    if categories:
        top_category = categories[0]
        insights.append(
            f"Your highest spending category this month is {top_category['category']}."
        )

    if len(categories) > 1:
        second_category = categories[1]
        insights.append(
            f"Your second highest spending category is {second_category['category']}."
        )

    if total_spent > Decimal("500.00"):
        insights.append(
            "Your spending this month is relatively high compared with a typical light-spending month."
        )
    elif total_spent < Decimal("100.00"):
        insights.append(
            "Your spending this month is currently quite low."
        )

    if not insights:
        insights.append("Your spending looks fairly balanced this month.")

    return insights


def get_monthly_spending_insights(user, month: int | None = None, year: int | None = None) -> dict:
    """
    Main function to return spending summary + generated insights.
    """
    summary = monthly_spending_summary(user=user, month=month, year=year)
    summary["insights"] = generate_insights(summary)
    return summary

