#!/usr/bin/env python3
"""
Валидатор outreach-писем перед отправкой.
Проверяет на спам-слова, правильность формата, персонализацию.

Usage:
  python3 validate_email.py --subject "Subject text" --body "Email body"
  python3 validate_email.py --file email.txt
"""

import sys
import json
import argparse
from typing import List, Tuple

# Спам-слова и фразы (русский)
SPAM_WORDS = [
    "срочно", "СРОЧНО", "прибыль", "ПРИБЫЛЬ",
    "вам нужно", "ВАМ НУЖНО",
    "гарантировано", "ГАРАНТИРОВАНО",
    "только для вас", "ТОЛЬКО ДЛЯ ВАС",
    "поскольку вы", "как мы видим",
    "мы предлагаем", "пожалуйста",
    "всем!", "доверьте", "СЕЙЧАС!",
    "!!!!", "?????", "....", # множественное пунктирование
]

# Красные флаги в структуре письма
RED_FLAGS = {
    "multiple_urls": "Более одной ссылки (максимум одна)",
    "no_personalization": "Нет персонализации (generic 'Hi there')",
    "hard_sell": "Aggressive CTA (немедленное требование действия)",
    "multiple_exclamation": "Множественные !!!!!",
    "generic_greeting": "Generic привет (не по имени)",
    "no_cta": "Нет четкого CTA (call-to-action)",
    "too_long": "Письмо > 300 слов (должно быть ~150-250)",
}

class EmailValidator:
    def __init__(self, subject: str, body: str):
        self.subject = subject
        self.body = body
        self.errors = []
        self.warnings = []
        self.score = 100

    def validate(self) -> Tuple[int, List[str], List[str]]:
        """Запустить все проверки. Возвращает score, errors, warnings."""

        self._check_spam_words()
        self._check_punctuation()
        self._check_personalization()
        self._check_urls()
        self._check_length()
        self._check_cta()
        self._check_greeting()

        return self.score, self.errors, self.warnings

    def _check_spam_words(self):
        """Проверить спам-слова."""
        found = []
        for word in SPAM_WORDS:
            if word.lower() in self.body.lower():
                found.append(word)
                self.score -= 20

        if found:
            self.errors.append(f"Спам-слова найдены: {', '.join(found)}")

    def _check_punctuation(self):
        """Проверить чрезмерное пунктирование."""
        if "!!!!" in self.body or "?????" in self.body:
            self.errors.append("Чрезмерное пунктирование (!!!!, ?????)")
            self.score -= 15

        if self.subject.endswith("!!!"):
            self.warnings.append("Subject заканчивается на !!! (может выглядеть спамом)")
            self.score -= 10

    def _check_personalization(self):
        """Проверить, что письмо персонализировано."""
        generic_greetings = [
            "hi friend", "hey there", "hello there",
            "дорогой друг", "привет там", "хай",
        ]

        body_lower = self.body.lower()

        # Проверить на specific name (хотя бы один,)
        if "привет," not in body_lower and "привет" not in body_lower[:50]:
            self.warnings.append("Приветствие не по имени (используй 'Привет, [Имя]!')")
            self.score -= 10

    def _check_urls(self):
        """Проверить количество ссылок."""
        url_count = self.body.count("http://") + self.body.count("https://")

        if url_count > 1:
            self.warnings.append(f"Более одной ссылки ({url_count}). Идеально: 0-1")
            self.score -= 5

    def _check_length(self):
        """Проверить длину письма."""
        word_count = len(self.body.split())

        if word_count > 300:
            self.errors.append(f"Письмо слишком длинное ({word_count} слов). Норма: 150-250")
            self.score -= 15
        elif word_count < 50:
            self.warnings.append(f"Письмо слишком короткое ({word_count} слов). Желательно: 150-250")
            self.score -= 10

    def _check_cta(self):
        """Проверить наличие четкого CTA."""
        cta_patterns = [
            "можно ли", "можешь", "интересует",
            "когда у вас будет", "я пришлю", "посмотри",
            "давай", "согласен", "как думаешь",
        ]

        has_cta = any(pattern in self.body.lower() for pattern in cta_patterns)

        if not has_cta:
            self.warnings.append("CTA не очень четкий. Используй: 'Можно ли...', 'Интересует?', 'Когда у вас будет...'")
            self.score -= 10

    def _check_greeting(self):
        """Проверить приветствие."""
        if self.body.lower().startswith(("hello", "hi friend", "hi there", "hey there")):
            self.errors.append("Generic greeting (используй русский, персональное приветствие)")
            self.score -= 20

    def print_report(self):
        """Вывести отчет валидации."""
        score, errors, warnings = self.validate()

        print("\n" + "="*60)
        print(f"Валидация письма | Score: {score}/100")
        print("="*60)

        print(f"\nSubject: {self.subject}")
        print(f"Body length: {len(self.body.split())} слов")

        if errors:
            print("\n❌ ОШИБКИ (письмо лучше не отправлять):")
            for error in errors:
                print(f"  • {error}")

        if warnings:
            print("\n⚠️  ПРЕДУПРЕЖДЕНИЯ (желательно исправить):")
            for warning in warnings:
                print(f"  • {warning}")

        if not errors and not warnings:
            print("\n✅ Письмо прошло все проверки!")

        print("\n" + "="*60)

        # Рекомендации по score
        if score >= 90:
            print("✅ ГОТОВО К ОТПРАВКЕ")
        elif score >= 70:
            print("⚠️  ПОДУМАЙ ДВАЖДЫ, но можно отправлять")
        else:
            print("❌ ПЕРЕДЕЛАЙ ПЕРЕД ОТПРАВКОЙ")

        print("="*60 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Валидатор outreach-писем")
    parser.add_argument("--subject", type=str, help="Subject письма")
    parser.add_argument("--body", type=str, help="Body письма")
    parser.add_argument("--file", type=str, help="Прочитать письмо из файла")

    args = parser.parse_args()

    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Предполагаем, что первая строка — subject, остальное — body
            lines = content.split('\n', 1)
            subject = lines[0] if lines else ""
            body = lines[1] if len(lines) > 1 else ""
    elif args.subject and args.body:
        subject = args.subject
        body = args.body
    else:
        print("Использование: python3 validate_email.py --subject '...' --body '...'")
        print("               или python3 validate_email.py --file email.txt")
        sys.exit(1)

    validator = EmailValidator(subject, body)
    validator.print_report()

    # Return exit code based on score
    score, _, _ = validator.validate()
    if score < 70:
        sys.exit(1)  # Не отправлять
    sys.exit(0)  # Отправлять

if __name__ == "__main__":
    main()
