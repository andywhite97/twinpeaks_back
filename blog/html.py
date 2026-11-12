"""Small, deliberately restricted editorial HTML vocabulary."""
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit


class ArticleHTML(HTMLParser):
    tags = {'p', 'div', 'h2', 'h3', 'strong', 'em', 'b', 'i', 'ul', 'ol', 'li', 'blockquote', 'a', 'br'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.tags:
            return
        attributes = ''
        if tag == 'a':
            href = dict(attrs).get('href', '') or ''
            # Only absolute HTTP(S) links or ordinary site-relative links.
            try:
                parsed = urlsplit(href.strip())
            except ValueError:
                parsed = urlsplit('')
            if not any(ord(c) < 32 for c in href) and '\\' not in href and (
                (parsed.scheme in {'https', 'http'} and parsed.netloc)
                or (href.startswith('/') and not href.startswith('//'))
            ):
                attributes = f' href="{escape(href, quote=True)}" rel="nofollow noopener"'
        self.parts.append(f'<{tag}{attributes}>')
        if tag != 'br':
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            while self.stack:
                current = self.stack.pop()
                self.parts.append(f'</{current}>')
                if current == tag:
                    break

    def handle_data(self, data):
        self.parts.append(escape(data))


def clean_article(value):
    parser = ArticleHTML()
    parser.feed(value or '')
    parser.close()
    return ''.join(parser.parts) + ''.join(f'</{tag}>' for tag in reversed(parser.stack))
