import traceback
from flask import Flask, redirect, render_template
import requests, os, urllib
from flask_bootstrap import Bootstrap4

app = Flask(__name__)
bootstrap = Bootstrap4(app)


BASE_URL = "http://localhost:41595"
LIST_LIMIT = 10000

def call_api(params):
    r = requests.get(BASE_URL + params, {redirect: 'follow'})
    return r.json()

def get_media_paths(id, ext):
    ri = requests.get(BASE_URL + "/api/item/thumbnail?id=" + id, {redirect: 'follow'})
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
    if os.path.exists(thumbnail_path):
        os.unlink(thumbnail_path)
    os.symlink(full_path, thumbnail_path)
    if os.path.exists(raw_path):
        os.unlink(raw_path)
    os.symlink(raw_full_path, raw_path)
    return "/" + thumbnail_path, "/" + raw_path

def get_folders_and_name(id=None, parents=[]):
    data = call_api("/api/library/info")
    if id is None:
        return [{'name': x['name'], 'id': x['id']} for x in data['data']['folders']], None
    else:
        core_data = data['data']['folders']
        for x in parents:
            for s in core_data:
                if s['id'] == x:
                    core_data = s['children']
                    break
        final_folders = []
        final_name = None
        for x in core_data:
            if x['children'] != []:
                parents.append(x['id'])
                final_folders, final_name = get_folders_and_name(id, parents)
                if final_name is not None:
                    break
            if x['id'] == id:
                final_name = x['name']
                final_folders = [{'name': x['name'], 'id': x['id']} for x in x['children']]
                break
            
        return final_folders, final_name
    
def get_images(include=None, exclude=[]):
    api_addr = "/api/item/list?limit={}".format(LIST_LIMIT)
    if include is not None:
        api_addr += "&folders={}".format(include)
    data = call_api(api_addr)
    images = []
    c = 0
    
    for x in data['data']:
        check = x['ext'] in ('jpg', 'png', 'gif') 
        if include is None:
            check = check and x['folders'] == []
        elif exclude != []:
            for e in exclude:
                check = check and e not in x['folders']
        if check:
            thumbnail, full_image = get_media_paths(x['id'], x['ext'])
            images.append({'name': x['name'], 'thumbnail': thumbnail, 'image': full_image, 'count': c})
            c+= 1
    return images

@app.route('/folders/<id>')
def list_items(id):
    try:
        folders, title = get_folders_and_name(id, [])
        exclude_ids = []
        if folders != []:
            exclude_ids = [x['id'] for x in folders]
        images = get_images(id, exclude_ids)
        return render_template('list_items.html', title=title, folders=folders, images=images)
    except Exception:
        return render_template('error.html', error=traceback.format_exc())

@app.route('/', methods=['GET'])
def show_main():
    try:
        folders, _ = get_folders_and_name()
        images = get_images()
        return render_template('list_items.html', folders=folders, images=images)
    except Exception:
        return render_template('error.html', error=traceback.format_exc())


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4674, debug=True)