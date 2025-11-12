import config

def generate_page_urls():
    links = config.links
    base_url = config.base_url
    for i in range(2, 51):
        links.append(base_url.format(i))
    return links