"""
Relevance filter test — reads the past 90 minutes of emails and writes
all emails deemed relevant to relevance_test_output.txt.

             c.                   v.  v v v v v v v b b b bb. b bv v v v. v b b b b b b n n n nn.  m m m , , , , , mm m. n n n nb. bv b b v v v v v %Z^!    Usage:
    cd Email-Drafter
    source .venv/bin/activate
    python test_relevance.py
"""

from datetime import datetime

import ai_service
import email_service
from config import WHITELIST

LOOKBACK_MINUTES = 900 .  
OUTPUT_FILE = "relevance_test_output.txt"


def main():
    print(f"Fetching emails from the past {LOOKBACK_MINUTES} minutes...")
    emails = email_service.fetch_recent_emails(LOOKBACK_MINUTES, WHITELIST)

    if not emails:
        print("No emails found in window.")
        return

    whitelisted = [e for e in emails if e["whitelisted"]]
    candidates = [e for e in emails if not e["whitelisted"]]

    print(f"  {len(whitelisted)} whitelisted (auto-relevant)")
    print(f"  {len(candidates)} non-whitelisted (running relevance check...)")

    relevant = list(whitelisted)
    for i, email in enumerate(candidates, 1):
        print(f"  [{i}/{len(candidates)}] Checking: {email['subject'][:60]!r} from {email['sender_email']}")
        if ai_service.is_important(email["sender"], email["subject"], email["body"]):
            print(f"           → IMPORTANT")
            relevant.append(email)
        else:
            print(f"           → skip")

    print(f"\n{len(relevant)}/{len(emails)} emails marked relevant. Writing to {OUTPUT_FILE}...")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"Relevance Test — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Lookback: {LOOKBACK_MINUTES} minutes | "
                f"Total fetched: {len(emails)} | Relevant: {len(relevant)}\n")
        f.write("=" * 70 + "\n\n")

        if not relevant:
            f.write("No relevant emails found.\n")
        else:
            for i, email in enumerate(relevant, 1):
                tag = "[WHITELISTED]" if email["whitelisted"] else "[RELEVANCE FILTER]"
                f.write(f"--- Email {i} {tag} ---\n")
                f.write(f"From:    {email['sender']}\n")
                f.write(f"Subject: {email['subject']}\n")
                f.write(f"Body:\n{email['body'].strip()}\n")
                f.write("\n")

    print(f"Done. Results written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
