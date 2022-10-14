"""HTML skeleton of predefined zh_hans responses."""

from string import Template
from os import name as osname
from os.path import dirname
from zlib import adler32
from config import STATIC_PATH

htmldir = dirname(__file__)

# Predefined responses
DEFAULT_SCR = (
    '生成的引用将出现在这里...', '', '')

UNDEFINED_INPUT_SCR = (
    '未定义的输入内容。',
    '输入的内容无法识别。',
    '')

HTTPERROR_SCR = (
    'HTTP 错误：',
    '创建引用所需的至少一个网络资源'
    '目前无法访问。',
    '')

OTHER_EXCEPTION_SCR = (
    '发生未知错误。',
    '',
    '')

CSS = open(f'{htmldir}/zh_hans.css', 'rb').read()
CSS_HEADERS = [
    ('Content-Type', 'text/css; charset=UTF-8'),
    ('Content-Length', str(len(CSS))),
    ('Cache-Control', 'immutable, public, max-age=31536000')]

JS = open(f'{htmldir}/zh_hans.js', 'rb').read()
# Invalidate cache after css change.
JS_HEADERS = [
    ('Content-Type', 'application/javascript; charset=UTF-8'),
    ('Content-Length', str(len(JS))),
    ('Cache-Control', 'immutable, public, max-age=31536000')]

# None-zero-padded day directive is os dependant ('%#d' or '%-d')
# See http://stackoverflow.com/questions/904928/
HTML_SUBST = Template(
    open(f'{htmldir}/zh_hans.html', encoding='utf8').read().replace(
        # Invalidate css cache after any change in css file.
        '"stylesheet" href="./static/zh_hans',
        '"stylesheet" href="' + STATIC_PATH + str(adler32(CSS)),
        1,
    ).replace(
        # Invalidate js cache after any change in js file.
        'src="./static/',
        'src="' + STATIC_PATH + str(adler32(JS)),
        1,
    ).replace('{d}', '#d' if osname == 'nt' else '-d')
).substitute


def scr_to_html(sfn_cit_ref: tuple, date_format: str, input_type: str):
    """Insert sfn_cit_ref into the HTML template and return response_body."""
    date_format = date_format or '%Y-%m-%d'
    sfn, cit, ref = sfn_cit_ref
    return HTML_SUBST(
        sfn=sfn, cit=cit, ref=ref,
    ).replace(f'{date_format}"', f'{date_format}" checked', 1).replace(
        f'="{input_type}"', f'="{input_type}" selected', 1)