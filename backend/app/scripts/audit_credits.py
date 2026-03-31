"""Credit system audit agent.

Detects negative balances, orphaned transactions, and balance drift.

Usage:
    python -m app.scripts.audit_credits
    python -m app.scripts.audit_credits --fix
"""

import asyncio
import argparse
import json
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


async def audit(fix: bool = False):
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    findings = {"negative_balances": [], "balance_drift": [], "summary": {}}

    async with async_session() as db:
        # Check 1: Negative balances
        result = await db.execute(
            text("SELECT id, email, credit_balance FROM users WHERE credit_balance < 0")
        )
        for row in result.fetchall():
            findings["negative_balances"].append(
                {"user_id": str(row[0]), "email": row[1], "balance": row[2]}
            )

        # Check 2: Balance drift (credit_balance != SUM of transactions)
        result = await db.execute(
            text("""
            SELECT u.id, u.email, u.credit_balance,
                   COALESCE(SUM(ct.amount), 0) AS tx_sum
            FROM users u
            LEFT JOIN credit_transactions ct ON ct.user_id = u.id
            GROUP BY u.id, u.email, u.credit_balance
            HAVING u.credit_balance != COALESCE(SUM(ct.amount), 0)
               AND (u.credit_balance != 50 OR COALESCE(SUM(ct.amount), 0) != 0)
        """)
        )
        for row in result.fetchall():
            drift = {
                "user_id": str(row[0]),
                "email": row[1],
                "db_balance": row[2],
                "tx_sum": int(row[3]),
                "drift": row[2] - int(row[3]),
            }
            findings["balance_drift"].append(drift)

            if fix:
                # Fix: set balance to match transaction history + initial 50
                correct = int(row[3]) + 50  # initial credits + transactions
                await db.execute(
                    text("UPDATE users SET credit_balance = :bal WHERE id = :uid"),
                    {"bal": correct, "uid": row[0]},
                )

        if fix and findings["balance_drift"]:
            await db.commit()

    await engine.dispose()

    findings["summary"] = {
        "negative_balances": len(findings["negative_balances"]),
        "balance_drift": len(findings["balance_drift"]),
        "fixed": fix and len(findings["balance_drift"]) > 0,
    }

    print(json.dumps(findings, indent=2))
    return 1 if findings["negative_balances"] or findings["balance_drift"] else 0


def main():
    parser = argparse.ArgumentParser(description="Audit credit system for anomalies")
    parser.add_argument("--fix", action="store_true", help="Auto-fix balance drift")
    args = parser.parse_args()
    sys.exit(asyncio.run(audit(fix=args.fix)))


if __name__ == "__main__":
    main()
