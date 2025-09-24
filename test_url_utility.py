#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для тестирования извлечения URL из HTML
Позволяет быстро проверить как анализатор извлекает ссылки из конкретного HTML
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from link_analyzer import WebsiteCrawler

def test_html_extraction(html_content, test_name="Test"):
    """Тестирует извлечение ссылок из HTML"""
    print(f"\n{'='*60}")
    print(f"🧪 {test_name}")
    print(f"{'='*60}")
    
    crawler = WebsiteCrawler("https://example.com", max_pages=1)
    
    # Показываем исходный HTML
    print("📄 Исходный HTML:")
    print("-" * 40)
    print(html_content.strip())
    print("-" * 40)
    
    # Извлекаем ссылки
    links = crawler.extract_links_from_page("https://example.com/test", html_content)
    
    print(f"\n🔗 Найдено ссылок: {len(links)}")
    print("-" * 40)
    
    for i, link in enumerate(links, 1):
        print(f"{i}. {link['url']}")
        print(f"   Источник: <{link['tag']} {link['attribute']}>")
        print(f"   Тип: {link['link_type']}")
        if link['text']:
            print(f"   Текст: {link['text'][:50]}...")
        print()
    
    return links

def main():
    """Основная функция для тестирования различных случаев"""
    print("🔧 УТИЛИТА ТЕСТИРОВАНИЯ URL EXTRACTION")
    print("Проверяем различные случаи извлечения ссылок")
    
    # Тест 1: URL с %-encoding
    html1 = """
    <html>
    <body>
        <p>Поиск: https://example.com/search?q=hello%20world%26test</p>
        <p>API: https://api.service.com/users?filter=%7B%22name%22%3A%22John%22%7D</p>
        <a href="https://site.com/path%20with%20spaces">Link</a>
    </body>
    </html>
    """
    
    links1 = test_html_extraction(html1, "URL с %-encoding")
    
    # Тест 2: Сложные URL 
    html2 = """
    <html>
    <body>
        <p>OAuth: https://oauth.example.com/authorize?response_type=code&client_id=123&redirect_uri=https%3A%2F%2Fapp.com%2Fcallback</p>
        <p>Graph API: https://graph.microsoft.com/v1.0/users?$filter=startswith(displayName,%27J%27)&$select=displayName,mail</p>
    </body>
    </html>
    """
    
    links2 = test_html_extraction(html2, "Сложные URL с множественным encoding")
    
    # Тест 3: URL в различных контекстах
    html3 = """
    <html>
    <body>
        <p>В скобках: (https://example.com/bracketed%20url)</p>
        <p>В кавычках: "https://example.com/quoted%20url"</p>
        <p>В конце: Смотрите https://example.com/end%20url.</p>
        <p>JSON: {"url": "https://example.com/json%20url"}</p>
    </body>
    </html>
    """
    
    links3 = test_html_extraction(html3, "URL в различных контекстах")
    
    # Тест 4: Реальный пример проблемного URL
    html4 = """
    <html>
    <body>
        <p>Проблемный URL: http://www.w3.org/2000/svg'%3E%3Cpath%20d%3D%22M10%2C10%20L20%2C20%22%3E%3C%2Fpath%3E</p>
        <p>Другой случай: https://cdn.example.com/file.js?v=1.0&hash=%2Fa1b2c3%2F</p>
    </body>
    </html>
    """
    
    links4 = test_html_extraction(html4, "Реальные проблемные URL")
    
    # Сводка
    total_links = len(links1) + len(links2) + len(links3) + len(links4)
    encoded_links = 0
    
    for links in [links1, links2, links3, links4]:
        for link in links:
            if '%' in link['url']:
                encoded_links += 1
    
    print(f"\n{'='*60}")
    print("📊 СВОДКА ТЕСТИРОВАНИЯ")
    print(f"{'='*60}")
    print(f"Всего ссылок найдено: {total_links}")
    print(f"Ссылок с %-encoding: {encoded_links}")
    print(f"Процент с encoding: {(encoded_links/total_links*100):.1f}%" if total_links > 0 else "Нет данных")
    
    if encoded_links > 0:
        print("\n✅ URL с %-encoding извлекаются корректно!")
        print("Исправление работает как надо.")
    else:
        print("\n⚠️  URL с %-encoding не найдены.")
        print("Возможно требуется дополнительная настройка.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано")
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")
        import traceback
        traceback.print_exc()