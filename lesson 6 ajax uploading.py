import pickle
import time
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import json
import re


"""логика работы с ajax запросами в случае подгрузки контента при скролинге вниз"""


session = requests.Session()


def request_get(url, session, params=None):
    """Посылает get запрос, получает ответ
    url - строка, ссылка на сайт
    session - объект сессии. олжен быть создан заранее и передан в функцию
    params - дополнительная cтрока для url, какие то параметры, например пагинация
    """
    if params:
        url = url + params
    response = session.get(url)

    if response.status_code != 200:
        raise ValueError(f"{url} код упал, стутус код не 200")

    return response.text


def request_post(url, session, params=None):
    """Посылает post запрос, получает ответ
    url - строка, ссылка на сайт
    session - объект сессии. олжен быть создан заранее и передан в функцию
    params - дополнительная cтрока для url, какие то параметры, например пагинация
    """

    response = session.post(url, data=params)

    return response.text


def get_products_url(url):
    """Стринца с товарам использует механизм бесконечной подгрузки контента при скролинге вниз"""

    product_urls = [] # результирующий массив в который складываем ссылки на продукты


    # Сперва сделаем обычный гет запрос по адресу. Получим первую пачку товаров, а так же получим параметры из вшитого
    # в хтмл документ яваскрипта. Этот парамент
    global session
    html = request_get(url, session)
    soup = BeautifulSoup(html, 'html.parser') # создаём экземпляр класса парсера
    elements: list = soup.select('div[class*="product-item"]') # находим первую пачку товаров на странице. используем селектор для поиска
    # это необходимо в случае когда нам нужно найти по одноиму классу из мультикласса

    for element in elements:
        a = element.find('a', class_='product-button')
        if a:
            product_url = a.get('href')
            product_urls.append(product_url)
    # нашли все товары первой пачки, переходим к поиску параметров для пост-запросов

    """В теле нтмл документа имеется яваскрипт код в котором содержится параметр vehicle_id. Он необходим для передачи в качестве параметра 
    в пост-запросе при имитации скролинга. Извлекаем значение этого параметра при помощи регулярных выражений. Пример кода:
    _request.send($.param({
                                vehicle_id: 62660, <<< найти и извлечь это
                                product_family: "",
                                page: ++current_page,
                                language: "ru"
                            }));
    
    """
    pattern = r"vehicle_id:\s*(\d+)," # паттерн по которому ищем

    match = re.search(pattern, html) # объект, который содержит найденные совпадения
    vehicle_id = None
    if match:  # если не None
        vehicle_id = match.group(1)

    # После того, как мы извлекли параметр для наших пост-запросов, формируем тело запроса и делаем пост-запросы
    current_page = 2  # параметр выдачи при скролинге. после каждой итерации увеличиваем на 1
    while True:
        pagination_params = {
            'vehicle_id': vehicle_id,
            'product_family': "",
            'page': str(current_page),
            'language': 'ru'
        }
        end_point_url = 'https://www.covind.it/template/ajax/is-vehicle.php'
        html = request_post(end_point_url, session, pagination_params)
        # получаем ответ, парсим так же как и предыдущие товары.
        if not html:
            break
        soup = BeautifulSoup(html, 'html.parser')  # создаём экземпляр класса парсера
        elements: list = soup.select('div[class*="product-item"]') # находим первую пачку товаров на странице. используем селектор для поиска
        if not elements:
            break
        for element in elements:
            a = element.find('a', class_='product-button')
            if a:
                product_url = a.get('href')
                # если url товара уже содержится в результирующем списке - значит мы пошли по кругу, выходим из цикла
                if product_url in product_urls:
                    return product_urls
                product_urls.append(product_url)
        current_page += 1

    return product_urls



