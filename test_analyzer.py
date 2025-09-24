#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки функциональности анализатора ссылок
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from link_analyzer import WebsiteCrawler
import time

def test_basic_functionality():
    """Базовый тест функциональности"""
    print("🧪 Тестируем базовую функциональность...")
    
    try:
        # Создаем тестовый краулер
        crawler = WebsiteCrawler(
            base_url="https://httpbin.org",
            max_pages=2,
            delay=0.5,
            max_workers=2
        )
        
        print("✅ Создание краулера: OK")
        
        # Тестируем создание сессии
        assert crawler.session is not None
        print("✅ Создание сессии: OK")
        
        # Тестируем нормализацию URL
        test_url = crawler._normalize_url("/test", "https://example.com")
        assert test_url == "https://example.com/test"
        print("✅ Нормализация URL: OK")
        
        # Тестируем проверку домена
        assert crawler._is_same_domain("https://httpbin.org/test") == True
        assert crawler._is_same_domain("https://google.com") == False
        print("✅ Проверка домена: OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в базовом тесте: {e}")
        return False

def test_link_extraction():
    """Тест извлечения ссылок"""
    print("\n🔗 Тестируем извлечение ссылок...")
    
    try:
        crawler = WebsiteCrawler("https://example.com", max_pages=1)
        
        # Тестовый HTML
        test_html = """
        <html>
        <head>
            <link rel="stylesheet" href="/style.css">
        </head>
        <body>
            <a href="/page1">Internal Link</a>
            <a href="https://external.com">External Link</a>
            <img src="/image.jpg" alt="Test">
            <p>Check out https://textlink.com for more info</p>
        </body>
        </html>
        """
        
        links = crawler.extract_links_from_page("https://example.com", test_html)
        
        # Проверяем что ссылки найдены
        assert len(links) > 0
        print(f"✅ Найдено ссылок: {len(links)}")
        
        # Проверяем типы ссылок
        link_types = [link['link_type'] for link in links]
        assert 'internal' in link_types
        assert 'external' in link_types
        print("✅ Найдены внутренние и внешние ссылки: OK")
        
        # Проверяем различные теги
        tags = [link['tag'] for link in links]
        assert 'a' in tags
        print("✅ Извлечение из разных тегов: OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте извлечения ссылок: {e}")
        return False

def test_link_checking():
    """Тест проверки статуса ссылок"""
    print("\n🌐 Тестируем проверку статуса ссылок...")
    
    try:
        crawler = WebsiteCrawler("https://httpbin.org", max_pages=1)
        
        # Тестируем рабочую ссылку
        working_link = {
            'url': 'https://httpbin.org/status/200',
            'link_type': 'external'
        }
        
        result = crawler.check_link_status(working_link)
        
        assert result['url'] == working_link['url']
        assert 'status_code' in result
        assert 'response_time' in result
        print(f"✅ Проверка рабочей ссылки: статус {result.get('status_code')}")
        
        # Тестируем битую ссылку
        broken_link = {
            'url': 'https://httpbin.org/status/404',
            'link_type': 'external'
        }
        
        result = crawler.check_link_status(broken_link)
        assert result['status_code'] == 404
        print(f"✅ Проверка битой ссылки: статус {result.get('status_code')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте проверки ссылок: {e}")
        return False

def test_real_website():
    """Тест на реальном сайте"""
    print("\n🚀 Тестируем на реальном сайте...")
    
    try:
        crawler = WebsiteCrawler(
            base_url="https://httpbin.org",
            max_pages=3,
            delay=0.5,
            max_workers=2
        )
        
        print("Запускаем краткий обход сайта...")
        start_time = time.time()
        
        crawler.crawl_website()
        
        end_time = time.time()
        
        # Проверяем результаты
        assert len(crawler.visited_pages) > 0
        print(f"✅ Посещено страниц: {len(crawler.visited_pages)}")
        
        total_links = sum(len(links) for links in crawler.found_links.values())
        print(f"✅ Найдено ссылок: {total_links}")
        
        if total_links > 0:
            print("Проверяем несколько ссылок...")
            crawler.check_all_links()
            print(f"✅ Проверено уникальных ссылок: {len(crawler.link_status)}")
            
            if crawler.broken_links:
                print(f"⚠️  Найдено битых ссылок: {len(crawler.broken_links)}")
            else:
                print("✅ Битых ссылок не найдено")
        
        print(f"✅ Время выполнения: {end_time - start_time:.2f} секунд")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте реального сайта: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Главная функция тестирования"""
    print("🔬 ТЕСТИРОВАНИЕ WEBSITE LINK ANALYZER")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Запускаем тесты
    tests = [
        test_basic_functionality,
        test_link_extraction,
        test_link_checking,
        test_real_website
    ]
    
    for test_func in tests:
        try:
            if not test_func():
                all_tests_passed = False
        except Exception as e:
            print(f"❌ Критическая ошибка в {test_func.__name__}: {e}")
            all_tests_passed = False
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("✅ Анализатор ссылок готов к использованию")
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        print("⚠️  Проверьте конфигурацию и зависимости")
    
    return all_tests_passed

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1)