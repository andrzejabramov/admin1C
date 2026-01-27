# 📚 Справочник команд rac (1С:Предприятие 8.3.27)

> ⚠️ **Важно!** Все команды `rac` должны выполняться от имени пользователя **`usr1cv8`**:
>
> ```bash
> sudo -u usr1cv8 rac <режим> <команда> [опции]
> ```

## 🔌 Требования к окружению

| Условие             | Проверка                           | Решение                                                                                  |
| ------------------- | ---------------------------------- | ---------------------------------------------------------------------------------------- |
| **RAS доступен**    | `sudo -u usr1cv8 rac cluster list` | Если «Connection refused» — запустить `ras cluster --port=1545 --cluster=127.0.0.1:1541` |
| **Кластер запущен** | `sudo ss -tulpn \| grep ':1541'`   | `sudo systemctl restart 1c-server`                                                       |
| **Пользователь**    | `whoami` → `usr1cv8`               | Использовать `sudo -u usr1cv8`                                                           |

> 💡 **Примечание:** Веб- и тонкий клиенты могут работать, даже если `rac` недоступен (сервис администрирования отключён).

## 🧩 Ключевые команды

### Кластер

```bash
# Список кластеров
sudo -u usr1cv8 rac cluster list

# Информация о кластере
sudo -u usr1cv8 rac cluster info --cluster=<uuid>
```

# Список ИБ

sudo -u usr1cv8 rac infobase summary list --cluster=<uuid>

# Создание ИБ (PostgreSQL)

sudo -u usr1cv8 rac infobase create \
 --cluster=<uuid> \
 --name=<имя> \
 --dbms=PostgreSQL \
 --db-server=10.129.0.27 \
 --db-name=<имя> \
 --db-user=postgres \
 --db-pwd-file=/home/usr1cv8/.pgpass \
 --locale=ru_RU \
 --create-database

# Удаление ИБ (НЕОБРАТИМО!)

sudo -u usr1cv8 rac infobase drop \
 --cluster=<uuid> \
 --infobase=<uuid> \
 [--drop-database]

# Список сессий

sudo -u usr1cv8 rac session list --cluster=<uuid>

# Завершение сессии

sudo -u usr1cv8 rac session terminate \
 --cluster=<uuid> \
 --session=<uuid>

# Список соединений

sudo -u usr1cv8 rac connection list --cluster=<uuid>

# Завершение соединения

sudo -u usr1cv8 rac connection terminate \
 --cluster=<uuid> \
 --connection=<uuid>
