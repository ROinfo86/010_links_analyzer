@echo off
chcp 65001 >nul
echo.
echo ====================================
echo   Website Link Analyzer
echo   Анализатор битых ссылок сайта
echo ====================================
echo.

if "%1"=="" (
    echo Использование: analyze_links.bat URL [параметры]
    echo.
    echo Примеры:
    echo   analyze_links.bat https://example.com
    echo   analyze_links.bat https://example.com --max-pages 50
    echo   analyze_links.bat https://example.com --delay 0.5 --max-workers 10
    echo.
    echo Доступные параметры:
    echo   --max-pages N      Максимум страниц для обхода (по умолчанию: 100)
    echo   --delay N          Задержка между запросами в сек (по умолчанию: 1.0)
    echo   --timeout N        Таймаут запросов в сек (по умолчанию: 10)
    echo   --max-workers N    Количество потоков (по умолчанию: 5)
    echo   --output DIR       Папка для отчетов (по умолчанию: текущая)
    echo   --no-robots        Игнорировать robots.txt
    echo   --user-agent UA    Кастомный User-Agent
    echo.
    pause
    exit /b 1
)

echo Запуск анализа для: %1
echo.

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден в системе!
    echo Установите Python 3.7+ и добавьте его в PATH
    pause
    exit /b 1
)

REM Проверяем наличие скрипта
if not exist "link_analyzer.py" (
    echo ОШИБКА: Файл link_analyzer.py не найден!
    echo Убедитесь что вы запускаете скрипт из правильной папки
    pause
    exit /b 1
)

REM Запускаем анализ
echo Начинаем анализ...
echo Для прерывания нажмите Ctrl+C
echo.

python link_analyzer.py %*

if errorlevel 1 (
    echo.
    echo ОШИБКА: Анализ завершился с ошибкой!
    echo Проверьте логи в файле link_analyzer.log
) else (
    echo.
    echo ✅ Анализ завершен успешно!
    echo Проверьте созданные отчеты в указанной папке
)

echo.
pause