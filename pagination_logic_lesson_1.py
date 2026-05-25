import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

ua = UserAgent() # Экхемппляр классса фейс юзер агент


session = requests.Session()  # Экхемппляр классса  сессии. Главный объект для сетевых запросов


headers = {'User-Agent':  ua.random,
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"} # заголовки

session.headers.update(headers) # записываем заголовки в люъект сессии что бы они использовались каждый раз при каждом запросе


def request_get(url, params=None):
    if params:
        url = url + params
    response: requests = session.get(url)
    if response.status_code != 200:
        raise ValueError(f"{url} код упал, стутус код не 200")

    return response.text


def collect_urls_from_catalog_page(html_text): # функция для парсинга (разбора) html документа. достаёт все ссылки на товары
    soup = BeautifulSoup(html_text, 'html.parser') # создаём экземпляр класса парсера
    a_list: list = soup.find_all('a', class_='catalog-item__preview') # находим все теги <a> c классом "catalog-item__preview"
    # и записываем в переменную (с типом данных "список\массив") a_list
    product_urls = [] # создаём пустой масссив (переменая product_urls)
    for a in a_list: # итерируемся по элементам массива a_list. екажды элемент массива это тег <a>
        url: str = a.get('href') # извлекаем из тега <a>  краметр href и записываем в переменную url
        product_urls.append(url)

    return product_urls



url = "https://tatsumi.ru/catalog"
last_page = 779



result = []
for i in range(1, 779 + 1):
    params = f"/?page={str(i)}"
    print(params)
    html = request_get(url, params)
    product_urls = collect_urls_from_catalog_page(html)
    result.extend(product_urls)

print(result)
