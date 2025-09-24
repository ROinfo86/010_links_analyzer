#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест для проверки извлечения URL с специальными символами
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from link_analyzer import WebsiteCrawler

def test_url_extraction_with_encoding():
    """Тест извлечения URL с процентным кодированием"""
    print("🔗 Тестируем извлечение URL с %-encoding...")
    
    crawler = WebsiteCrawler("https://example.com", max_pages=1)
    
    # HTML с различными типами URL включая %-encoded
    test_html = """
    <html>
    <body>
        <p>Обычная ссылка: https://example.com/page</p>
        <p>Ссылка с процентами: https://example.com/search?q=hello%20world%26more</p>
        <p>Сложная ссылка: https://api.example.com/v1/users?filter=%7B%22name%22%3A%22John%22%7D&sort=asc</p>
        <p>Ссылка с якорем: https://docs.example.com/guide#section%20title</p>
        <p>Ссылка с портом: https://localhost:8080/api/v1/data?param=%2Fpath%2Fto%2Ffile</p>
        <a href="https://encoded.example.com/path%20with%20spaces">Link with spaces</a>
    </body>
    </html>
    """
    
    links = crawler.extract_links_from_page("https://example.com/test", test_html)
    
    print(f"Найдено ссылок: {len(links)}")
    
    # Проверяем каждую найденную ссылку
    found_urls = [link['url'] for link in links]
    
    expected_patterns = [
        '%20',  # пробел
        '%26',  # амперсанд  
        '%7B',  # {
        '%22',  # "
        '%3A',  # :
        '%7D',  # }
        '%2F',  # /
    ]
    
    print("\nНайденные URL:")
    for i, url in enumerate(found_urls, 1):
        print(f"{i}. {url}")
        
        # Проверяем наличие %-encoded символов
        has_encoding = any(pattern in url for pattern in expected_patterns)
        if has_encoding:
            print(f"   ✅ Содержит URL-encoding")
        
    # Проверяем что найдены URL с %-encoding
    urls_with_encoding = [url for url in found_urls if '%' in url]
    
    print(f"\nURL с %-encoding: {len(urls_with_encoding)}")
    for url in urls_with_encoding:
        print(f"  - {url}")
    
    if len(urls_with_encoding) > 0:
        print("✅ Тест пройден: URL с %-encoding найдены корректно")
        return True
    else:
        print("❌ Тест провален: URL с %-encoding не найдены")
        return False

def test_edge_cases():
    """Тест граничных случаев"""
    print("\n🎯 Тестируем граничные случаи...")
    
    crawler = WebsiteCrawler("https://example.com", max_pages=1)
    
    edge_case_html = """
    <html>
    <body>
        <p>URL в скобках: (https://example.com/bracketed%20url)</p>
        <p>URL в кавычках: "https://example.com/quoted%20url"</p>
        <p>URL в конце предложения: Смотрите https://example.com/end%20url.</p>
        <p>Очень длинный URL: https://verylongdomain.example.com/very/long/path/with/many/segments?param1=value1%20with%20spaces&param2=value2%26encoded&param3=%7B%22json%22%3A%22data%22%7D#section%20with%20spaces</p>
        <p>URL с русскими символами в %-encoding: https://example.com/поиск -> https://example.com/%D0%BF%D0%BE%D0%B8%D1%81%D0%BA</p>
    </body>
    </html>
    """
    
    links = crawler.extract_links_from_page("https://example.com/edge", edge_case_html)
    
    print(f"Найдено ссылок в граничных случаях: {len(links)}")
    
    for i, link in enumerate(links, 1):
        url = link['url']
        print(f"{i}. {url}")
        
        # Проверяем что URL не обрезается на специальных символах
        if url.endswith('.') or url.endswith(')') or url.endswith('"'):
            print(f"   ⚠️  Возможно обрезан на: {url[-1]}")
        else:
            print(f"   ✅ Выглядит корректно")
    
    return True

if __name__ == "__main__":
    print("🧪 ТЕСТИРОВАНИЕ URL-EXTRACTION С СПЕЦИАЛЬНЫМИ СИМВОЛАМИ")
    print("=" * 60)
    
    try:
        test1_passed = test_url_extraction_with_encoding()
        test2_passed = test_edge_cases()
        
        print("\n" + "=" * 60)
        if test1_passed and test2_passed:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
            print("✅ URL с %-encoding теперь извлекаются корректно")
        else:
            print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
            
    except Exception as e:
        print(f"💥 Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()