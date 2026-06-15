from playwright.sync_api import sync_playwright
from typing import List, Dict
import requests


# https://playwright.dev/python/docs/library
class NetworkTrafficAnalyzer:
    """Класс для перехвата всего трафика при обращении по какому либо урлу. Собирает и возвращает данные по всему стеку
    вызовов"""
    def __init__(self, headless: bool = True):  # отображать браузер или работать в скрытом режиме
        self.headless = headless

    def analyze_url(self, url: str) -> List[Dict]:  # Передаём функции урл для анализа. Метод возвращает список словарей
        traffic_data = []
        request_store: Dict[object, Dict] = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()

            def handle_request(request):
                request_store[request] = {
                    'url': request.url,
                    'method': request.method,
                    'request_headers': dict(request.headers),
                }

            def handle_response(response):
                request = response.request

                if request in request_store:
                    try:
                        body = response.text()
                    except Exception as e:
                        body = f"[Error getting response body: {e}]"

                    entry = request_store[request]
                    entry.update({
                        'status': response.status,
                        'response_headers': dict(response.headers),
                        'response_body': body,
                        'cookies': context.cookies(),
                    })
                    traffic_data.append(entry)

            page.on("request", handle_request)
            page.on("response", handle_response)

            page.goto(url, wait_until="networkidle")
            browser.close()
        # -> dict_keys(['url', 'method', 'request_headers', 'status', 'response_headers', 'response_body', 'cookies'])
        """Метод возвращает список словарей. Каждый словарь имеет ключи: url - содержит адрес запроса, method - метод запросаб
        request_headers - заголовки запроса, status - статускод, response_headers - заголовки ответа, 
        response_body - содержание ответа, cookies - куки (список словарей)"""
        return traffic_data


def get_cookies(url, filter_url) -> tuple:
    # создаём экземпляр класса NetworkTrafficAnalyzer в безголовом режиме (без отображения браузера)
    analyzer = NetworkTrafficAnalyzer(headless=True)
    results: list = analyzer.analyze_url(url) # делаем запрос, получаем ответ и сохраняем в переменную

    for entry in results:
        # начинаем итерироваться по списку
        # entry имеет следующаю сигнатуру -> dict['url', 'method', 'request_headers', 'status', 'response_headers', 'response_body', 'cookies']
        # нам нужен вызов по определённому адресу. фильтруем через условный оператор
        if 'https://catalogue.impergom.it/api/catalog/search?filters=' in entry['url']:

            # далее нам нужно немного преобразовать структуру значений по ключу cookies. создаём пустой словарь, в который будем всё хаписыввать
            result_cookies = {}

            for cookie_item in entry['cookies']:  # entry['cookies'] это список словарей
                # имеет такую сигнатуру
                # cookie_item -> dict['name', 'value', 'domain', 'path', ...]
                key_ = cookie_item['name']
                value_ = cookie_item['value']
                # нам нужно дёрнуть два ключа: cookie_item['name'] и cookie_item['value']
                # cookie_item['name'] (key_) записываем в качестве ключа в наш пустой словарь, cookie_item['value'] туда же в качестве значения
                result_cookies[key_] = value_

            # возвращаем кортеж из двух элементов: под индексом 0 у нас словаь с куками, под индексом 1 словаь с заголовками запроса
            return (result_cookies, entry['request_headers'])



session = requests.Session()
url = "https://catalogue.impergom.it/ru/search"  # адресс, по которому будем перехватывать траффик
# адресс, по которому будет фильтроваться траффик. запросы, которые не содержат данный filter_url будут отфутболиваться
filter_url = 'https://catalogue.impergom.it/api/catalog/search?filters='
template: tuple = get_cookies(url, filter_url)
cookies = template[0]  # содержит куки
headers = template[1]  # содержит заголовки запроса

session.headers.update(headers) # передаём в объект сессии заголовки, которые получили через NetworkTrafficAnalyzer
session.cookies.update(cookies) # передаём в объект сессии куки, которые получили через NetworkTrafficAnalyzer
# Делаем запрос к апи. Используя этот объект сессии обходим сайт до конца
r = session.get(url='https://catalogue.impergom.it/api/catalog/search?filters={}&page=1&perPage=24&sort=-createdAt&lang=ru')
print(r.status_code) #
print(r.json())

