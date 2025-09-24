#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПРАВИЛЬНЫЙ анализатор ссылок - по логике пользователя:
1. Сначала собираем базу всех СТРАНИЦ сайта
2. Потом ищем все ссылки на каждой странице 
3. Проверяем статус каждой уникальной ссылки
4. Создаем отчет с привязкой битых ссылок к страницам
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
import logging
from typing import Set, Dict, List
from urllib.parse import urljoin, urlparse
import requests
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from bs4 import BeautifulSoup
import urllib.robotparser
import re

class WebsiteCrawler:
    """Краулер для обхода сайта и извлечения ссылок"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(self.base_url).netloc
        
        # Загружаем robots.txt один раз
        self.robots_parser = urllib.robotparser.RobotFileParser()
        self.robots_parser.set_url(f"{self.base_url}/robots.txt")
        try:
            self.robots_parser.read()
            logging.info(f"Robots.txt загружен с {self.base_url}/robots.txt")
        except:
            logging.warning(f"Не удалось загрузить robots.txt для {self.base_url}")
            self.robots_parser = None
    
    def extract_links_from_page(self, html_content: str, page_url: str) -> List[Dict]:
        """Извлекает все ссылки со страницы"""
        soup = BeautifulSoup(html_content, 'lxml')
        links = []
        
        # Регулярное выражение для URL (RFC 3986 compatible)
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        
        # Извлекаем ссылки из разных тегов
        link_selectors = [
            ('a', 'href'),
            ('img', 'src'),
            ('link', 'href'),
            ('script', 'src'),
            ('iframe', 'src'),
            ('form', 'action')
        ]
        
        for tag_name, attr_name in link_selectors:
            for tag in soup.find_all(tag_name):
                url = tag.get(attr_name)
                if url:
                    url = url.strip()
                    if url and not url.startswith('#') and not url.startswith('javascript:'):
                        # Нормализуем URL
                        full_url = urljoin(page_url, url)
                        
                        # Пропускаем нежелательные ссылки
                        if self._should_skip_url(full_url):
                            continue
                            
                        # Определяем тип ссылки
                        link_type = 'external'
                        if urlparse(full_url).netloc == self.domain:
                            link_type = 'internal'
                        
                        links.append({
                            'url': full_url,
                            'link_type': link_type,
                            'found_in_tag': tag_name,
                            'anchor_text': tag.get_text().strip() if tag_name == 'a' else ''
                        })
        
        return links
    
    def _should_skip_url(self, url: str) -> bool:
        """Проверяет, нужно ли пропустить URL"""
        url_lower = url.lower()
        
        # Пропускаем tel:, mailto:, etc.
        if any(url_lower.startswith(prefix) for prefix in ['tel:', 'mailto:', 'ftp:', 'data:']):
            return True
            
        # Пропускаем cdn-cgi и подобные
        if '/cdn-cgi/' in url_lower:
            return True
            
        return False

class ProperLinkAnalyzer:
    """Правильный анализатор по логике пользователя"""
    
    def __init__(self, base_url: str, output_dir: str = "./proper_analysis", 
                 delay: float = 1.0, max_workers: int = 3):
        """
        Инициализация анализатора
        
        Args:
            base_url: URL сайта для анализа
            output_dir: Директория для сохранения результатов
            delay: Задержка между запросами
            max_workers: Количество потоков для проверки ссылок
        """
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(self.base_url).netloc
        self.output_dir = Path(output_dir)
        self.delay = delay
        self.max_workers = max_workers
        
        # Создаем директории
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Базы данных
        self.all_pages = set()  # База всех страниц сайта
        self.all_links = {}     # {link_url: {'type': 'page/image/etc', 'found_on': [page1, page2]}}
        self.link_statuses = {} # {link_url: {'status_code': 200, 'error': None, 'response_time': 1.5}}
        
        # Настройка сессии
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(self.output_dir / "analysis.log", encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(f"ProperAnalyzer_{self.base_url}")
        
        # Создаем ОДИН анализатор для всей работы
        self.crawler = WebsiteCrawler(base_url=self.base_url)
        self.logger.info(f"Создан единый анализатор для {self.base_url}")
        self.logger = logging.getLogger(__name__)
        
    def _is_same_domain(self, url: str) -> bool:
        """Проверяет, принадлежит ли URL тому же домену"""
        try:
            parsed = urlparse(url)
            return parsed.netloc == self.domain
        except:
            return False
    
    def _is_html_page(self, url: str) -> bool:
        """Проверяет, является ли URL HTML страницей (не файлом)"""
        # Исключаем файлы по расширению
        excluded_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico',
            '.css', '.js', '.xml', '.pdf', '.zip', '.rar', '.txt',
            '.doc', '.docx', '.xls', '.xlsx', '.mp4', '.avi', '.mp3'
        ]
        
        url_lower = url.lower()
        for ext in excluded_extensions:
            if url_lower.endswith(ext):
                return False
                
        # Исключаем служебные пути
        excluded_paths = ['/cdn-cgi/', '/admin/', '/api/']
        for path in excluded_paths:
            if path in url_lower:
                return False
                
        return True
    
    def step1_collect_all_pages(self, max_pages: int = 1000) -> int:
        """
        ЭТАП 1: Собираем базу всех СТРАНИЦ сайта (ОПТИМИЗИРОВАННО)
        Returns: количество найденных страниц
        """
        self.logger.info("=" * 60)
        self.logger.info("ЭТАП 1: БЫСТРЫЙ СБОР ВСЕХ СТРАНИЦ САЙТА")
        self.logger.info(f"Максимум страниц: {max_pages}")
        self.logger.info("=" * 60)
        
        pages_to_visit = [self.base_url]
        pages_to_visit_set = {self.base_url}
        processed_count = 0
        
        while pages_to_visit and processed_count < max_pages:
            # Обрабатываем пакетами по несколько страниц
            batch_size = min(5, len(pages_to_visit))
            current_batch = []
            
            for _ in range(batch_size):
                if pages_to_visit:
                    page = pages_to_visit.pop(0)
                    if page not in self.all_pages:
                        current_batch.append(page)
                        
            if not current_batch:
                break
                
            self.logger.info(f"Обрабатываем пакет из {len(current_batch)} страниц...")
            
            batch_new_pages = 0
            for current_page in current_batch:
                try:
                    response = self.session.get(current_page, timeout=15, verify=False)
                    response.raise_for_status()
                    
                    # Добавляем страницу в базу
                    self.all_pages.add(current_page)
                    processed_count += 1
                    
                    # Используем ЕДИНЫЙ анализатор (robots.txt уже загружен!)
                    links = self.crawler.extract_links_from_page(response.text, current_page)
                    
                    # Собираем ВСЕ новые страницы сразу
                    for link in links:
                        link_url = link['url']
                        
                        if (link['link_type'] == 'internal' and 
                            self._is_html_page(link_url) and
                            link_url not in self.all_pages and
                            link_url not in pages_to_visit_set):
                            
                            pages_to_visit.append(link_url)
                            pages_to_visit_set.add(link_url)
                            batch_new_pages += 1
                    
                    time.sleep(self.delay * 0.2)  # Меньшая задержка внутри пакета
                    
                except Exception as e:
                    self.logger.error(f"Ошибка при сканировании {current_page}: {e}")
                    continue
            
            self.logger.info(f"Пакет обработан: +{batch_new_pages} новых страниц")
            self.logger.info(f"Всего страниц: {len(self.all_pages)}, в очереди: {len(pages_to_visit)}")
            
            # Задержка между пакетами
            time.sleep(self.delay)
        
        self.logger.info(f"ЭТАП 1 ЗАВЕРШЕН: Найдено {len(self.all_pages)} страниц")
        
        # Сохраняем базу страниц
        pages_file = self.output_dir / "all_pages.json"
        with open(pages_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.all_pages), f, ensure_ascii=False, indent=2)
            
        return len(self.all_pages)
    
    def step2_collect_all_links(self) -> int:
        """
        ЭТАП 2: Собираем ВСЕ ссылки с каждой страницы
        Returns: количество уникальных ссылок
        """
        self.logger.info("=" * 60)
        self.logger.info("ЭТАП 2: СБОР ВСЕХ ССЫЛОК С КАЖДОЙ СТРАНИЦЫ") 
        self.logger.info("=" * 60)
        
        processed_pages = 0
        
        for page_url in self.all_pages:
            try:
                self.logger.info(f"Извлекаем ссылки со страницы {processed_pages + 1}/{len(self.all_pages)}: {page_url}")
                
                response = self.session.get(page_url, timeout=15, verify=False)
                response.raise_for_status()
                
                # Используем ЕДИНЫЙ анализатор
                links = self.crawler.extract_links_from_page(response.text, page_url)
                
                # Обрабатываем все найденные ссылки
                new_links_count = 0
                for link in links:
                    link_url = link['url']
                    
                    # Определяем тип ссылки
                    link_type = 'external'
                    if link['link_type'] == 'internal':
                        if self._is_html_page(link_url):
                            link_type = 'page'
                        elif any(link_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']):
                            link_type = 'image'
                        elif any(link_url.lower().endswith(ext) for ext in ['.css', '.js']):
                            link_type = 'resource'
                        else:
                            link_type = 'file'
                    
                    # Добавляем в базу ссылок
                    if link_url not in self.all_links:
                        self.all_links[link_url] = {
                            'type': link_type,
                            'found_on': [page_url]
                        }
                        new_links_count += 1
                    else:
                        # Добавляем страницу в список, где найдена ссылка (если еще нет)
                        if page_url not in self.all_links[link_url]['found_on']:
                            self.all_links[link_url]['found_on'].append(page_url)
                
                processed_pages += 1
                self.logger.info(f"Найдено {new_links_count} новых уникальных ссылок")
                self.logger.info(f"Всего уникальных ссылок: {len(self.all_links)}")
                
                time.sleep(self.delay)
                
            except Exception as e:
                self.logger.error(f"Ошибка при обработке {page_url}: {e}")
                continue
        
        self.logger.info(f"ЭТАП 2 ЗАВЕРШЕН: Найдено {len(self.all_links)} уникальных ссылок")
        
        # Сохраняем базу ссылок
        links_file = self.output_dir / "all_links.json"
        with open(links_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_links, f, ensure_ascii=False, indent=2)
            
        return len(self.all_links)
    
    def step3_check_link_statuses(self) -> Dict:
        """
        ЭТАП 3: Проверяем статус каждой уникальной ссылки
        Returns: статистика проверки
        """
        self.logger.info("=" * 60)
        self.logger.info("ЭТАП 3: ПРОВЕРКА СТАТУСА КАЖДОЙ ССЫЛКИ")
        self.logger.info("=" * 60)
        
        total_links = len(self.all_links)
        checked_links = 0
        broken_links = 0
        
        for link_url in self.all_links:
            try:
                checked_links += 1
                self.logger.info(f"Проверяем ссылку {checked_links}/{total_links}: {link_url}")
                
                start_time = time.time()
                response = self.session.get(link_url, timeout=10, verify=False)
                response_time = time.time() - start_time
                
                status_code = response.status_code
                error = None
                
                if status_code != 200:
                    broken_links += 1
                    
            except Exception as e:
                status_code = None
                error = str(e)
                response_time = None
                broken_links += 1
            
            # Сохраняем результат
            self.link_statuses[link_url] = {
                'status_code': status_code,
                'error': error,
                'response_time': response_time,
                'checked_at': datetime.now().isoformat()
            }
            
            if checked_links % 50 == 0:
                self.logger.info(f"Проверено {checked_links}/{total_links} ссылок, битых: {broken_links}")
            
            time.sleep(self.delay * 0.5)  # Меньшая задержка для проверки
        
        stats = {
            'total_links': total_links,
            'checked_links': checked_links,
            'broken_links': broken_links,
            'working_links': checked_links - broken_links
        }
        
        self.logger.info(f"ЭТАП 3 ЗАВЕРШЕН: Проверено {checked_links} ссылок, битых: {broken_links}")
        
        # Сохраняем статусы
        statuses_file = self.output_dir / "link_statuses.json"
        with open(statuses_file, 'w', encoding='utf-8') as f:
            json.dump(self.link_statuses, f, ensure_ascii=False, indent=2)
            
        return stats
    
    def step4_create_reports(self) -> None:
        """
        ЭТАП 4: Создаем отчеты с привязкой битых ссылок к страницам
        """
        self.logger.info("=" * 60)
        self.logger.info("ЭТАП 4: СОЗДАНИЕ ОТЧЕТОВ")
        self.logger.info("=" * 60)
        
        # Отчет битых ссылок с привязкой к страницам
        broken_links_report = {}
        
        for link_url, link_info in self.all_links.items():
            status = self.link_statuses.get(link_url, {})
            
            # Если ссылка битая
            if (status.get('status_code') != 200 or status.get('error')):
                broken_links_report[link_url] = {
                    'type': link_info['type'],
                    'status_code': status.get('status_code'),
                    'error': status.get('error'),
                    'found_on_pages': link_info['found_on'],
                    'pages_count': len(link_info['found_on'])
                }
        
        # Сохраняем отчет битых ссылок
        broken_report_file = self.output_dir / "broken_links_report.json"
        with open(broken_report_file, 'w', encoding='utf-8') as f:
            json.dump(broken_links_report, f, ensure_ascii=False, indent=2)
        
        # Создаем текстовый отчет
        txt_report_file = self.output_dir / "analysis_report.txt"
        with open(txt_report_file, 'w', encoding='utf-8') as f:
            f.write("АНАЛИЗ ССЫЛОК САЙТА\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Сайт: {self.base_url}\n")
            f.write(f"Дата анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("СТАТИСТИКА:\n")
            f.write(f"Всего страниц на сайте: {len(self.all_pages)}\n")
            f.write(f"Всего уникальных ссылок: {len(self.all_links)}\n")
            f.write(f"Битых ссылок: {len(broken_links_report)}\n\n")
            
            f.write("БИТЫЕ ССЫЛКИ ПО СТРАНИЦАМ:\n")
            f.write("-" * 50 + "\n")
            
            for link_url, info in broken_links_report.items():
                f.write(f"\nБитая ссылка: {link_url}\n")
                f.write(f"Тип: {info['type']}\n")
                f.write(f"Статус: {info['status_code'] or 'ERROR'}\n")
                if info['error']:
                    f.write(f"Ошибка: {info['error']}\n")
                f.write(f"Найдена на {info['pages_count']} страницах:\n")
                for page in info['found_on_pages']:
                    f.write(f"  - {page}\n")
                f.write("\n" + "-" * 30 + "\n")
        
        self.logger.info(f"Отчеты созданы:")
        self.logger.info(f"  JSON: {broken_report_file}")
        self.logger.info(f"  TXT: {txt_report_file}")
    
    def run_full_analysis(self) -> Dict:
        """Запускает полный анализ по правильной логике"""
        start_time = time.time()
        
        self.logger.info("ЗАПУСК ПОЛНОГО АНАЛИЗА САЙТА")
        self.logger.info(f"Сайт: {self.base_url}")
        self.logger.info(f"Задержка: {self.delay}с")
        self.logger.info("=" * 60)
        
        try:
            # ЭТАП 1: Собираем все страницы
            pages_count = self.step1_collect_all_pages()
            
            # ЭТАП 2: Собираем все ссылки
            links_count = self.step2_collect_all_links()
            
            # ЭТАП 3: Проверяем статусы
            stats = self.step3_check_link_statuses()
            
            # ЭТАП 4: Создаем отчеты
            self.step4_create_reports()
            
            total_time = time.time() - start_time
            
            final_stats = {
                'pages_found': pages_count,
                'links_found': links_count,
                'broken_links': stats['broken_links'],
                'analysis_time': total_time
            }
            
            self.logger.info("=" * 60)
            self.logger.info("АНАЛИЗ ЗАВЕРШЕН УСПЕШНО!")
            self.logger.info(f"Время выполнения: {total_time:.1f} секунд")
            self.logger.info(f"Найдено страниц: {pages_count}")
            self.logger.info(f"Найдено ссылок: {links_count}")
            self.logger.info(f"Битых ссылок: {stats['broken_links']}")
            self.logger.info("=" * 60)
            
            return final_stats
            
        except Exception as e:
            self.logger.error(f"Ошибка при анализе: {e}")
            raise

def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Правильный анализ ссылок сайта по этапам')
    parser.add_argument('url', help='URL сайта для анализа')
    parser.add_argument('--delay', type=float, default=1.0, help='Задержка между запросами')
    parser.add_argument('--workers', type=int, default=3, help='Количество потоков')
    parser.add_argument('--output', default='./proper_analysis', help='Директория для результатов')
    
    args = parser.parse_args()
    
    analyzer = ProperLinkAnalyzer(
        base_url=args.url,
        output_dir=args.output,
        delay=args.delay,
        max_workers=args.workers
    )
    
    analyzer.run_full_analysis()

if __name__ == "__main__":
    main()