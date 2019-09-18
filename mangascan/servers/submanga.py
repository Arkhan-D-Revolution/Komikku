# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

import dateparser
from bs4 import BeautifulSoup
import cloudscraper
import magic
from requests.exceptions import ConnectionError

from mangascan.servers import Server

server_id = 'submanga'
server_name = 'Submanga'
server_lang = 'es'


class Submanga(Server):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'https://submanga.online'
    search_url = base_url + '/search'
    manga_url = base_url + '/manga/{0}'
    chapter_url = base_url + '/manga/{0}/{1}'
    image_url = base_url + '/uploads/manga/{0}/chapters/{1}/{2}'
    cover_url = base_url + '/uploads/manga/{0}/cover/cover_250x350.jpg'

    def __init__(self):
        if self.session is None:
            self.session = cloudscraper.create_scraper()

    def get_manga_data(self, initial_data):
        """
        Returns manga data by scraping manga HTML page content

        Initial data should contain at least manga's slug (provided by search)
        """
        assert 'slug' in initial_data, 'Manga slug is missing in initial data'

        try:
            r = self.session.get(self.manga_url.format(initial_data['slug']))
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'lxml')

        data = initial_data.copy()
        data.update(dict(
            authors=[],
            scanlators=[],
            genres=[],
            status=None,
            synopsis=None,
            chapters=[],
            server_id=self.id,
            cover=None,
        ))

        data['name'] = soup.find_all('h3')[0].text.strip()
        data['cover'] = self.cover_url.format(data['slug'])

        # Details
        elements = soup.find('div', class_='list-group').find_all('span', class_='list-group-item')
        for element in elements:
            label = element.b.text.strip()

            if label.startswith(('Autor', 'Artist')):
                for a_element in element.find_all('a'):
                    value = a_element.text.strip()
                    if value not in data['authors']:
                        data['authors'].append(value)
            elif label.startswith('Categorías'):
                for a_element in element.find_all('a'):
                    value = a_element.text.strip()
                    if value not in data['authors']:
                        data['genres'].append(value)
            elif label.startswith('Estado'):
                value = element.span.text.strip()
                # possible values: ongoing, complete, None
                data['status'] = element.span.text.strip().lower()
            elif label.startswith('Resumen'):
                element.b.extract()
                data['synopsis'] = element.text.strip()

        # Chapters
        elements = soup.find('div', class_='capitulos-list').find_all('tr')
        for element in reversed(elements):
            td_elements = element.find_all('td')
            a_element = td_elements[0].find('a')
            date_element = td_elements[1]
            date_element.i.extract()
            date_element.span.extract()

            data['chapters'].append(dict(
                slug=a_element.get('href').split('/')[-1],
                title=a_element.text.strip(),
                date=dateparser.parse(date_element.text.strip()).date(),
            ))

        return data

    def get_manga_chapter_data(self, manga_slug, chapter_slug, chapter_url):
        """
        Returns manga chapter data by scraping chapter HTML page content

        Currently, only pages (list of images filenames) are expected.
        """
        url = self.chapter_url.format(manga_slug, chapter_slug)

        try:
            r = self.session.get(url)
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        if r.status_code != 200 or mime_type != 'text/html':
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        pages_imgs = soup.find('div', id='all').find_all('img')

        data = dict(
            pages=[],
        )
        for img in pages_imgs:
            data['pages'].append(dict(
                slug=None,  # not necessary, we know image url directly
                image=img.get('data-src').strip().split('/')[-1],
            ))

        return data

    def get_manga_chapter_page_image(self, manga_slug, manga_name, chapter_slug, page):
        """
        Returns chapter page scan (image) content
        """
        url = self.image_url.format(manga_slug, chapter_slug, page['image'])

        try:
            r = self.session.get(url)
        except ConnectionError:
            return (None, None)

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return (page['image'], r.content) if r.status_code == 200 and mime_type.startswith('image') else (None, None)

    def get_manga_cover_image(self, url):
        """
        Returns manga cover (image) content
        """
        try:
            r = self.session.get(url)
        except ConnectionError:
            return None

        mime_type = magic.from_buffer(r.content[:128], mime=True)

        return r.content if r.status_code == 200 and mime_type.startswith('image') else None

    def get_manga_url(self, slug, url):
        """
        Returns manga absolute URL
        """
        return self.manga_url.format(slug)

    def search(self, term):
        self.session.get(self.base_url)

        try:
            r = self.session.get(self.search_url, params=dict(query=term))
        except ConnectionError:
            return None

        if r.status_code == 200:
            try:
                results = r.json()['suggestions']

                # Returned data for each manga:
                # value: name of the manga
                # data: slug of the manga
                for result in results:
                    result['slug'] = result.pop('data')
                    result['name'] = result.pop('value')

                return results
            except Exception:
                return None
        else:
            return None
