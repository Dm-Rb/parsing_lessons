import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


"""
Логика обхода сайта по категориям и дальнейшим сбором ссылон на товары
"""

def request_get(url, session, params=None):
    if params:
        url = url + params
    response = session.get(url)

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


def get_categories(url, session):
    html = request_get(url, session)
    soup = BeautifulSoup(html, 'html.parser') # создаём экземпляр класса парсера
    ul = soup.find('ul', class_="catalog-content__list")
    li_list: list = ul.find_all('li', class_="catalog-content__list-item")

    result: list = []
    for li in li_list:
        a = li.find('a', class_='catalog-content__list-link')
        category_name: str = ""
        category_url: str = ""
        try:
            category_name = a.text
            category_name = category_name.lstrip('\r\n')
            category_name = category_name.strip(' ')


        except:
            pass
        try:
            category_url = a.get('href')
        except:
            pass

        result.append(
            {
                "category_name": category_name,
                "category_url": category_url
            }
        )
    return result


def get_last_number_page_category(url, session):
    html = request_get(url, session)
    soup = BeautifulSoup(html, 'html.parser')
    ul = soup.find('ul', class_='pagination')
    li_list = ul.find_all('li')
    if li_list:
        a = li_list[-2].find('a')
        try:
            last_number_page = a.text
            return int(last_number_page.strip(' '))

        except:
            return None


def pagination(url, session, last_number_page=None):
    print('Начинаю обход с пагинацией')
    current_page_num = 1
    if not last_number_page:
        last_number_page = 1
    result = []
    while current_page_num <= last_number_page:
        print(f"Текущая страница пагинации номер: {str(current_page_num)}")
        page_url = url + f"?page={str(current_page_num)}"
        html = request_get(page_url, session)
        urls = collect_urls_from_catalog_page(html)
        result.extend(urls)
        current_page_num += 1

    return result

def main():
    result = []

    ua = UserAgent()  # Экхемппляр классса фейс юзер агент
    headers = {'User-Agent': ua.random,
               "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}  # заголовки
    session = requests.Session()  # Экхемппляр классса  сессии. Главный объект для сетевых запросов
    session.headers.update(headers) # прокидываем хедерс в объект сессии

    # получаем список категорий. списко категорий содержит пару: имя и ссылка
    root_catalog_url = "https://tatsumi.ru/catalog"
    categories_list = get_categories(root_catalog_url, session) # возвращает пару: имя и ссылка

    # итерируемся по списку категорий
    for category_item in categories_list:
        # category_item > {category_name: имя, category_url: ссылка}
        print(f"Текущая категория: {category_item['category_name']}")
        # получаем номер последней страницы для текущей категории
        last_number_page: int or None = get_last_number_page_category(url=category_item['category_url'], session=session)

        # вызываем функцию которая обходит категорию с параментром пагинации и возвращает список всех ссылок на товвары для этой категории

        product_urls = pagination(url=category_item['category_url'], session=session, last_number_page=last_number_page)

        category_obj = {
            'category_name': category_item['category_name'], # имя категории
            'product_urls': product_urls # список ссылок на товары
        }
        # category_obj > это словарь с двумя ключами. category_name содержит имя категории, а product_urls это
        # список всех ссылок длят этой категории

        result.append(category_obj) # добавляем в результирующий массив

if __name__ == "__main__":
    main()