# Быстрый старт - Website Link Analyzer

## 🚀 Установка и запуск за 2 минуты

### 1. Проверка требований
```bash
# Проверьте что Python 3.7+ установлен
python --version
```

### 2. Установка зависимостей
```bash
# Из файла requirements.txt
pip install -r requirements.txt

# Или вручную
pip install requests beautifulsoup4 lxml urllib3
```

### 3. Быстрый тест
```bash
# Запуск тестов
python test_analyzer.py
```

### 4. Первый анализ
```bash
# Базовый анализ (небольшой сайт)
python link_analyzer.py https://httpbin.org --max-pages 10

# Windows пользователи могут использовать
analyze_links.bat https://httpbin.org --max-pages 10
```

## 📊 Что вы получите

После анализа будут созданы 3 файла:
- **JSON отчет** - полные данные для программной обработки
- **CSV отчет** - таблица битых ссылок для Excel/Google Sheets  
- **TXT отчет** - человеко-читаемый отчет

## ⚙️ Рекомендуемые настройки

### Для небольших сайтов (< 50 страниц)
```bash
python link_analyzer.py https://yoursite.com --max-pages 50 --delay 0.5
```

### Для средних сайтов (50-200 страниц)
```bash
python link_analyzer.py https://yoursite.com --max-pages 200 --delay 1.0 --max-workers 8
```

### Для больших сайтов (> 200 страниц)
```bash
python link_analyzer.py https://yoursite.com --max-pages 500 --delay 1.5 --max-workers 10
```

## 🛠️ Решение проблем

### Ошибка "SSL certificate verify failed"
```bash
# Скрипт автоматически игнорирует SSL ошибки
# Дополнительных действий не требуется
```

### Медленная работа
```bash
# Увеличьте количество потоков и уменьшите задержку
python link_analyzer.py https://yoursite.com --max-workers 10 --delay 0.5
```

### Блокировка по IP
```bash
# Увеличьте задержку или используйте кастомный User-Agent
python link_analyzer.py https://yoursite.com --delay 2.0 --user-agent "MyBot/1.0"
```

## 📝 Примеры команд

```bash
# Анализ с сохранением в отдельную папку
python link_analyzer.py https://example.com --output ./reports

# Игнорирование robots.txt  
python link_analyzer.py https://example.com --no-robots

# Быстрый анализ (только внутренние ссылки)
python link_analyzer.py https://example.com --max-pages 20 --delay 0.3

# Детальный анализ с отчетами
python link_analyzer.py https://example.com --max-pages 100 --max-workers 8
```

## 🎯 Что анализируется

✅ Все типы HTML ссылок (href, src, action)  
✅ Текстовые URL в содержимом страниц  
✅ Внутренние и внешние ссылки  
✅ HTTP статус коды (200, 404, 500, etc.)  
✅ SSL/HTTPS соединения  
✅ Редиректы и цепочки перенаправлений  
✅ Время отклика каждой ссылки  

## 📞 Поддержка

При проблемах:
1. Проверьте `link_analyzer.log` для деталей
2. Запустите `python test_analyzer.py` для диагностики
3. Убедитесь что все зависимости установлены

---
**Готово!** Теперь вы можете анализировать любые сайты на битые ссылки! 🎉