from flask import Flask, render_template, request, send_file
from flask_restful import reqparse, abort, Api, Resource
import sqlite3
import os, re, subprocess

app = Flask(__name__,  template_folder='.')

api = Api(app)

class ApiIndex(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id')
        args = parser.parse_args()
        if args['id'] is None:
            return {"error" : "Send 'id' via GET request or 'url' via POST"}
        task_id = args['id']
        conn = sqlite3.connect('app.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE id = {0}" . format(task_id))
        task = cur.fetchone()
        if task[1] == 0:
            return {"status": "Website is processing right now"}
        else:
            filename = re.findall('[^\/]+$',task[2])[0]
            return {"download_link" : "{0}download/{1}" . format(request.host_url, filename)}
        

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('url')
        args = parser.parse_args()
        if args['url'] is None:
            return {"error" : "Send 'id' via GET request or 'url' via POST"}
            
        conn = sqlite3.connect('app.db')
        cur = conn.cursor()
        cur.execute("INSERT INTO tasks (status, filename) VALUES (0, '')")
        task_id = cur.lastrowid
        conn.commit()
        url = args['url']
        subprocess.Popen(["python", "sp.py", url, str(task_id)])
        return {"task_id" : str(task_id)}

api.add_resource(ApiIndex, '/')


@app.route('/web', methods=['GET', 'POST'])
def index():
    if request.method == "GET":
        if request.args.get('id') is not None:
            task_id = request.args['id']
            conn = sqlite3.connect('app.db')
            cur = conn.cursor()
            cur.execute("SELECT * FROM tasks WHERE id = {0}" . format(task_id))
            task = cur.fetchone()
            if task[1] == 0:
                return 'Website is processing right now'
            else:
                return '<a href="/download/?id={0}">Download archive</a>' . format(task[0])
    
    if request.method == "POST":
        if request.form.get('url') is not None:
            conn = sqlite3.connect('app.db')
            cur = conn.cursor()
            cur.execute("INSERT INTO tasks (status, filename) VALUES (0, '')")
            task_id = cur.lastrowid
            conn.commit()
            url = request.form['url']
            subprocess.Popen(["python", "sp.py", url, str(task_id)])
            return str(task_id)
        
    return render_template('index.html')
    

@app.route('/download/', defaults={'filename': None})
@app.route('/download/<filename>', methods=['GET'])
def dwnload(filename):
    task = None
    if request.method == "GET":
        if request.args.get('id') is not None:
            task_id = request.args['id']
            conn = sqlite3.connect('app.db')
            cur = conn.cursor()
            cur.execute("SELECT * FROM tasks WHERE id = {0}" . format(task_id))
            task = cur.fetchone()
    if task is None:
        if filename is None:
            return "404"
        if os.path.isfile(os.path.dirname(os.path.realpath(__file__)) + '/files/' + filename):
            task = ['','',os.path.dirname(os.path.realpath(__file__)) + '/files/' + filename]
    
    if task is None:
        return "404"
    return send_file(task[2], as_attachment=True, cache_timeout = -1)
    
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8888)