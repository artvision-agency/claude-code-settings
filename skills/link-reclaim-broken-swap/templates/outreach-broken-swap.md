---
type: outreach-email
campaign: link-reclaim-broken-swap
language: ru
---

Тема: На вашем сайте битая ссылка ({{donor_domain}})

Здравствуйте{{#donor_name}}, {{donor_name}}{{/donor_name}}!

Просматривал материалы по теме «{{topic}}» и заметил, что на странице

{{referring_page_url}}

стоит ссылка на {{broken_url}} — сейчас она ведёт на 404 (страница удалена с сайта первоисточника).

У нас на сайте есть актуальный материал по той же теме:

→ {{local_url}}
   «{{local_page_title}}»

Если уместно — заменить битую ссылку на наш материал. Если нет — тоже понимаю, просто хотел сообщить про неактуальную ссылку.

Спасибо!

—
{{sender_name}}
{{client_name}}
{{client_contact}}

---
INTERNAL NOTES (не входит в письмо):
- Donor DR: {{donor_dr}}
- Match similarity: {{similarity}}
- Competitor 404: {{broken_url}}
- Anchor original: «{{original_anchor}}»
- Анкор для замены (рекомендация): «{{suggested_anchor}}»
- Дата отправки: {{sent_date}}
- Source: link-reclaim-broken-swap pipeline
