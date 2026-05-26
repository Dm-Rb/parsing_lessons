import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import json
"""
Логика обхода сайта по категориям и парсинг данных на целевых страницах (сатраницы-карточки товаров)
"""


def request_get(url, session, params=None):
    """Посылает запрос, получает ответ
    url - строка, ссылка на сайт
    session - объект сессии. должен быть создан заранее и передан в функцию
    params - дополнительная cтрока для url, какие то параметры, например пагинация
    """
    if params:
        url = url + params
    response = session.get(url)

    if response.status_code != 200:
        raise ValueError(f"{url} код упал, стутус код не 200")

    return response.text


def collect_urls_from_catalog_page(
        html_text):  # функция для парсинга (разбора) html документа. достаёт все ссылки на товары
    """
    Функция собирает ссылки на товары
    html_text - html документ страницы полученный в ходе ответа от функции request_get
    """
    soup = BeautifulSoup(html_text, 'html.parser')  # создаём экземпляр класса парсера
    a_list: list = soup.find_all('a',
                                 class_='catalog-item__preview')  # находим все теги <a> c классом "catalog-item__preview"
    # и записываем в переменную (с типом данных "список\массив") a_list
    product_urls = []  # создаём пустой масссив (переменая product_urls)
    for a in a_list:  # итерируемся по элементам массива a_list. екажды элемент массива это тег <a>
        url: str = a.get('href')  # извлекаем из тега <a>  краметр href и записываем в переменную url
        product_urls.append(url)

    return product_urls


def get_categories(url, session):
    """
    Функция собирает ссылки на категории и имена категорий
    """
    html = request_get(url, session)
    soup = BeautifulSoup(html, 'html.parser')  # создаём экземпляр класса парсера
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
    """Получает номер последней страницы в категории. Используем для пагинации"""
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
    """Фунция осуществления пагинации. Генерирует каждый раз новую строку url и поввторяет запросы до тех пор, покуда
    значение текушей страницы не станет больше значения последней страницы"""
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


def get_product_details(url, session):
    response = request_get(url, session)
    soup = BeautifulSoup(response, 'html.parser')
    product_info = {
        "source_url": url,
        'name': None,
        'article': None,
        'cross_num': None,
        'image_urls': [],
        'crosses': []
    }
    try:
        name = soup.find('div', class_='catalog-product__name').text
        name = name.lstrip('\n').strip()
        product_info['name'] = name
    except:
        pass

    try:
        parent_tag = soup.find('div', class_='catalog-product__text').find('div', class_='catalog-product__info')
        if "Артикул" in parent_tag.find('div', class_='catalog-product__group-name').text:
            article = parent_tag.find('div', class_='catalog-product__group-value').text
            article = article.lstrip('\n').strip()
            product_info['article'] = article
    except:
        pass

    try:
        parent_tag = soup.find('div', class_='catalog-product__text').find('div', class_='catalog-product__info')
        groups = parent_tag.find_all('div', class_='catalog-product__group')
        if "Кросс-номер" in groups[-1].find('div', class_= 'catalog-product__group-name').text:
            cross_num = groups[-1].find('div', class_= 'catalog-product__group-value').text
            product_info['cross_num'] = cross_num
    except:
        pass

    try:
        empty = "/assets/uploads/products/no-image/empty.png"
        parent_tag = soup.find('div', id='product-slider')
        a_tag = parent_tag.find('a')
        url = a_tag.get('href')
        if not url == empty:
            url = 'https://tatsumi.ru' + url
            product_info['image_urls'].append(url)
    except:
        pass

    try:
        parents_tag_list = soup.find_all('div', class_="model-table__line")
        for div in parents_tag_list:
            couple_div = div.find_all('div', class_='model-table__item')
            if len(couple_div) == 2:
                cross_brand = couple_div[0].text
                cross_art = couple_div[1].text
                item = {'brand': cross_brand, 'article': cross_art}
                product_info['crosses'].append(item)
    except:
        pass
    return product_info

def main():
    """Главная функция"""

    result = []  # результирующий массив. сюда складывам все ссылки на товары

    ua = UserAgent()  # Экхемппляр классса фейс юзер агент
    headers = {'User-Agent': ua.random,
               "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}  # заголовки
    session = requests.Session()  # Экхемппляр классса  сессии. Главный объект для сетевых запросов
    session.headers.update(headers)  # прокидываем хедерс в объект сессии

    # получаем список категорий. списко категорий содержит пару: имя и ссылка
    root_catalog_url = "https://tatsumi.ru/catalog"
    categories_list = get_categories(root_catalog_url, session)  # возвращает пару: имя и ссылка на категорию

    # итерируемся по списку категорий
    for category_item in categories_list:
        # category_item > {category_name: имя, category_url: ссылка}
        print(f"Текущая категория: {category_item['category_name']}")
        # получаем номер последней страницы для текущей категории
        last_number_page: int or None = get_last_number_page_category(url=category_item['category_url'],
                                                                      session=session)

        # вызываем функцию которая обходит категорию с параментром пагинации и возвращает список всех ссылок на товвары для этой категории

        product_urls = pagination(url=category_item['category_url'], session=session, last_number_page=last_number_page)

        category_obj = {
            'category_name': category_item['category_name'],  # имя категории
            'products': []
        }
        # category_obj > это словарь с двумя ключами. category_name содержит имя категории, а product_urls это
        # список всех ссылок длят этой категории
        for product_url in product_urls:
            product_info = get_product_details(product_url, session)
            category_obj['products'].append(product_info)
        # result.append(category_obj)  # добавляем в результирующий массив
        #
        with open('products.json', 'w', encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)



if __name__ == "__main__":
    main()

    # ua = UserAgent()  # Экхемппляр классса фейс юзер агент
    # headers = {'User-Agent': ua.random,
    #            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}  # заголовки
    # session = requests.Session()  # Экхемппляр классса  сессии. Главный объект для сетевых запросов
    # session.headers.update(headers)
    # 
    # with open('product_urls.json', 'r', encoding='utf-8') as f:
    #     data = json.load(f)
    # 
    # result = []
    # 
    # 
    # for category_item in data:
    #     product_result = []
    #     print(f"Текущая категория: {category_item['category_name']}")
    #     for url in category_item['product_urls']:
    #         print(f"> {url}")
    #         product_details = get_product_details(url, session)
    #         product_result.append(product_details)
    #     item = {'category_name': category_item['category_name'],
    #             'products': product_result}
    #     result.append(item)
    # 
    #     with open('reasult.json', 'w', encoding='utf-8') as f:
    #         json.dump(result, f, ensure_ascii=False, indent=4)


