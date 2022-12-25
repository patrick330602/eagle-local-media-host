import json
import os
import traceback
import argparse
from pathlib import Path

from flask import Flask, redirect, render_template, url_for
from flask_bootstrap import Bootstrap4

app = Flask(__name__)
bootstrap = Bootstrap4(app)

parser = argparse.ArgumentParser(
                prog = 'edge-local-media-host',
                description = 'A simple local media host for Edge browser',)

parser.add_argument('-p', '--port', type=int, default=4674, help='port to listen on')
parser.add_argument('library_location', type=str, help='location of the library')
parser.add_argument('--page-limit', type=int, default=20, help='number of images per page')

args = parser.parse_args()

PAGE_LIMIT = args.page_limit
BASE_FOLDER = Path(__file__).parent.absolute()

LOCAL_BASE_FOLDER = args.library_location
CACHE_FILE = os.path.join(BASE_FOLDER, "static", "full_definition.json")
LIMIT_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webm']

def cache():
    with open(os.path.join(LOCAL_BASE_FOLDER, "mtime.json"), "r+") as f:
        data = json.loads(f.read())
        data.pop("all")
        l = []
        for i in data:
            t = {}
            print(i)
            head = os.path.join(LOCAL_BASE_FOLDER, "images", i+".info")
            with open(os.path.join(head, "metadata.json"), "r+") as ff:
                x = json.loads(ff.read())
                if x["ext"] not in LIMIT_EXTENSIONS or x["isDeleted"]:
                    continue
                t["id"] = x["id"]
                t["name"] = x["name"]
                t["folders"] = x["folders"]
                lx = []
                full_file = ""
                thumb_file = ""
                for a in os.listdir(head):
                    m = str(a)
                    if m != "metadata.json":
                        lx.append(os.path.join(head, m))
                ll = len(lx)
                if ll == 2:
                    for y in lx:
                        if not y.endswith("_thumbnail.png"):
                            full_file = y
                        else:
                            thumb_file = y
                elif ll == 1:
                    full_file = lx[0]
                    thumb_file = lx[0]
                t['file'] = "images/{}.info/{}".format(i, os.path.basename(full_file))
                t['thumb'] = "images/{}.info/{}".format(i, os.path.basename(thumb_file))
                l.append(t)
        l.reverse()
        with open(CACHE_FILE, "w+") as fx:
            fx.write(json.dumps(l))

def get_folders_and_name(id=None, parents=[]):
    with open(os.path.join(LOCAL_BASE_FOLDER, "metadata.json"), "r+") as f:
        data = json.loads(f.read())
        if id is None:
            return [{'name': x['name'], 'id': x['id']} for x in data['folders']], None
        else:
            core_data = data['folders']
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
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r+") as f:
            data = json.loads(f.read())
            images = []
            c = 0

            for x in data:
                app.logger.debug("Checking Image {}".format(x['id']))
                check = True
                if include is None:
                    check = check and x['folders'] == []
                else:
                    check = check and include in x['folders']
                if exclude != []:
                    for e in exclude:
                        check = check and e not in x['folders']
                if check:
                    images.append(
                        {'name': x['name'], 'id': x['id'], 'file': x['file'], 'thumb': x['thumb'] , 'count': c % PAGE_LIMIT})
                    c += 1
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
    print(counter)
    if counter['page'] == 0:
        return html
    if counter['page'] == 1:
        html += "<li class=\"page-item disabled\"><a class=\"page-link\">Previous</a></li>"
    else:
        html += "<li class=\"page-item\"><a class=\"page-link\" href=\"{b}/page/{c}\">Previous</a></li>".format(
            b=base, c=counter['page'] - 1)
    if counter['page'] == 1:
        html += "<li class=\"page-item active\" aria-current=\"page\"><a class=\"page-link\">1</a></li>"
    elif counter['page'] == counter['total'] and counter['total'] > 2:
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
        return render_template('list_items_full_path.html', title=title, folders=folders, images=limited_images, counter=counter, pagination=pagination, parents=actual_parents)
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
        return render_template('list_items_full_path.html', folders=folders, images=limited_images, counter=counter, pagination=pagination)
    except Exception:
        return render_template('error.html', error=traceback.format_exc())


@app.route('/', methods=['GET'])
def show_main():
    return redirect(url_for('list_page', p=1))

@app.route('/cache', methods=['GET'])
def do_cache():
    if os.path.exists(CACHE_FILE):
        os.system("rm -rf {}".format(CACHE_FILE))
    cache()
    return "complete caching"

@app.route('/link', methods=['GET'])
def link():
    local_source = os.path.join(BASE_FOLDER, "static/files")
    if not os.path.exists(local_source):
        os.symlink(LOCAL_BASE_FOLDER, local_source)
    return "linked"

app.run(host='0.0.0.0', port=args.port, debug=False)
