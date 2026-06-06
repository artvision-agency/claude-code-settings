# Личный VPN на VPS Artvision (Xray VLESS+Reality+Vision)

> Установлен 2026-06-02. VPS 80.90.181.152, порт 8843. Прод (nginx/боты) не задет.
> Это личный VPN Антона на нашем сервере. Файл вне git (секрет UUID).

## Подключение (импорт в v2RayTun / Hiddify / любой Xray-клиент)

```
vless://743d231c-9d25-43d9-abc9-1af76e17939e@80.90.181.152:8843?type=tcp&security=reality&pbk=YG-56kXJQdLpKGAO3zd3fUEyGCkPrinYFFdo_FsDVnU&fp=chrome&sni=www.microsoft.com&sid=d07b2fc1696272fd&flow=xtls-rprx-vision#ArtvisionVPS
```

## Параметры
- Протокол: VLESS + Reality + XTLS-Vision (TCP)
- Server: 80.90.181.152:8843
- UUID: 743d231c-9d25-43d9-abc9-1af76e17939e
- PublicKey: YG-56kXJQdLpKGAO3zd3fUEyGCkPrinYFFdo_FsDVnU
- ShortID: d07b2fc1696272fd
- SNI (маскировка): www.microsoft.com
- privateKey: на VPS в /root/.reality-params + /usr/local/etc/xray/config.json

## Управление на VPS
- Конфиг: /usr/local/etc/xray/config.json
- `systemctl restart|status xray` · enable уже включён (переживёт reboot)
- Добавить юзера: новый UUID в clients[] + restart
- Fallback на 443 (если режут 8843): nginx stream-проксирование ИЛИ перевесить inbound на 443 с dest-fallback

## Почему этот VPN
Подписочный v2RayTun рвался: сидел на VLESS+gRPC (ТСПУ-2026 давит gRPC) + 5 залипших utun на Mac. Свой Reality+Vision на TCP — устойчивый профиль, под нашим контролем.
