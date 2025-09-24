#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Website Link Analyzer
Анализатор ссылок веб-сайта для поиска битых ссылок

Автор: Анализатор битых ссылок
Версия: 1.0
"""

import requests
import urllib3
from urllib.parse import urljoin, urlparse, unquote
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
import re
import json
import csv
import time
import logging
from datetime import datetime
from typing import Set, Dict, List, Tuple
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Отключаем предупреждения SSL для некорректных сертификатов
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WebsiteCrawler:
    """Класс для обхода веб-сайта и анализа ссылок"""
    
    def __init__(self, base_url: str, max_pages: int = 100, delay: float = 1.0, 
                 respect_robots: bool = True, timeout: int = 10, 
                 max_workers: int = 5, user_agent: str = None):
        """
        Инициализация краулера
        
        Args:
            base_url: Базовый URL сайта
            max_pages: Максимальное количество страниц для обхода
            delay: Задержка между запросами в секундах
            respect_robots: Учитывать ли robots.txt
            timeout: Таймаут для HTTP запросов
            max_workers: Количество потоков для параллельной обработки
            user_agent: User-Agent для запросов
        """
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.delay = delay
        self.timeout = timeout
        self.max_workers = max_workers
        
        # Настройка User-Agent
        self.user_agent = user_agent or (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        
        # Настройка логирования (должно быть первым)
        self._setup_logging()
        
        # Множества для хранения обработанных данных
        self.visited_pages: Set[str] = set()
        self.found_links: Dict[str, List[Dict]] = {}  # страница -> список ссылок
        self.link_status: Dict[str, Dict] = {}  # ссылка -> статус
        self.broken_links: List[Dict] = []
        
        # Настройка robots.txt
        self.respect_robots = respect_robots
        self.robot_parser = None
        if respect_robots:
            self._load_robots_txt()
        
        # Настройка сессии
        self.session = self._create_session()
        
    def _setup_logging(self):
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('link_analyzer.log', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def _create_session(self) -> requests.Session:
        """Создание сессии с настройками повторных попыток"""
        session = requests.Session()
        
        # Настройка повторных попыток
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Настройка заголовков
        session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        return session
        
    def _load_robots_txt(self):
        """Загрузка и парсинг robots.txt"""
        try:
            robots_url = urljoin(self.base_url, '/robots.txt')
            self.robot_parser = RobotFileParser()
            self.robot_parser.set_url(robots_url)
            self.robot_parser.read()
            self.logger.info(f"Robots.txt загружен с {robots_url}")
        except Exception as e:
            self.logger.warning(f"Не удалось загрузить robots.txt: {e}")
            self.robot_parser = None
            
    def _can_fetch(self, url: str) -> bool:
        """Проверка разрешения на обход URL согласно robots.txt"""
        if not self.robot_parser:
            return True
        try:
            return self.robot_parser.can_fetch(self.user_agent, url)
        except:
            return True
            
    def _is_same_domain(self, url: str) -> bool:
        """Проверка принадлежности URL к тому же домену"""
        try:
            parsed = urlparse(url)
            return parsed.netloc == self.domain or parsed.netloc == ''
        except:
            return False
            
    def _normalize_url(self, url: str, base_url: str) -> str:
        """Нормализация URL"""
        try:
            # Удаляем якоря (но сохраняем их если они важны для идентификации)
            anchor = ''
            if '#' in url:
                url, anchor = url.split('#', 1)
            
            # Создаем абсолютный URL
            absolute_url = urljoin(base_url, url)
            
            # НЕ декодируем URL - сохраняем %-encoding как есть
            # absolute_url = unquote(absolute_url)  # Комментируем эту строку
            
            # Добавляем якорь обратно если он был
            if anchor:
                absolute_url += '#' + anchor
                
            return absolute_url.rstrip('/')
        except:
            return url
            
    def extract_links_from_page(self, url: str, html_content: str) -> List[Dict]:
        """
        Извлечение всех ссылок со страницы
        
        Args:
            url: URL страницы
            html_content: HTML содержимое страницы
            
        Returns:
            Список словарей с информацией о ссылках
        """
        links = []
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Извлекаем ссылки из различных тегов и атрибутов
            link_selectors = [
                ('a', 'href'),
                ('link', 'href'),
                ('img', 'src'),
                ('script', 'src'),
                ('iframe', 'src'),
                ('frame', 'src'),
                ('embed', 'src'),
                ('object', 'data'),
                ('source', 'src'),
                ('video', 'src'),
                ('audio', 'src'),
                ('form', 'action'),
                ('area', 'href'),
                ('base', 'href'),
            ]
            
            # Извлечение ссылок из тегов
            for tag_name, attr_name in link_selectors:
                elements = soup.find_all(tag_name, {attr_name: True})
                for element in elements:
                    link_url = element.get(attr_name, '').strip()
                    if link_url:
                        normalized_url = self._normalize_url(link_url, url)
                        if normalized_url and normalized_url != url:
                            links.append({
                                'url': normalized_url,
                                'source_page': url,
                                'tag': tag_name,
                                'attribute': attr_name,
                                'text': element.get_text(strip=True)[:100] if element.get_text(strip=True) else '',
                                'link_type': 'internal' if self._is_same_domain(normalized_url) else 'external'
                            })
            
            # Поиск URL в тексте (улучшенный regex с правильными границами)
            text_content = soup.get_text()
            # Паттерн включает все допустимые символы в URL включая %-encoding
            # Исключаем символы которые обычно завершают URL в тексте
            url_pattern = re.compile(
                r'https?://[^\s<>"{}|\\^`\[\]()]+(?:\([^\s)]*\))*[^\s<>"{}|\\^`\[\]().,;:!?]',
                re.IGNORECASE
            )
            
            text_urls = url_pattern.findall(text_content)
            for text_url in text_urls:
                normalized_url = self._normalize_url(text_url, url)
                if normalized_url and normalized_url != url:
                    # Проверяем, что эта ссылка уже не найдена в тегах
                    existing_urls = [link['url'] for link in links]
                    if normalized_url not in existing_urls:
                        links.append({
                            'url': normalized_url,
                            'source_page': url,
                            'tag': 'text',
                            'attribute': 'content',
                            'text': text_url[:100],
                            'link_type': 'internal' if self._is_same_domain(normalized_url) else 'external'
                        })
            
        except Exception as e:
            self.logger.error(f"Ошибка при извлечении ссылок с {url}: {e}")
            
        return links
        
    def check_link_status(self, link_info: Dict) -> Dict:
        """
        Проверка статуса ссылки
        
        Args:
            link_info: Словарь с информацией о ссылке
            
        Returns:
            Словарь с результатами проверки
        """
        url = link_info['url']
        result = {
            'url': url,
            'status_code': None,
            'status_text': '',
            'response_time': None,
            'error': None,
            'redirect_url': None,
            'content_type': None,
            'final_url': url
        }
        
        try:
            start_time = time.time()
            
            # Выполняем HEAD запрос сначала (быстрее)
            try:
                response = self.session.head(
                    url, 
                    timeout=self.timeout, 
                    allow_redirects=True,
                    verify=False  # Игнорируем SSL ошибки
                )
                
                # Если HEAD не поддерживается, делаем GET
                if response.status_code == 405:
                    response = self.session.get(
                        url, 
                        timeout=self.timeout, 
                        allow_redirects=True,
                        verify=False,
                        stream=True  # Не загружаем весь контент
                    )
                    
            except requests.exceptions.SSLError:
                # Если SSL ошибка, пробуем без проверки сертификата
                response = self.session.get(
                    url, 
                    timeout=self.timeout, 
                    allow_redirects=True,
                    verify=False,
                    stream=True
                )
            
            end_time = time.time()
            
            result.update({
                'status_code': response.status_code,
                'status_text': response.reason or '',
                'response_time': round(end_time - start_time, 2),
                'final_url': response.url,
                'content_type': response.headers.get('content-type', '').split(';')[0]
            })
            
            # Проверяем, был ли редирект
            if response.url != url:
                result['redirect_url'] = response.url
                
        except requests.exceptions.Timeout:
            result['error'] = 'Timeout'
            result['status_text'] = 'Request Timeout'
        except requests.exceptions.ConnectionError as e:
            result['error'] = f'Connection Error: {str(e)}'
            result['status_text'] = 'Connection Failed'
        except requests.exceptions.TooManyRedirects:
            result['error'] = 'Too Many Redirects'
            result['status_text'] = 'Redirect Loop'
        except requests.exceptions.RequestException as e:
            result['error'] = f'Request Error: {str(e)}'
            result['status_text'] = 'Request Failed'
        except Exception as e:
            result['error'] = f'Unknown Error: {str(e)}'
            result['status_text'] = 'Unknown Error'
            
        return result
        
    def crawl_website(self):
        """Основной метод для обхода веб-сайта"""
        self.logger.info(f"Начинаем обход сайта: {self.base_url}")
        
        # Начинаем с главной страницы
        pages_to_visit = [self.base_url]
        pages_visited = 0
        
        while pages_to_visit and pages_visited < self.max_pages:
            current_url = pages_to_visit.pop(0)
            
            # Пропускаем уже посещенные страницы
            if current_url in self.visited_pages:
                continue
                
            # Проверяем robots.txt
            if not self._can_fetch(current_url):
                self.logger.info(f"Пропускаем {current_url} согласно robots.txt")
                continue
                
            try:
                self.logger.info(f"Обрабатываем страницу {pages_visited + 1}/{self.max_pages}: {current_url}")
                
                # Запрашиваем страницу
                response = self.session.get(
                    current_url, 
                    timeout=self.timeout,
                    verify=False
                )
                response.raise_for_status()
                
                # Добавляем в посещенные
                self.visited_pages.add(current_url)
                pages_visited += 1
                
                # Извлекаем ссылки
                links = self.extract_links_from_page(current_url, response.text)
                self.found_links[current_url] = links
                
                self.logger.info(f"Найдено {len(links)} ссылок на странице {current_url}")
                
                # Добавляем новые внутренние страницы для обхода
                for link in links:
                    link_url = link['url']
                    if (link['link_type'] == 'internal' and 
                        link_url not in self.visited_pages and 
                        link_url not in pages_to_visit and
                        self._is_same_domain(link_url)):
                        pages_to_visit.append(link_url)
                
                # Задержка между запросами
                time.sleep(self.delay)
                
            except Exception as e:
                self.logger.error(f"Ошибка при обработке {current_url}: {e}")
                continue
                
        self.logger.info(f"Обход завершен. Посещено страниц: {pages_visited}")
        
    def check_all_links(self):
        """Проверка всех найденных ссылок"""
        # Собираем все уникальные ссылки
        all_links = {}
        for page_url, links in self.found_links.items():
            for link in links:
                link_url = link['url']
                if link_url not in all_links:
                    all_links[link_url] = []
                all_links[link_url].append(link)
        
        total_links = len(all_links)
        self.logger.info(f"Начинаем проверку {total_links} уникальных ссылок")
        
        # Проверяем ссылки параллельно
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Создаем задачи для проверки ссылок
            future_to_url = {}
            for link_url, link_instances in all_links.items():
                # Берем первый экземпляр ссылки для проверки
                future = executor.submit(self.check_link_status, link_instances[0])
                future_to_url[future] = (link_url, link_instances)
            
            # Обрабатываем результаты
            completed = 0
            for future in as_completed(future_to_url):
                link_url, link_instances = future_to_url[future]
                completed += 1
                
                try:
                    result = future.result()
                    self.link_status[link_url] = result
                    
                    # Логируем прогресс
                    if completed % 10 == 0 or completed == total_links:
                        self.logger.info(f"Проверено ссылок: {completed}/{total_links}")
                    
                    # Если ссылка битая, добавляем в список проблемных
                    status_code = result.get('status_code')
                    if (status_code is None or status_code >= 400 or 
                        result.get('error') is not None):
                        
                        for link_instance in link_instances:
                            broken_link = {
                                **link_instance,
                                **result
                            }
                            self.broken_links.append(broken_link)
                            
                except Exception as e:
                    self.logger.error(f"Ошибка при проверке {link_url}: {e}")
                    
        self.logger.info(f"Проверка завершена. Найдено битых ссылок: {len(self.broken_links)}")
        
    def generate_reports(self, output_dir: str = "."):
        """Генерация отчетов в различных форматах"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON отчет
        json_report = {
            'scan_info': {
                'base_url': self.base_url,
                'scan_date': datetime.now().isoformat(),
                'pages_scanned': len(self.visited_pages),
                'total_links_found': sum(len(links) for links in self.found_links.values()),
                'unique_links': len(self.link_status),
                'broken_links_count': len(self.broken_links)
            },
            'visited_pages': list(self.visited_pages),
            'broken_links': self.broken_links,
            'all_links_status': self.link_status
        }
        
        json_filename = f"{output_dir}/link_analysis_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, ensure_ascii=False, indent=2)
        
        # CSV отчет с битыми ссылками
        csv_filename = f"{output_dir}/broken_links_{timestamp}.csv"
        if self.broken_links:
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'source_page', 'url', 'link_type', 'tag', 'attribute', 
                    'text', 'status_code', 'status_text', 'error', 
                    'response_time', 'final_url', 'content_type'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for link in self.broken_links:
                    row = {field: link.get(field, '') for field in fieldnames}
                    writer.writerow(row)
        
        # Текстовый отчет
        txt_filename = f"{output_dir}/link_analysis_report_{timestamp}.txt"
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(f"ОТЧЕТ ОБ АНАЛИЗЕ ССЫЛОК\n")
            f.write(f"=" * 50 + "\n\n")
            f.write(f"Сайт: {self.base_url}\n")
            f.write(f"Дата сканирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Обработано страниц: {len(self.visited_pages)}\n")
            f.write(f"Найдено уникальных ссылок: {len(self.link_status)}\n")
            f.write(f"Найдено битых ссылок: {len(self.broken_links)}\n\n")
            
            if self.broken_links:
                f.write("БИТЫЕ ССЫЛКИ:\n")
                f.write("-" * 30 + "\n\n")
                
                # Группируем по исходным страницам
                broken_by_page = {}
                for link in self.broken_links:
                    page = link['source_page']
                    if page not in broken_by_page:
                        broken_by_page[page] = []
                    broken_by_page[page].append(link)
                
                for page, links in broken_by_page.items():
                    f.write(f"Страница: {page}\n")
                    for link in links:
                        f.write(f"  - {link['url']}\n")
                        f.write(f"    Статус: {link.get('status_code', 'N/A')} - {link.get('status_text', '')}\n")
                        f.write(f"    Тип: {link['link_type']}\n")
                        if link.get('error'):
                            f.write(f"    Ошибка: {link['error']}\n")
                        f.write("\n")
            
        self.logger.info(f"Отчеты сохранены:")
        self.logger.info(f"  - JSON: {json_filename}")
        self.logger.info(f"  - CSV: {csv_filename}")
        self.logger.info(f"  - TXT: {txt_filename}")


def main():
    """Главная функция программы"""
    parser = argparse.ArgumentParser(
        description='Анализатор битых ссылок веб-сайта',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python link_analyzer.py https://example.com
  python link_analyzer.py https://example.com --max-pages 50 --delay 0.5
  python link_analyzer.py https://example.com --output ./reports --no-robots
        """
    )
    
    parser.add_argument('url', help='URL сайта для анализа')
    parser.add_argument('--max-pages', type=int, default=100, 
                        help='Максимальное количество страниц для обхода (по умолчанию: 100)')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Задержка между запросами в секундах (по умолчанию: 1.0)')
    parser.add_argument('--timeout', type=int, default=10,
                        help='Таймаут для HTTP запросов в секундах (по умолчанию: 10)')
    parser.add_argument('--max-workers', type=int, default=5,
                        help='Количество потоков для проверки ссылок (по умолчанию: 5)')
    parser.add_argument('--output', default='.',
                        help='Директория для сохранения отчетов (по умолчанию: текущая)')
    parser.add_argument('--no-robots', action='store_true',
                        help='Игнорировать robots.txt')
    parser.add_argument('--user-agent', 
                        help='Кастомный User-Agent для запросов')
                        
    args = parser.parse_args()
    
    # Проверяем URL
    if not args.url.startswith(('http://', 'https://')):
        print("Ошибка: URL должен начинаться с http:// или https://")
        sys.exit(1)
    
    try:
        # Создаем экземпляр краулера
        crawler = WebsiteCrawler(
            base_url=args.url,
            max_pages=args.max_pages,
            delay=args.delay,
            respect_robots=not args.no_robots,
            timeout=args.timeout,
            max_workers=args.max_workers,
            user_agent=args.user_agent
        )
        
        # Выполняем анализ
        print(f"Начинаем анализ сайта: {args.url}")
        print(f"Максимум страниц: {args.max_pages}")
        print(f"Задержка между запросами: {args.delay}s")
        print(f"Потоков для проверки ссылок: {args.max_workers}")
        print("-" * 50)
        
        start_time = time.time()
        
        # Обходим сайт
        crawler.crawl_website()
        
        # Проверяем все ссылки
        crawler.check_all_links()
        
        # Генерируем отчеты
        crawler.generate_reports(args.output)
        
        end_time = time.time()
        total_time = round(end_time - start_time, 2)
        
        print("-" * 50)
        print("АНАЛИЗ ЗАВЕРШЕН")
        print(f"Время выполнения: {total_time} секунд")
        print(f"Обработано страниц: {len(crawler.visited_pages)}")
        print(f"Найдено уникальных ссылок: {len(crawler.link_status)}")
        print(f"Битых ссылок: {len(crawler.broken_links)}")
        
        if crawler.broken_links:
            print("\nТОП-10 БИТЫХ ССЫЛОК:")
            for i, link in enumerate(crawler.broken_links[:10], 1):
                print(f"{i}. {link['url']} (статус: {link.get('status_code', 'N/A')})")
        
    except KeyboardInterrupt:
        print("\nАнализ прерван пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()