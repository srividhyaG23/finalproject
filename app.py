import json
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from flask import (Flask, flash, redirect, render_template, request, session, url_for)
import os
from nutrients import Calculator
import requests
from jinja2 import Template

app = Flask(__name__)
app.secret_key="12345"

con=sqlite3.connect("database.db")
con.execute("create table if not exists customer(pid integer primary key,name text,address text,contact integer,password text)")
con.close()

@app.route('/inde')
def inde():
    return render_template('inde.html')
    return redirect(url_for("inde"))

@app.route('/bas')
def bas():
    return render_template('bas.html')
######################edamam##############

@app.route('/recipes')
def search():
    ingredient = request.args.get('ingredient')

    hits = edamam_search(ingredient)

    with open('./templates/recipes.html') as file_:
        template = Template(file_.read())
    return template.render(ingredient=ingredient, hits=hits)

def edamam_search(query):
    # In e.g. Heroku and Pycharm, environment variables can easily be provided
    # Pass our Edamam credentials in with env variables so they're not in source code (keep them private)
    app_id = '76a6734a'
    app_key = '0ac3717905d2068d76a3492232d77d3a'


    curl = f"https://api.edamam.com/search?q={query}" \
           f"&app_id={app_id}" \
           f"&app_key={app_key}"

    response = requests.get(curl)
    hits = response.json()['hits']

    return hits


# if __name__ == '__main__':
#     app.run()


#################################################################




@app.route('/water')
def water():
    return render_template('water.html')



@app.route('/calorie')
def calorie():
    return render_template('calorie.html') 

@app.route("/")
def discover():
    return render_template('discover.html')



@app.route('/login',methods=["GET","POST"])
def login():
    if request.method=='POST':
        name=request.form['name']
        password=request.form['password']
        con=sqlite3.connect("database.db")
        con.row_factory=sqlite3.Row
        cur=con.cursor()
        cur.execute("select * from customer where name=? and password=?",(name,password))
        data=cur.fetchone()

        if data:
            session["name"]=data["name"]
            session["password"]=data["password"]
            return redirect("customer")
        else:
            flash("Username and Password Mismatch","danger")
    return redirect(url_for("inde"))


@app.route('/customer',methods=["GET","POST"])
def customer():
    return render_template("customer.html")

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        try:
            name=request.form['name']
            address=request.form['address']
            contact=request.form['contact']
            mail=request.form['mail']
            password=request.form['password']
            con=sqlite3.connect("database.db")
            cur=con.cursor()
            cur.execute("insert into customer(name,address,contact,mail,password)values(?,?,?,?,?)",(name,address,contact,mail,password))
            con.commit()
            flash("Record Added  Successfully","success")
        except:
            flash("Error in Insert Operation","danger")
        finally:
            return redirect(url_for("inde"))
            con.close()

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("inde"))


app.config["UPLOAD_FOLDER"] = "static/images"

sizes = {}
nutrients = []
responses = []

with open("foods.json", "r") as f:
    foods = json.load(f)


with open("order.txt", "r") as f:
    order = f.read().splitlines(keepends=False)


for i in foods:
    for j in list(i["nuts"].keys()):
        if j not in nutrients:
            nutrients.append(j)
            sizes[j] = i["nuts"][j]["unit"]
    i["image"] = i["name"].replace(" ", "") + ".jpg"
for i in nutrients:
    if i not in order:
        order.append(i)

nutrients = [i for i in order if i in nutrients]


def response_to_list(r):
    buf = []
    new = {}
    for i in r.keys():
        try:
            new[int(i)] = r[i]
        except ValueError:
            pass
    for i in new.keys():
        while i >= len(buf):
            buf.append(0)
        buf[i] = int(new[i])
    return buf



@app.route("/index")
def index():
    return render_template("index.html", tags=nutrients, sizes=sizes, foods=foods)


@app.route("/data", methods=["POST", "GET"])
def data():
    global responses
    form_data = json.loads(request.form["values"])
    prios = json.loads(request.form["prios"])
    prios = response_to_list(prios)
    to_except = json.loads(request.form["except"])
    if len(responses) > 60:
        responses = []
    key = len(responses)
    nuts = response_to_list(form_data)
    if len(nuts) < 1:
        return "INVALID"

    print("LOAD")
    calc = Calculator()
    calc.load_foods(foods, prios, order)
    print("LOADED")
    res = calc.calculate(nuts, except_foods=to_except)
    if len(res["foods"]) == 0:
        return str(-1)
    responses.append(res)
    query = [(i[0], i[1] - 1) for i in zip(nutrients, nuts) if i[1] != 0]
    responses[key]["query"] = query

    return str(key)


@app.route("/result", methods=["GET"])
def result():
    global responses
    data = request.args
    if int(data["id"]) == -1:
        return render_template("noresult.html")
    try:
        resp = responses[int(data["id"])]
    except (ValueError, IndexError):
        return redirect(url_for("index"))
    foods = resp["foods"]
    for j in foods:
        j["nuts"] = {}
        j["qtty"] = len([i for i in foods if i["id"] == j["id"]]) * 10  # TODO: serving size related
    foods = [i for n, i in enumerate(foods) if i not in foods[n + 1 :]]
    return render_template(
        "result.html",
        nuts=list(zip(nutrients, resp["nutrients"])),
        sizes=sizes,
        foods=foods,
        query=resp["query"],
        time=resp["time"],
        likeness=resp["likeness"],
    )

@app.route("/bmi")
def bmi():
    return render_template('bmi.html')

@app.route("/edamam")
def edamam():
    return render_template('edamam.html')

@app.route("/dietbot")
def dietbot():
    return render_template('dietbot.html')

##############################################################
UPLOAD_FOLDER = 'static/uploads/'
# app = Flask(__name__, static_url_path='/')
# app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#my_secret = os.environ['apikey']
my_secret = "0d68bb24ae8bc3a6f7c3233aa2c625941b516ed7"


def demo_cal(num):
    if int(num)==1:
        data_load = "testdata2burger.json"
    else:
        data_load= "testdata.json"
    with open(data_load, "r") as f:
        data = json.load(f)
    return data

def get_cal(fname):
    try:
        img = f"static/uploads/{fname}"
        api_user_token = my_secret
        headers = {'Authorization': 'Bearer ' + api_user_token}

        # Single/Several Dishes Detection
        url = 'https://api.logmeal.es/v2/recognition/complete'
        resp = requests.post(url,files={'image': open(img, 'rb')},headers=headers)
        print(resp.json())
        #print("response21:\n")
        # Nutritional information
        url = 'https://api.logmeal.es/v2/recipe/nutritionalInfo'
        resp = requests.post(url,json={'imageId': resp.json()['imageId']}, headers=headers)
        print(resp.json()) # display nutritional info
        return resp.json() 
    except:
        return "Error"

@app.route('/logmeal')

def logmeal():
    return render_template("logmeal.html")



@app.route("/api")
def testdata():
    data = demo_cal(1)
    return data

@app.route("/demo/<num>")
def demo(num):
    data = demo_cal(num)
    fname = "damplefood.jpg"
    if int(num)==1:
        fname = "istockphoto-1125149183-612x612.jpg"
    else:
        fname = "depositphotos_50523105-stock-photo-pizza-with-tomatoes.jpg"
    #print(num)
    return render_template("demo.html",fname=fname, data=data)

@app.route('/resultlog', methods = ['GET', 'POST'])
def upload_file():
   if request.method == 'POST':
      f = request.files['file']
      fname = secure_filename(f.filename)
      f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
      data = get_cal(fname)
      if data=="Error":
          return "Service has been exhausted please try after 24hrs!"
      an_object = data["foodName"]
      check_list = isinstance(an_object, list)
      if check_list==True:
          data["foodName"] = data["foodName"][0]
      return render_template("resultlog.html",fname=fname, data=data)
      #return redirect(url_for('static', filename='uploads/' + fname), code=301)

@app.errorhandler(HTTPException)
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    # start with the correct headers and status code from the error
    response = e.get_response()
    # replace the body with JSON
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)