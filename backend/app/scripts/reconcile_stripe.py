"""Stripe subscription reconciliation agent.

Compares Stripe subscription state with database and auto-fixes mismatches.

Usage:
    python -m app.scripts.reconcile_stripe
    python -m app.scripts.reconcile_stripe --dry-run
"""

import asyncio
import argparse
import os
import sys
from datetime import datetime, timezone

import stripe
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


async def reconcile(dry_run: bool = False):
    database_url = os.environ.get("DATABASE_URL")
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")

    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    if not stripe_key:
        print("ERROR: STRIPE_SECRET_KEY not set")
        sys.exit(1)

    stripe.api_key = stripe_key
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    checked = 0
    mismatches = 0
    fixed = 0

    async with async_session() as db:
        result = await db.execute(
            text(
                "SELECT id, email, stripe_customer_id, subscription_active, "
                "subscription_expires_at FROM users "
                "WHERE stripe_customer_id IS NOT NULL"
            )
        )
        users = result.fetchall()

        for user in users:
            user_id, email, cust_id, db_active, db_expires = user
            checked += 1

            try:
                subs = stripe.Subscription.list(customer=cust_id, status="all", limit=1)
            except Exception as e:
                print(
                    f"  ERROR: Failed to fetch Stripe subs for {email} ({cust_id}): {e}"
                )
                continue

            if not subs.data:
                if db_active:
                    print(
                        f"  MISMATCH: {email} - DB says active but no Stripe subscription found"
                    )
                    mismatches += 1
                    if not dry_run:
                        await db.execute(
                            text(
                                "UPDATE users SET subscription_active = false WHERE id = :uid"
                            ),
                            {"uid": user_id},
                        )
                        fixed += 1
                continue

            sub = subs.data[0]
            stripe_active = sub.status in ("active", "trialing")
            stripe_expires = (
                datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc)
                if sub.current_period_end
                else None
            )

            if stripe_active != db_active:
                print(
                    f"  MISMATCH: {email} - Stripe={sub.status} DB_active={db_active}"
                )
                mismatches += 1
                if not dry_run:
                    await db.execute(
                        text(
                            "UPDATE users SET subscription_active = :active WHERE id = :uid"
                        ),
                        {"active": stripe_active, "uid": user_id},
                    )
                    fixed += 1

            if stripe_active and stripe_expires and db_expires:
                if abs((stripe_expires - db_expires).total_seconds()) > 86400:
                    print(
                        f"  MISMATCH: {email} - Stripe expires={stripe_expires} DB expires={db_expires}"
                    )
                    mismatches += 1
                    if not dry_run:
                        await db.execute(
                            text(
                                "UPDATE users SET subscription_expires_at = :exp WHERE id = :uid"
                            ),
                            {"exp": stripe_expires, "uid": user_id},
                        )
                        fixed += 1

        if not dry_run and fixed > 0:
            await db.commit()

    await engine.dispose()

    print(
        f"\nSummary: {checked} users checked, {mismatches} mismatches found, {fixed} auto-fixed"
    )
    if dry_run and mismatches > 0:
        print("(dry-run mode -- no changes applied)")
    return 1 if mismatches > 0 and dry_run else 0


def main():
    parser = argparse.ArgumentParser(
        description="Reconcile Stripe subscriptions with database"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report mismatches without fixing"
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(reconcile(dry_run=args.dry_run)))


if __name__ == "__main__":
    main()
