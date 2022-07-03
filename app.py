import json
import os
import traceback
import urllib

import requests
from flask import Flask, redirect, render_template, request, url_for
from flask_bootstrap import Bootstrap4

app = Flask(__name__)
bootstrap = Bootstrap4(app)


BASE_URL = "http://localhost:41595"
LIST_LIMIT = 1000000
PAGE_LIMIT = 20


def call_api(params):
    r = requests.get(BASE_URL + params, {redirect: 'follow'})
    return r.json()


def get_media_paths(id, ext):
    ri = requests.get(BASE_URL + "/api/item/thumbnail?id=" +
                      id, {redirect: 'follow'})
    full_path = urllib.parse.unquote(ri.json()['data'])
    head, tail = os.path.split(full_path)
    last_files = []
    for a in os.listdir(head):
        a = str(a)
        if a == tail or a == "metadata.json":
            continue
        last_files.append(a)
    if len(last_files) == 0:
        last_files.append(tail)
    raw_full_path = os.path.join(head, last_files[-1])
    os.makedirs('static/thumbnails/', exist_ok=True)
    os.makedirs('static/full/', exist_ok=True)
    thumbnail_path = "static/thumbnails/{}.png".format(id)
    raw_path = "static/full/{}.{}".format(id, ext)
    if not os.path.exists(thumbnail_path):
        os.symlink(full_path, thumbnail_path)
        # Path(raw_path).unlink(missing_ok=True)
    if not os.path.exists(raw_path):
        os.symlink(raw_full_path, raw_path)
    return "/" + thumbnail_path, "/" + raw_path


def get_folders_and_name(id=None, parents=[]):
    data = call_api("/api/library/info")
    os.makedirs('static/cache/', exist_ok=True)
    with open("static/cache/folders.json", "w") as f:
        f.write(json.dumps(data['data']))
    if id is None:
        return [{'name': x['name'], 'id': x['id']} for x in data['data']['folders']], None
    else:
        core_data = data['data']['folders']
        for x in parents:
            for s in core_data:
                if s['id'] == x['id']:
                    app.logger.debug(
                        "Core Data Set to{} with name {}".format(s['id'], s['name']))
                    core_data = s['children']
                    break
        final_folders = []
        final_name = None
        actual_parents = {}
        for x in core_data:
            app.logger.debug(
                "Checking {} with name {}".format(x['id'], x['name']))
            if x['children'] != []:
                app.logger.debug("Found children for {}".format(x['id']))
                parents.append({'id': x['id'], 'name': x['name']})
                final_folders, final_name, actual_parents = get_folders_and_name(
                    id, parents)
                if final_name is not None:
                    break
                else:
                    parents.pop()
            if x['id'] == id:
                app.logger.debug("Found id: {}".format(x['name']))
                final_name = x['name']
                final_folders = [{'name': x['name'], 'id': x['id']}
                                 for x in x['children']]
                actual_parents = parents
                break
        app.logger.debug("Final folders: {}".format(final_folders))
        app.logger.debug("Final name: {}".format(final_name))
        return final_folders, final_name, actual_parents


def get_images(include=None, exclude=[]):
    cache_name = "static/cache/root"
    if include is not None:
        cache_name = "static/cache/" + include
    if os.path.exists(cache_name):
        imf = json.loads(open(cache_name+"/meta.json", "r+").read())
        c = int(open(cache_name+"/counter", "r+").read())
        return imf, c

    api_addr = "/api/item/list?limit={}".format(LIST_LIMIT)
    if include is not None:
        api_addr += "&folders={}".format(include)
    data = call_api(api_addr)
    images = []
    c = 0

    for x in data['data']:
        app.logger.debug("Checking Image {}".format(x['id']))
        check = x['ext'] in ('jpg', 'png', 'gif')
        if include is None:
            check = check and x['folders'] == []
        elif exclude != []:
            for e in exclude:
                check = check and e not in x['folders']
        if check:
            images.append(
                {'name': x['name'], 'id': x['id'], 'ext': x['ext'], 'count': c})
            c += 1
    os.makedirs(cache_name, exist_ok=True)
    with open(cache_name+"/meta.json", "w") as f:
        f.write(json.dumps(images))
    with open(cache_name+"/counter", "w") as f:
        f.write(str(c))
    return images, c


def counter_calc(page, len):
    p = int(page)
    total = len
    if len == 0:
        return {'page': 0, 'min': 0, 'max': 0, 'total': 0}
    len = len // PAGE_LIMIT + 1
    if p > len:
        raise Exception("Page does not exist")
    min = (p - 1) * PAGE_LIMIT
    if p == len:
        max = total
    else:
        max = min + PAGE_LIMIT
    return {'page': p, 'min': min, 'max': max, 'total': len}


def generate_pagination_to_html_from_counter(counter, base=""):
    html = ""
    if counter['page'] == 0:
        return html
    if counter['page'] == 1:
        html += "<li class=\"page-item disabled\"><a class=\"page-link\">Previous</a></li>"
    else:
        html += "<li class=\"page-item\"><a class=\"page-link\" href=\"{b}/page/{c}\">Previous</a></li>".format(
            b=base, c=counter['page'] - 1)
    if counter['page'] == 1:
        html += "<li class=\"page-item active\" aria-current=\"page\"><a class=\"page-link\">1</a></li>"
    elif counter['page'] == counter['total']:
        html += "<li class=\"page-item\"><a class=\"page-link\" href=\"{b}/page/{c}\">{c}</a></li>".format(
            b=base, c=counter['total']-2)
    else:
        html += "<li class=\"page-item\"><a class=\"page-link\" href=\"{b}/page/{c}\">{c}</a></li>".format(
            b=base, c=counter['page']-1)
    if counter['total'] >= 2:
        if counter['page'] == 1:
            html += "<li class=\"page-item\"><a class=\"page-link\" href=\"{b}/page/{c}\">{c}</a></li>".format(
                b=base, c=counter['page']+1)
        elif counter['page'] == counter['total'] and counter['total'] > 2:
            html += "<li class=\"page-item\"><a class=\"page-link\" href=\"{b}/page/{c}\">{c}</a></li>".format(
                b=base, c=counter['page']-1)
        else:
            html += "<li class=\"page-item active\" aria-current=\"page\"><a class=\"page-link\" href=\"{b}/page/{c}\">{c}</a></li>".format(
                b=base, c=counter['page'])
        if counter['total'] >= 3:
            if counter['page'] == counter['total']:
                html += "<li class=\"page-item active\" aria-current=\"page\"><a class=\"page-link\" href=\"{b}/page/{c}\">{c}</a></li>".format(
                    b=base, c=counter['page'])
            elif counter['page'] == 1:
                html += "<li class=\"page-item\"><a class=\"page-link\" href=\"{b}/page/{c}\">{c}</a></li>".format(
                    b=base, c=counter['page']+2)
            else:
                html += "<li class=\"page-item\"><a class=\"page-link\" href=\"{b}/page/{c}\">{c}</a></li>".format(
                    b=base, c=counter['page']+1)
    if counter['page'] == counter['total']:
        html += "<li class=\"page-item disabled\"><a class=\"page-link\">Next</a></li>"
    else:
        html += "<li class=\"page-item\"><a class=\"page-link\" href=\"{b}/page/{c}\">Next</a></li>".format(
            b=base, c=counter['page'] + 1)
    return html


@app.route('/resources')
def resources():
    id = request.args.get('id')
    ext = request.args.get('ext')
    tp = request.args.get('type')

    tn, fl = get_media_paths(id, ext)
    if tp == "thumbnail":
        return redirect(tn)
    elif tp == "full":
        return redirect(fl)


@app.route('/folders/<id>/page/<p>', methods=['GET'])
def list_items(id, p):
    try:
        folders, title, actual_parents = get_folders_and_name(id, [])
        print(actual_parents)
        exclude_ids = []
        if folders != []:
            exclude_ids = [x['id'] for x in folders]
        images, len = get_images(id, exclude_ids)
        counter = counter_calc(p, len)
        limited_images = images[counter['min']:counter['max']]
        pagination = generate_pagination_to_html_from_counter(
            counter, "/folders/{}".format(id))
        return render_template('list_items.html', title=title, folders=folders, images=limited_images, counter=counter, pagination=pagination, parents=actual_parents)
    except Exception:
        return render_template('error.html', error=traceback.format_exc())


@app.route('/page/<p>', methods=['GET'])
def list_page(p):
    try:
        folders, _ = get_folders_and_name()
        images, len = get_images()
        counter = counter_calc(p, len)
        limited_images = images[counter['min']:counter['max']]
        pagination = generate_pagination_to_html_from_counter(counter)
        return render_template('list_items.html', folders=folders, images=limited_images, counter=counter, pagination=pagination)
    except Exception:
        return render_template('error.html', error=traceback.format_exc())


@app.route('/', methods=['GET'])
def show_main():
    return redirect(url_for('list_page', p=1))


@app.route('/clear', methods=['GET'])
def clear_cache():
    os.system("rm -rf static/cache")
    os.system("rm -rf static/thumbnails")
    os.system("rm -rf static/full")
    return redirect(url_for('show_main'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4674, debug=True)
