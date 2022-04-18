from flask import Flask, redirect, render_template
import requests, os, urllib
from flask_bootstrap import Bootstrap4

app = Flask(__name__)
bootstrap = Bootstrap4(app)


BASE_URL = "http://localhost:41595"

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

@app.route('/folders/<item>')
def list_items(item):
    data = requests.get(BASE_URL + "/api/library/info", {redirect: 'follow'}).json()
    name = [x['name'] for x in data['data']['folders'] if x['id'] == item][-1]
    r = requests.get(BASE_URL + "/api/item/list?limit=10000&folders=" + item, {redirect: 'follow'})
    data = r.json()
    list = []
    c = 0
    for x in data['data']:
        if x['ext'] in ('jpg', 'png', 'gif'):
            thumbnail, full_image = get_media_paths(x['id'], x['ext'])
            list.append({'name': x['name'], 'thumbnail': thumbnail, 'image': full_image, 'count': c})
            c+= 1
    
    return render_template('list_items.html', title=name, list=list)

@app.route('/', methods=['GET'])
def show_main():
    r = requests.get(BASE_URL + "/api/library/info", {redirect: 'follow'})
    data = r.json()
    nni = [{'name': x['name'], 'id': x['id']} for x in data['data']['folders']]
    return render_template('index.html', list=nni)


if __name__ == '__main__':
    bootstrap.run(host='127.0.0.1', port=4674, debug=True)