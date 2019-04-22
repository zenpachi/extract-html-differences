import os
import time
import difflib
import base64
import itertools
import threading
import pandas as pd
from urllib import parse
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup as bs

ENV = os.environ
waiting_time = int(ENV['WAITING_TIME']) / 1000

def zero_padding(num, length):
    """
    Zero padding
    :param num:
    :param length:
    :return:
    """
    return f'0000000000{num}'[-length:]


def get_code(url):
    """
    get html code from URL
    :param url: target url
    :return: html
    """
    target = url

    # Basic Auth
    parsed_url = parse.urlparse(url)
    headers = {}
    if parsed_url.username is not None and parsed_url.password is not None:
        target = target.replace(f'{parsed_url.username}:{parsed_url.password}@', '')
        basic_auth = base64.b64encode('{}:{}'.format(parsed_url.username, parsed_url.password).encode('utf-8'))
        headers = {"Authorization": "Basic " + basic_auth.decode('utf-8')}

    try:
        res = urlopen(Request(url=parse.quote(target, safe=':/'), headers=headers))
    except HTTPError as e:
        return 'HTTP Error'
    except URLError as e:
        return 'URL Error'
    except Exception as e:
        return 'Other Error'

    return str(res.read().decode('utf-8'))


def compare_and_generate_result(template, diff_data, url_a, url_b):
    """
    Compare two HTML and generate a result
    :param template: template html
    :param diff_data: page A html
    :param url_a: page A url
    :param url_b: page B url
    :return: page_html
    """
    dd1, dd2 = itertools.tee(diff_data, 2)

    # There is no difference
    if ''.join(dd1) == '':
        return None

    page_html = bs(template, 'html5lib')
    page_content = page_html.find(id='content')

    # append header
    el_head = bs(
        f'''
            <header class="header">
                <a href="./_index.html" class="header__link">← Index</a>
                <div class="header__text">
                    <p>URL A: {url_a}</p>
                    <p>URL B: {url_b}</p>
                </div>
            </header>
            ''',
        'html.parser'
    )
    page_content.append(el_head)

    # write row with difference
    el_diff = bs('', 'html.parser').new_tag('div', attrs={'class': 'diff'})
    el_diff_block = ''
    for diff_row in dd2:
        if diff_row.startswith('---') or diff_row.startswith('+++'):
            continue
        elif diff_row.startswith('@@'):
            if el_diff_block != '':
                el_diff.append(el_diff_block)
                el_diff_block = ''

            el_diff_block = bs('', 'html.parser').new_tag('div', attrs={'class': 'diff__block'})
            el_diff_head = bs('', 'html.parser').new_tag('h2', attrs={'class': 'diff__head'})
            el_diff_head.string = diff_row
            el_diff.append(el_diff_head)
        elif diff_row.startswith('-'):
            el_delete = bs(f'<pre class="row row--delete"><code><math><![CDATA[{diff_row}]]></math></code></pre>',
                           'html.parser')
            el_diff_block.append(el_delete)
        elif diff_row.startswith('+'):
            el_add = bs(f'<pre class="row row--add"><code><math><![CDATA[{diff_row}]]></math></code></pre>',
                        'html.parser')
            el_diff_block.append(el_add)
        else:
            el_other = bs(f'<pre class="row"><code><math><![CDATA[{diff_row}]]></math></code></pre>', 'html.parser')
            el_diff_block.append(el_other)
    else:
        if el_diff_block != '':
            el_diff.append(el_diff_block)

    page_content.append(el_diff)
    return page_html


def generate_index_html(result_index):
    """
    Generate a _index.html
    :param result_index: difference result
    """
    template_index_data = open(f'{os.path.dirname(os.path.abspath(__file__))}/template_index.html', 'r')
    template_index_html = template_index_data.read()
    template_index_data.close()
    index_html = bs(template_index_html, 'html5lib')
    index_table = index_html.find(id='table')

    for result in result_index:
        el_tr = bs('', 'html.parser').new_tag('tr')
        el_index = bs(f'<td>{result["Index"]}</td>', 'html.parser')
        el_tr.append(el_index)
        el_urls = bs(f'''<td>
        <p>URL A: {result["URL A"]}</p>
        <p>URL B: {result["URL B"]}</p>
        </td>''',
                     'html.parser')
        el_tr.append(el_urls)
        if result["Is diff exist"]:
            el_link = bs(f'<td><a href="./{result["File"]}.html">Code</a></td>', 'html.parser')
            el_tr.append(el_link)
            el_note = bs(f'<td></td>', 'html.parser')
            el_tr.append(el_note)
        else:
            el_link = bs(f'<td></td>', 'html.parser')
            el_tr.append(el_link)
            el_note = bs(f'<td>There is no difference</td>', 'html.parser')
            el_tr.append(el_note)
        index_table.append(el_tr)

    f = open(f'{ENV["OUTPUT_PATH"]}/_index.html', 'w')
    f.write(str(index_html.html))
    f.close()


def generate_result_csv(result_index):
    """
    Generate a _result.csv
    :param result_index: difference result
    """
    result_json = pd.io.json.json_normalize(result_index)
    result_df = pd.DataFrame(result_json,
                             columns=['Index',
                                      'URL A',
                                      'URL B',
                                      'File',
                                      'Is diff exist',
                                      'Diff'
                                      ])
    result_df.to_csv(f"{ENV['OUTPUT_PATH']}/_result.csv", encoding="utf_8", index=False)


def scrape_page(result_index, list_index, list_url_a, list_url_b, template_page_html, thread_length, thread_index):
    """
    Scrape pages per thread
    :param result_index:
    :param list_index:
    :param list_url_a:
    :param list_url_b:
    :param thread_length:
    :param thread_index:
    :param template_page_html:
    :return:
    """
    for i, (index, url_a, url_b) in enumerate(zip(list_index, list_url_a, list_url_b)):
        time.sleep(waiting_time)
        file_name = zero_padding(index, 5)
        html_a = get_code(url_a)
        html_b = get_code(url_b)

        # Error
        if html_a in ['HTTP Error', 'URL Error', 'Other Error']:
            print(f'Failure: Page No.{index} is {html_a}', flush=True)
            # Add result data to index
            result_index[thread_index + (i * thread_length)] = {
                'Index': index,
                'URL A': url_a,
                'URL B': url_b,
                'File': '',
                'Is diff exist': html_a,
                'Diff': ''
            }
            continue
        if html_b in ['HTTP Error', 'URL Error', 'Other Error']:
            print(f'Failure: Page No.{index} is {html_b}', flush=True)
            # Add result data to index
            result_index[thread_index + (i * thread_length)] = {
                'Index': index,
                'URL A': url_a,
                'URL B': url_b,
                'File': '',
                'Is diff exist': html_b,
                'Diff': ''
            }
            continue

        diff_data = difflib.unified_diff(html_a.splitlines(), html_b.splitlines(), url_a, url_b, n=2)
        dd1, dd2 = itertools.tee(diff_data, 2)
        result_html = compare_and_generate_result(template_page_html, dd1, url_a, url_b)

        # generate html file
        if result_html is not None:
            f = open(f'{ENV["OUTPUT_PATH"]}/{file_name}.html', 'w')
            f.write(str(result_html.html))
            f.close()

        print(f'Index {index} page is finished.', flush=True)

        # Add result data to index
        result_index[thread_index + (i * thread_length)] = {
            'Index': index,
            'URL A': url_a,
            'URL B': url_b,
            'File': file_name,
            'Is diff exist': result_html is not None,
            'Diff': '\r\n'.join(dd2)
        }


def main():
    input_data = pd.read_csv(ENV['CSV_PATH'], header=None).fillna('')
    input_data = pd.DataFrame(input_data).T.values.tolist()

    list_index = input_data[0]
    list_url_a = input_data[1]
    list_url_b = input_data[2]

    threads_number = int(ENV['THREADS_NUMBER'])
    split_list_index = [list_index[i::threads_number] for i in range(threads_number)]
    split_list_url_a = [list_url_a[i::threads_number] for i in range(threads_number)]
    split_list_url_b = [list_url_b[i::threads_number] for i in range(threads_number)]

    template_page_data = open(f'{os.path.dirname(os.path.abspath(__file__))}/template_page.html', 'r')
    template_page_html = template_page_data.read()
    template_page_data.close()

    result_index = [{
        'Index': '',
        'URL A': '',
        'URL B': '',
        'File': '',
        'Is diff exist': '',
        'Diff': ''
    }] * len(list_index)
    list_thread = [None] * threads_number
    for i in range(threads_number):
        list_thread[i] = threading.Thread(target=scrape_page,
                                          args=(result_index,
                                                split_list_index[i],
                                                split_list_url_a[i],
                                                split_list_url_b[i],
                                                template_page_html,
                                                threads_number,
                                                i))
        list_thread[i].start()

    while True:
        time.sleep(1)
        if all([not t.isAlive() for t in list_thread]):
            break

    generate_index_html(result_index)
    generate_result_csv(result_index)


if __name__ == '__main__':
    main()
