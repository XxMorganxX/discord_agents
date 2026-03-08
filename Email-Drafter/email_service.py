import email
import imaplib
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr, parsedate_to_datetime

from config import get_env

log = logging.getLogger(__name__)

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
DRAFTS_FOLDER = "[Gmail]/Drafts"


def _connect() -> imaplib.IMAP4_SSL:
    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    conn.login(get_env("GMAIL_ADDRESS"), get_env("GMAIL_APP_PASSWORD"))
    return conn


def fetch_recent_emails(lookback_minutes: int, whitelist: list[str]) -> list[dict]:
    conn = _connect()
    cutoff = datetime.now(EASTERN) - timedelta(minutes=lookback_minutes)
    since = cutoff.strftime("%d-%b-%Y")
    whitelist_lower = {w.lower().strip() for w in whitelist}
    emails = []

    try:
        conn.select("INBOX")
        conn.noop()
        status, data = conn.search(None, "SINCE", since)
        if status != "OK":
            log.warning("IMAP SINCE search failed: status=%s data=%s", status, data)
            return []
        msg_ids = data[0].split() if data and data[0] else []

        for num in msg_ids:
            _, header_data = conn.fetch(num, "(BODY.PEEK[HEADER.FIELDS (DATE FROM SUBJECT MESSAGE-ID)])")
            if not header_data or header_data[0] is None:
                continue
            raw_header = header_data[0][1]
            header_msg = email.message_from_bytes(raw_header)

            sent_at = _extract_sent_at(header_msg)
            if sent_at is None or sent_at < cutoff:
                continue

            sender = header_msg.get("From", "")
            sender_email = _extract_email(sender).lower().strip()

            _, msg_data = conn.fetch(num, "(RFC822)")
            if not msg_data or msg_data[0] is None:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            emails.append(
                {
                    "message_id": msg.get("Message-ID", ""),
                    "thread_id": None,
                    "sender": msg.get("From", sender),
                    "sender_email": _extract_email(msg.get("From", sender)),
                    "subject": msg.get("Subject", "(no subject)"),
                    "body": _extract_body(msg),
                    "whitelisted": sender_email in whitelist_lower,
                }
            )
    finally:
        conn.logout()

    log.info(
        "Fetched %d email(s) from the past %d minutes (%d whitelisted)",
        len(emails),
        lookback_minutes,
        sum(1 for e in emails if e["whitelisted"]),
    )
    return emails


def inspect_recent_emails(
    lookback_minutes: int, whitelist: list[str], limit: int = 25
) -> dict:
    """Return per-message whitelist diagnostics for recent inbox messages.
    Returns dict with keys: checks, search_since, cutoff_est, total_in_inbox, total_matching_search.
    """
    conn = _connect()
    cutoff = datetime.now(EASTERN) - timedelta(minutes=lookback_minutes)
    since = cutoff.strftime("%d-%b-%Y")
    whitelist_lower = {w.lower().strip() for w in whitelist}
    checks = []

    try:
        conn.select("INBOX")
        conn.noop()

        status, data = conn.search(None, "SINCE", since)
        if status != "OK":
            log.warning("IMAP diagnostics SINCE search failed: status=%s data=%s", status, data)
            return {
                "checks": [],
                "search_since": since,
                "cutoff_est": cutoff.isoformat(),
                "total_in_inbox": None,
                "total_matching_search": 0,
                "search_status": status,
                "search_error": str(data) if data else "no data",
            }
        msg_ids = data[0].split() if data and data[0] else []

        # Fallback: if SINCE returns nothing, try ALL to see if inbox has any mail
        total_in_inbox = None
        if not msg_ids:
            all_status, all_data = conn.search(None, "ALL")
            if all_status == "OK" and all_data and all_data[0]:
                total_in_inbox = len(all_data[0].split())

        for num in msg_ids[-limit:]:
            _, header_data = conn.fetch(num, "(BODY.PEEK[HEADER.FIELDS (DATE FROM SUBJECT MESSAGE-ID)])")
            if not header_data or header_data[0] is None:
                continue
            raw_header = header_data[0][1]
            msg = email.message_from_bytes(raw_header)

            sender_raw = msg.get("From", "")
            parsed_email = _extract_email(sender_raw).lower().strip()
            sent_at = _extract_sent_at(msg)
            checks.append(
                {
                    "imap_id": num.decode() if isinstance(num, bytes) else str(num),
                    "subject": msg.get("Subject", "(no subject)"),
                    "from_raw": sender_raw,
                    "parsed_email": parsed_email,
                    "matched": parsed_email in whitelist_lower,
                    "in_time_window": bool(sent_at and sent_at >= cutoff),
                    "sent_at": sent_at.isoformat() if sent_at else "unknown",
                    "message_id": msg.get("Message-ID", ""),
                    "search_mode": f"SINCE {since}",
                }
            )
    finally:
        conn.logout()

    return {
        "checks": checks,
        "search_since": since,
        "cutoff_est": cutoff.isoformat(),
        "total_in_inbox": total_in_inbox if total_in_inbox is not None else len(msg_ids),
        "total_matching_search": len(msg_ids),
        "search_status": "OK",
        "search_error": None,
    }


def create_draft_reply(thread_id: str, message_id: str, to: str, subject: str, body: str):
    mime = MIMEMultipart()
    mime["To"] = to
    mime["From"] = get_env("GMAIL_ADDRESS")
    mime["Subject"] = f"Re: {subject}" if not subject.lower().startswith("re:") else subject
    mime["In-Reply-To"] = message_id
    mime["References"] = message_id
    mime.attach(MIMEText(body, "plain"))

    conn = _connect()
    conn.select(DRAFTS_FOLDER)
    conn.append(
        DRAFTS_FOLDER,
        "",
        imaplib.Time2Internaldate(datetime.now().timetuple()),
        mime.as_bytes(),
    )
    conn.logout()
    log.info("Draft saved to %s for message %s", DRAFTS_FOLDER, message_id)


def _extract_email(from_header: str) -> str:
    _, addr = parseaddr(from_header)
    return (addr or from_header).strip()


def _extract_sent_at(msg: email.message.Message) -> datetime | None:
    date_header = msg.get("Date")
    if not date_header:
        return None
    try:
        dt = parsedate_to_datetime(date_header)
    except Exception:
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone(EASTERN)
    return dt.astimezone(EASTERN)


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and part.get("Content-Disposition") is None:
                return part.get_payload(decode=True).decode("utf-8", errors="replace")
    else:
        return msg.get_payload(decode=True).decode("utf-8", errors="replace")
    return ""
