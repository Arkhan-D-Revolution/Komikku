from komikku.servers.ninemanga import Ninemanga

server_id = 'ninemanga_it'
server_name = 'Nine Manga'
server_lang = 'it'


class Ninemanga_it(Ninemanga):
    id = server_id
    name = server_name
    lang = server_lang

    base_url = 'http://it.ninemanga.com'
    search_url = base_url + '/search/ajax/'
    manga_url = base_url + '/manga/{0}.html'
    chapter_url = base_url + '/chapter/{0}/{1}'
    page_url = chapter_url
    cover_url = 'https://na3.taadd.com{0}'