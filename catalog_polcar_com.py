import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import re
import json
import time
from functools import wraps
import os


class StatusCodeError(Exception):
    """кастомное исключение для статус кода"""
    pass


def check_response_status(max_retries: int = 5, delay: int = 2):
    """
    декоратор для проверки статускода и повторных попыток при ошибке статуса.
    max_retries: максимальное количество попыток. при превышении - исключение
    delay: задержка между попытками в секундах
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    response = func(*args, **kwargs)
                    if isinstance(response, dict):
                        status = response.get('status_code')
                        url = response.get('url')
                        if status and status != 200:
                            raise StatusCodeError(f'HTTP {status} -> {url}')
                        return response.get('data')

                except StatusCodeError:
                    if attempt < max_retries:
                        time.sleep(delay)
                    else:
                        raise StatusCodeError
                except Exception as e:
                    # если любое другое исключение - немедленно возбуждаем
                    raise

        return wrapper
    return decorator


class Data:
    """Класс для хранения данных (промежуточных и итоговых)"""
    def __init__(self):
        self.manufacturers = []
        self.categories = []
        self.universal_models = []
        self.models = []
        self.products = []
        self.load() # загрузить данные при инициализации в аттрибуты класса из файла (если есть)

    def to_dict(self):
        """преобразует атрибуты класса в словарь (исключая методы)"""
        data = {
            k: v for k, v in self.__dict__.items() if not k.startswith('_') and not callable(v)
        }
        return data

    def write_to_file(self, path_file='Data.json'):
        """записывает аттрибуты класса в файл"""
        with open(path_file, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=4)

    def load(self, path_file: str = 'Data.json'):
        """
        загружает данные из файла в атрибуты экземпляра, совпадающие ключи записываются, несовпадающие - игнорируются.
        """
        if not os.path.exists(path_file):
            return False

        with open(path_file, 'r', encoding='utf-8') as f:
            file_data = json.load(f)
        if not isinstance(file_data, dict):
            return False

        # Сопоставляем ключи из файла с атрибутами экземпляра
        for key, value in file_data.items():
            if hasattr(self, key) and not key.startswith('_'):
                # Проверяем, что это не метод
                attr = getattr(self, key)
                if not callable(attr):
                    setattr(self, key, value)
        return

class Spider():
    """класс пасера. обходит сайт, собираает данные"""

    host = 'https://catalog.polcar.com'

    def __init__(self): # инициализация
        self.data = Data() # создаём экземпляр класса для хранения данных
        self.session = requests.Session() # создаём объект сессии
        self.set_user_agent() # записваем хедерс объекта сессии юзер агент и заголовок языка (метод ниже)
        self.update_headers() # получаем данные токенов и пробрасываем их в хередс объекта сессии

    def set_user_agent(self):
        """устанавливаем юзерагент в сессию"""
        ua = UserAgent()
        self.session.headers.update({'User-Agent': ua.random, 'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'})
        return

    def update_headers(self):
        """обновляем заголовки"""
        html = self.request_get('') # запрос к корню сайта, получаем html
        soup = self.get_bs(html)
        # парсим html и извлекаем значение csrf_token
        csrf_token = soup.find("meta", {"name": "csrf-token"})["content"]
        # обновляем хедерсы (X-XSRF-TOKEN извлекаем из кук)
        self.session.headers.update({
            "X-CSRF-TOKEN": csrf_token,
            "X-XSRF-TOKEN": self.session.cookies.get("XSRF-TOKEN"),
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.host}/",
            "Origin": self.host,
        })
        return

    @check_response_status()
    def request_get(self, url: str, host: bool = True):
        """Базовый метод для ГЕТ запросов"""
        response = self.session.get(url=self.host + url if host else url)
        response.encoding = response.apparent_encoding  # на случай проблем с кодировкой ответа
        data = response.text
        return {'url': url, 'status_code': response.status_code, 'data': data}

    @check_response_status()
    def request_post(self, url, body_data, host: bool = True):
        """Базовый метод для ПОСТ запросов"""
        response = self.session.post(url=self.host + url if host else url, json=body_data)
        data = response.json()
        return {'url': url, 'status_code': response.status_code, 'data': data}

    @staticmethod
    def get_bs(html_text):
        return BeautifulSoup(html_text, 'html.parser')

    def get_manufacturers_categories(self) -> list[list, list]:
        """Получаем список всех производителей с назанияями и айдишниками и список всех категорий с названиями и айдишниками"""
        html = self.request_get('')
        soup = self.get_bs(html)
        script_tags = soup.find_all('script')
        manufacturers_list = []
        categories_list = []
        for script in script_tags:
            # script.text - простыня текста с данными. используем регулярное выражение для извлечения необходимых данных
            pattern = r'"manufacturer":{"items":\[([^]]*?)\]\s*,?\s*"selected"'  # паттерн для manufacturer
            match = re.search(pattern, script.text, re.DOTALL)
            if match:
                # извлекаем содержимое между скобками
                extracted_data = match.group(1)
                # добавляем квадратные скобки обратно
                json_string = f'[{extracted_data}]'
                # десериализируем
                manufacturers_list = json.loads(json_string)
                ###
            pattern = r'window\.CATEGORIES_DATA\s*=\s*(\[[\s\S]*?\]);' # паттерн для categories
            match = re.search(pattern, script.text)

            if match:
                json_string = match.group(1)
                categories_list = json.loads(json_string)

        # manufacturers_list-> [{'id': str, 'name': str}, ...]
        # categories_list -> [str, str, ...]
        return [manufacturers_list, categories_list]

    def get_universal_models(self, manufacturer_item: dict) -> list[dict]:
        """Делаем пост запрос с производителем в параметрах и полуаем все доступные универсальные модели
        для этого производителя"""
        # manufacturer_item -> {"id": "kieiJ", "name": "ABARTH"}
        body_data = {"manufacturer_id": manufacturer_item['id']}
        r = self.request_post(url='/catalog/universal-models', body_data=body_data)
        # добавление ключа через копирование словаря
        # return -> [{'id': str, 'name': str, 'manufacturer_id': str, 'manufacturer_name': str}, {}, ...]
        return [{**item, "manufacturer_name": manufacturer_item['name']} for item in r]

    def get_models(self, universal_model_item: dict, category_code: str):
        """Делаем пост запрос, получаем список всех моделей для универсальной модели"""
        body_data = {"category_code": category_code, "universal_model_id": universal_model_item['id']}
        r = self.request_post(url='/catalog/models', body_data=body_data)
        result = []
        for item in r:
            item['universal_model_id'] = universal_model_item['id']
            item['universal_model_name'] = universal_model_item['name']
            item['manufacturer_id'] = universal_model_item['manufacturer_id']
            item['manufacturer_name'] = universal_model_item['manufacturer_name']
            result.append(item)
        return result

    def get_assortment_stats(self, model_item):
        """Делаем пост запрос, получаем ассортимент товаров для конкретной модели (содержит айдишнике товаров без детализации"""

        body_data = {"category_code": model_item['category_code'], "model_id": model_item['id']}
        r = self.request_post(url='/catalog/assortment/stats', body_data=body_data)
        return r

    def get_results(self, assortment_group_id, assortment_type_id, assortment_name_id, model_item):
        """Делаем пост запрос, получаем список товаров с базовой детализайцией"""

        body_data = {
            "category_code": model_item['category_code'],
            "assortment_group_id": assortment_group_id,
            "assortment_type_id": assortment_type_id,
            "assortment_name_id": None,
            "model_id": model_item['id'],
            "precise_model_id": None,
            "order_by": None,
            "filters":{},
            "page":1,
            "last_family_name":"",
            "families_count":0,
            "last_assortment_hash":""}
        r = self.request_post(url='/catalog/results', body_data=body_data)
        return r

    def get_product_details(self, public_id, number, url, model_item):
        """Делаем пост запрос, получаем полную детализацию для конкретного товара"""

        body_data = {"category": model_item['category_code'],
                     "number": number,
                     "appliance_id": public_id,
                     "referrer": url
                     }
        r = self.request_post(url='/catalog/product', body_data=body_data)
        return r

    def get_vehicles_categories(self):
        """Получить данные по транспортым средствам и каталогам"""

        # Получаем массивы с производителями и категориями
        # если данных нет в классе Data - вызвать метод и записать результат в класс. Данные есть - пропускаем этап
        if not (self.data.manufacturers and self.data.categories):
            self.data.manufacturers, self.data.categories = self.get_manufacturers_categories() # распаковка массива в две переменные
        # итерируемся по производителям и получаем универсальные модели
        for manufacturer_item in self.data.manufacturers:
            self.data.universal_models.extend(self.get_universal_models(manufacturer_item))
        self.data.write_to_file()  # Записать промежуточный результат в файл
        for category_item in self.data.categories: # итерируемся по категориям
            if category_item['code'] == "KatAkcesoria": # для этой категории отдельная логика с запросом к отдельному ендпоинту
                continue
            category_code = category_item['code']

            for universal_model_item in self.data.universal_models: # итерируемся по универсальным моделям
                model_item: list = self.get_models(universal_model_item, category_code) # получаем модели
                if not model_item:
                    continue
                self.data.models.extend(model_item)
            self.data.write_to_file() # хапись в файл

    def get_products(self):
        for model_item in self.data.models:
            stats = self.get_assortment_stats(model_item)
            for stat_item in stats:
                if stat_item.get('quantity', 0) == 0:
                    continue
                assortment_group_id = stat_item.get('id')
                for node in stat_item['nodes']:
                    if node['quantity'] == 0:
                        continue
                    assortment_type_id = node.get('id')
                    try:
                        prd_result = self.get_results(assortment_group_id, assortment_type_id, None, model_item)
                    except StatusCodeError:
                        continue

                    if prd_result.get('total', 0) == 0:
                        continue
                    for assortment_group in prd_result['assortment_groups']:
                        for family_group in assortment_group['family_groups']:
                            for part in family_group['parts']:
                                public_id = part['appliance_identifier']['public_id']
                                number = part['number']
                                url = part['urls']['self']
                                product_details = self.get_product_details(public_id, number, url, model_item)
                                if product_details:
                                    details = self.parsing_product_details(product_details)
                                    self.data.products.append(details)
            self.data.write_to_file('products.json')


    def parsing_product_details(self, product_details):
        """Дёрнуть из объекта только необходимые данные"""
        name = product_details['data']['part']['name']
        display = product_details['data']['part']['number']
        supplier = product_details['data']['part']['producer']
        params = []
        if product_details['data']['part']["features"]['part']:
            for item in product_details['data']['part']["features"]['part']:
                params.append(
                    {
                        "name": item['name'],
                        "value": item['value']
                    }
                )

        p1 = {'name': product_details['data']['part']['assortment']['group']['name']}
        p2 = {'name': product_details['data']['part']['assortment']['type']['name']}
        product = [p1, p2]
        providers_photos = product_details['data']['part']['urls']['providers_photos']
        images = []
        if providers_photos:
            try:
                images = self.request_get(providers_photos, host=False)
            except StatusCodeError:
                pass
        vehicle = {
            'manufacturer': product_details['data']['part']['manufacturer']['data']['name'],
            'model': product_details['data']['part']['model']['data']['name']
        }
        result = {
            'source_url': product_details['data']['part']['urls']['self'],
            'name': name,
            'display': display,
            'supplier': supplier,
            'params': params,
            'product': product,
            'applicability': vehicle,
            'images': images
        }
        return result


if __name__ == "__main__":
    spider = Spider()
    # получаем сперва список всех конечных моделей + категории
    spider.get_vehicles_categories()
    # обходим модели  и получаем все доступные товары
    spider.get_products()






