#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пример использования Website Link Analyzer
Демонстрирует различные способы запуска анализатора
"""

from link_analyzer import WebsiteCrawler
import time

def example_basic_usage():
    """Базовый пример использования"""
    print("=== БАЗОВЫЙ ПРИМЕР ===")
    
    # Создаем экземпляр анализатора
    crawler = WebsiteCrawler(
        base_url="https://httpbin.org",  # Тестовый сайт
        max_pages=5,  # Ограничиваем для примера
        delay=0.5,    # Быстрее для демо
        max_workers=3
    )
    
    print("Начинаем анализ...")
    start_time = time.time()
    
    # Обходим сайт
    crawler.crawl_website()
    
    # Проверяем ссылки
    crawler.check_all_links()
    
    # Генерируем отчеты
    crawler.generate_reports("./example_reports")
    
    end_time = time.time()
    
    print(f"Анализ завершен за {end_time - start_time:.2f} секунд")
    print(f"Найдено страниц: {len(crawler.visited_pages)}")
    print(f"Найдено ссылок: {len(crawler.link_status)}")
    print(f"Битых ссылок: {len(crawler.broken_links)}")

def example_advanced_usage():
    """Расширенный пример с настройками"""
    print("\n=== РАСШИРЕННЫЙ ПРИМЕР ===")
    
    # Создаем анализатор с расширенными настройками
    crawler = WebsiteCrawler(
        base_url="https://httpbin.org",
        max_pages=10,
        delay=1.0,
        respect_robots=True,
        timeout=15,
        max_workers=5,
        user_agent="LinkAnalyzer/1.0 (+https://example.com/bot)"
    )
    
    # Можем также настроить дополнительные параметры
    crawler.session.headers.update({
        'Accept-Language': 'ru-RU,en-US;q=0.9',
        'Cache-Control': 'no-cache'
    })
    
    print("Запускаем расширенный анализ...")
    
    try:
        crawler.crawl_website()
        crawler.check_all_links()
        crawler.generate_reports("./advanced_reports")
        
        # Выводим статистику
        print("\n=== СТАТИСТИКА ===")
        print(f"Обработано страниц: {len(crawler.visited_pages)}")
        
        # Подсчитываем типы ссылок
        internal_count = sum(1 for links in crawler.found_links.values() 
                           for link in links if link['link_type'] == 'internal')
        external_count = sum(1 for links in crawler.found_links.values() 
                           for link in links if link['link_type'] == 'external')
        
        print(f"Внутренних ссылок: {internal_count}")
        print(f"Внешних ссылок: {external_count}")
        
        # Подсчитываем статусы
        status_counts = {}
        for status_info in crawler.link_status.values():
            status = status_info.get('status_code', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\n=== СТАТУСЫ ССЫЛОК ===")
        for status, count in sorted(status_counts.items()):
            print(f"Статус {status}: {count} ссылок")
            
    except Exception as e:
        print(f"Ошибка при анализе: {e}")

def example_specific_analysis():
    """Пример анализа конкретных аспектов"""
    print("\n=== СПЕЦИФИЧЕСКИЙ АНАЛИЗ ===")
    
    crawler = WebsiteCrawler(
        base_url="https://httpbin.org",
        max_pages=3,
        delay=0.5
    )
    
    # Обходим сайт
    crawler.crawl_website()
    
    # Анализируем найденные ссылки
    print("\n=== ТИПЫ НАЙДЕННЫХ ЭЛЕМЕНТОВ ===")
    tag_counts = {}
    
    for page_links in crawler.found_links.values():
        for link in page_links:
            tag = link['tag']
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    for tag, count in sorted(tag_counts.items()):
        print(f"Тег <{tag}>: {count} ссылок")
    
    # Проверяем только внешние ссылки
    external_links = []
    for page_links in crawler.found_links.values():
        for link in page_links:
            if link['link_type'] == 'external':
                external_links.append(link)
    
    print(f"\n=== ВНЕШНИЕ ССЫЛКИ ({len(external_links)}) ===")
    unique_external = {}
    for link in external_links:
        url = link['url']
        if url not in unique_external:
            unique_external[url] = []
        unique_external[url].append(link['source_page'])
    
    for url, sources in list(unique_external.items())[:5]:  # Показываем первые 5
        print(f"URL: {url}")
        print(f"  Найден на страницах: {len(sources)}")
        
    # Проверяем статусы только внешних ссылок
    if unique_external:
        print("\nПроверяем внешние ссылки...")
        external_sample = list(unique_external.keys())[:3]  # Проверяем только 3 для примера
        
        for url in external_sample:
            link_info = {'url': url, 'link_type': 'external'}
            status = crawler.check_link_status(link_info)
            print(f"  {url}: {status.get('status_code', 'Error')} - {status.get('status_text', 'Unknown')}")

if __name__ == "__main__":
    print("ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ WEBSITE LINK ANALYZER")
    print("=" * 50)
    
    # Запускаем примеры
    try:
        example_basic_usage()
        example_advanced_usage() 
        example_specific_analysis()
        
        print("\n" + "=" * 50)
        print("Все примеры выполнены успешно!")
        print("Проверьте папки ./example_reports и ./advanced_reports для отчетов")
        
    except KeyboardInterrupt:
        print("\nПримеры прерваны пользователем")
    except Exception as e:
        print(f"\nОшибка в примерах: {e}")
        import traceback
        traceback.print_exc()