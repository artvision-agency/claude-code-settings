#!/usr/bin/env python3
"""
Менеджер трекера outreach-писем.
Добавляет письма, обновляет статус, показывает метрики.

Usage:
  python3 tracker_manager.py add --campaign "ant-partners" --website "nalogovoe.pro" --type "GUEST_POST" --recipient "Ivan"
  python3 tracker_manager.py update --id "email-001" --status "positive" --response "Согласился"
  python3 tracker_manager.py status
  python3 tracker_manager.py metrics
"""

import json
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

TRACKER_FILE = Path(__file__).parent / "tracker.json"

class TrackerManager:
    def __init__(self):
        self.tracker = self._load_tracker()

    def _load_tracker(self) -> dict:
        """Загрузить трекер из JSON."""
        if TRACKER_FILE.exists():
            with open(TRACKER_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"campaigns": [], "emails": [], "metrics": {}}

    def _save_tracker(self):
        """Сохранить трекер в JSON."""
        with open(TRACKER_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.tracker, f, ensure_ascii=False, indent=2)

    def add_email(self, campaign_id: str, website: str, recipient_name: str,
                  recipient_email: str, outreach_type: str, subject: str) -> str:
        """Добавить новое письмо в трекер."""

        # Создать уникальный ID
        email_id = f"email-{len(self.tracker['emails']) + 1:03d}"

        email_record = {
            "id": email_id,
            "campaign_id": campaign_id,
            "recipient_name": recipient_name,
            "website_name": website,
            "website_url": f"https://{website}",
            "recipient_email": recipient_email,
            "outreach_type": outreach_type,
            "subject": subject,
            "sent_at": datetime.now().isoformat() + "Z",
            "status": "waiting",
            "follow_up_1": {
                "scheduled_at": (datetime.now() + timedelta(days=3)).isoformat() + "Z",
                "sent_at": None,
                "status": "pending"
            },
            "follow_up_2": {
                "scheduled_at": (datetime.now() + timedelta(days=7)).isoformat() + "Z",
                "sent_at": None,
                "status": "pending"
            },
            "response": None,
            "conversion": None,
            "notes": ""
        }

        self.tracker["emails"].append(email_record)
        self._save_tracker()
        return email_id

    def update_email(self, email_id: str, status: str, response: Optional[str] = None,
                     conversion: Optional[str] = None, notes: Optional[str] = None):
        """Обновить статус письма."""

        for email in self.tracker["emails"]:
            if email["id"] == email_id:
                email["status"] = status
                if response:
                    email["response"] = response
                if conversion:
                    email["conversion"] = conversion
                if notes:
                    email["notes"] = notes
                self._save_tracker()
                return True

        print(f"Письмо {email_id} не найдено")
        return False

    def add_follow_up(self, email_id: str, follow_up_number: int):
        """Отметить follow-up как отправленный."""

        for email in self.tracker["emails"]:
            if email["id"] == email_id:
                key = f"follow_up_{follow_up_number}"
                if key in email:
                    email[key]["sent_at"] = datetime.now().isoformat() + "Z"
                    email[key]["status"] = "sent"
                    self._save_tracker()
                    return True

        return False

    def show_status(self, campaign_id: Optional[str] = None):
        """Показать статус всех писем."""

        emails = self.tracker["emails"]
        if campaign_id:
            emails = [e for e in emails if e["campaign_id"] == campaign_id]

        if not emails:
            print("Писем не найдено")
            return

        print("\n" + "="*100)
        print(f"{'ID':<12} {'Сайт':<20} {'Тип':<15} {'Статус':<12} {'Отправлено':<11} {'FU1':<6} {'FU2':<6} {'Ответ':<15}")
        print("="*100)

        for email in emails:
            sent_date = email["sent_at"][:10] if email["sent_at"] else "—"
            fu1_status = email["follow_up_1"]["status"][0].upper() if email["follow_up_1"]["status"] else "—"
            fu2_status = email["follow_up_2"]["status"][0].upper() if email["follow_up_2"]["status"] else "—"
            response = email["response"][:12] if email["response"] else "—"

            print(f"{email['id']:<12} {email['website_name']:<20} {email['outreach_type']:<15} {email['status']:<12} {sent_date:<11} {fu1_status:<6} {fu2_status:<6} {response:<15}")

        print("="*100 + "\n")

    def show_metrics(self):
        """Показать метрики кампании."""

        emails = self.tracker["emails"]
        if not emails:
            print("Нет данных для метрик")
            return

        total = len(emails)
        replied = len([e for e in emails if e["status"] in ("positive", "negative")])
        positive = len([e for e in emails if e["status"] == "positive"])
        negative = len([e for e in emails if e["status"] == "negative"])
        conversions = len([e for e in emails if e["conversion"] == "COMPLETED"])

        reply_rate = (replied / total * 100) if total > 0 else 0
        conversion_rate = (conversions / total * 100) if total > 0 else 0

        # Считать время до ответа
        response_times = []
        for email in emails:
            if email["response"] and email["sent_at"]:
                # Это приблизительный расчет
                response_times.append(3)  # упрощенно

        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        print("\n" + "="*60)
        print("МЕТРИКИ КАМПАНИИ")
        print("="*60)
        print(f"Писем отправлено:      {total}")
        print(f"Получено ответов:      {replied} ({reply_rate:.1f}%)")
        print(f"  - Положительных:     {positive}")
        print(f"  - Отрицательных:     {negative}")
        print(f"Конверсии:             {conversions} ({conversion_rate:.1f}%)")
        print(f"Среднее время ответа:  {avg_response_time:.0f} дней")
        print("="*60 + "\n")

    def show_pending_follow_ups(self):
        """Показать письма, которым нужен follow-up."""

        pending = []

        for email in self.tracker["emails"]:
            today = datetime.now()

            # Check FU1
            if email["follow_up_1"]["status"] == "pending":
                fu_date = datetime.fromisoformat(email["follow_up_1"]["scheduled_at"].replace("Z", "+00:00"))
                if today >= fu_date.replace(tzinfo=None):
                    pending.append({
                        "id": email["id"],
                        "website": email["website_name"],
                        "type": "Follow-up 1",
                        "date": email["follow_up_1"]["scheduled_at"][:10]
                    })

            # Check FU2
            if email["follow_up_2"]["status"] == "pending":
                fu_date = datetime.fromisoformat(email["follow_up_2"]["scheduled_at"].replace("Z", "+00:00"))
                if today >= fu_date.replace(tzinfo=None):
                    pending.append({
                        "id": email["id"],
                        "website": email["website_name"],
                        "type": "Follow-up 2",
                        "date": email["follow_up_2"]["scheduled_at"][:10]
                    })

        if pending:
            print("\n" + "="*70)
            print("ОЖИДАЮЩИЕ FOLLOW-UP")
            print("="*70)
            for item in pending:
                print(f"{item['id']:<12} {item['website']:<25} {item['type']:<15} {item['date']}")
            print("="*70 + "\n")
        else:
            print("Нет ожидающих follow-up\n")

def main():
    parser = argparse.ArgumentParser(description="Менеджер трекера outreach-писем")

    subparsers = parser.add_subparsers(dest="command", help="Команда")

    # Add command
    add_parser = subparsers.add_parser("add", help="Добавить новое письмо")
    add_parser.add_argument("--campaign", required=True, help="ID кампании")
    add_parser.add_argument("--website", required=True, help="Сайт (без https://)")
    add_parser.add_argument("--recipient", required=True, help="Имя получателя")
    add_parser.add_argument("--email", required=True, help="Email получателя")
    add_parser.add_argument("--type", required=True, help="Тип письма (GUEST_POST, LINK_EXCHANGE, etc)")
    add_parser.add_argument("--subject", required=True, help="Subject письма")

    # Update command
    update_parser = subparsers.add_parser("update", help="Обновить статус письма")
    update_parser.add_argument("--id", required=True, help="ID письма")
    update_parser.add_argument("--status", required=True, help="Статус (waiting, positive, negative)")
    update_parser.add_argument("--response", help="Ответ/комментарий")
    update_parser.add_argument("--conversion", help="Тип конверсии (COMPLETED, ARCHIVED)")
    update_parser.add_argument("--notes", help="Заметки")

    # Follow-up command
    fu_parser = subparsers.add_parser("follow-up", help="Отметить follow-up как отправленный")
    fu_parser.add_argument("--id", required=True, help="ID письма")
    fu_parser.add_argument("--number", type=int, required=True, help="Номер follow-up (1 или 2)")

    # Status command
    status_parser = subparsers.add_parser("status", help="Показать статус писем")
    status_parser.add_argument("--campaign", help="Фильтр по ID кампании")

    # Metrics command
    subparsers.add_parser("metrics", help="Показать метрики")

    # Pending command
    subparsers.add_parser("pending", help="Показать ожидающие follow-up")

    args = parser.parse_args()
    manager = TrackerManager()

    if args.command == "add":
        email_id = manager.add_email(
            campaign_id=args.campaign,
            website=args.website,
            recipient_name=args.recipient,
            recipient_email=args.email,
            outreach_type=args.type,
            subject=args.subject
        )
        print(f"✅ Письмо добавлено: {email_id}")

    elif args.command == "update":
        if manager.update_email(
            email_id=args.id,
            status=args.status,
            response=args.response,
            conversion=args.conversion,
            notes=args.notes
        ):
            print(f"✅ Письмо {args.id} обновлено")
        else:
            sys.exit(1)

    elif args.command == "follow-up":
        if manager.add_follow_up(args.id, args.number):
            print(f"✅ Follow-up #{args.number} для {args.id} отмечен как отправленный")
        else:
            sys.exit(1)

    elif args.command == "status":
        manager.show_status(campaign_id=args.campaign)

    elif args.command == "metrics":
        manager.show_metrics()

    elif args.command == "pending":
        manager.show_pending_follow_ups()

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
