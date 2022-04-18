from flask import Flask, redirect, render_template
import requests, os, urllib
from flask_bootstrap import Bootstrap5

app = Flask(__name__)
bootstrap = Bootstrap5(app)


BASE_URL = "http://localhost:41595"


def get_thumbnail_path(id):
    if id == "L20GYYPWRJM4O":
        print("here")
    ri = requests.get(BASE_URL + "/api/item/thumbnail?id=" + id, {redirect: 'follow'})
    full_path = urllib.parse.unquote(ri.json()['data'])
    os.makedirs('static/thumbnails/', exist_ok=True)
    thumbnail_path = 'static/thumbnails/' + id + "_thumbnail.png"
    if os.path.exists(thumbnail_path):
        os.remove(thumbnail_path)
    os.symlink(full_path, thumbnail_path)
    return "/" + thumbnail_path

@app.route('/folders/<item>')
def list_items(item):
    r = requests.get(BASE_URL + "/api/item/list?limit=10000&folders=" + item, {redirect: 'follow'})
    data = r.json()
    list = []
    for x in data['data']:
        if x['ext'] in ('jpg', 'png', 'gif'):
            list.append({'name': x['name'], 'thumbnail': get_thumbnail_path(x['id'])})
    
    return render_template('list_items.html', list=list)

@app.route('/clean')
def clear_cache():
    os.rmdir('static/thumbnails/')

@app.route('/', methods=['GET'])
def show_main():
    r = requests.get(BASE_URL + "/api/library/info", {redirect: 'follow'})
    data = r.json()
    nni = [{'name': x['name'], 'id': x['id']} for x in data['data']['folders']]
    return render_template('index.html', list=nni)


if __name__ == '__main__':
    bootstrap.run(host='127.0.0.1', port=4674, debug=True)