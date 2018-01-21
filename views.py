import random
import string
from flask import Flask, render_template, request, redirect, url_for, jsonify ,make_response ,flash
from flask import session as login_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from oauth2client.client import flow_from_clientsecrets ,FlowExchangeError
import httplib2,json
from models import Base
from models import Category, Item, User
import requests, os

# google client id
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

engine = create_engine('sqlite:///itemsCatalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__)


@app.context_processor
def override_url_for():
    """
    Generate a new token on every request to prevent the browser from
    caching static files.
    """
    return dict(url_for=dated_url_for)


def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                     endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).first()
    return user


def getUserId(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                  )
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id



#facebook connect
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    #print "access token received %s " % access_token


    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]


    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"
    '''
        Due to the formatting for the result from the server token exchange we have to
        split the token first on commas and select the first index which gives us the key : value
        for the server access token then we split it on colons to pull out the actual token value
        and replace the remaining quotes with nothing so that it can be used directly in the graph
        api calls
    '''
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.8/me?access_token=%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    #url = 'https://graph.facebook.com/v2.8/me/picture?access_token=%s&redirect=0&height=200&width=200' % token
    #h = httplib2.Http()
    #result = h.request(url, 'GET')[1]
    data = json.loads(result)

    #login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserId(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    output = ''

    output += '<h1>Welcome, '
    output += login_session['username']
    ''''
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username']) '''
    return output



@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"

# google connect
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        #print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
   # login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserId(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''

    output += '<h1>Welcome, '
    output += login_session['username']
    '''output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    #print "done!" '''
    return output

@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        #del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('main'))
    else:
        flash("You were not logged in")
        return redirect(url_for('main'))


@app.route('/login')
def showLogin():
    if 'user' in login_session:
        disconnect()
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)

@app.route('/catalog.json')
def catalogjson():
    categories = session.query(Category).all()
    return jsonify(categories=[i.serialize for i in categories])


@app.route('/category/<string:category_name>.json')
def categoryitemsjson(category_name):
    category = session.query(Category).filter_by(name=category_name).first()
    if category is not None:
        items = session.query(Item).filter_by(category_id=category.id).all()
        return jsonify(items=[i.serialize for i in items])
    else:
        return jsonify(error='not Category with that name ')

@app.route(
        '/category/<string:category_name>/item/<string:item_name>.json')
def item(category_name, item_name):
    item = session.query(Item).filter_by(name=item_name ,category_name=category_name).first()
    return jsonify(item=item.serialize)


@app.route('/privacypolicy')
def privacypolicy():
    return render_template('privacypolicy.html')
#main page
@app.route('/')
@app.route('/catalog')
def main():
    categories = session.query(Category).all()
    lastItems = session.query(Item).order_by(Item.id.desc()).limit(10).all()
    if 'username' not in login_session:
        #retuen public tamplete
        return render_template('main.html', categories=categories, lastItems=lastItems)
    else:
        #retuen privete tamplete
        return render_template('mainlogin.html', categories=categories, lastItems=lastItems)


@app.route('/category/new', methods=['POST', 'GET'])
def NewCategory():
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    if request.method == 'POST':
        name = request.form['name']
        if name:
           # check if name in database
            category = session.query(Category).filter_by(name=name).first()
            if category is None:
                category = Category(name=name, user_id=login_session['user_id'])
                session.add(category)
                session.commit()
                return redirect(url_for('main'))
            else:
                return render_template('NewCategory.html', error='the name is already existing')
        else:
            return render_template('NewCategory.html', error='write valid name ')
    else:
        return render_template('NewCategory.html')


@app.route('/category/<string:category_name>/edit', methods=['POST', 'GET'])
def EditCategory(category_name):
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    category = session.query(Category).filter_by(name=category_name).first()
    # if category is existing
    if category is not None:
        # if the user is not  the owner of category
        if category.user_id != login_session['user_id']:
            return render_template('EditCategory.html',
                                   category=category,
                                   notexisting='you are not the owner of the category ')
        if request.method == 'POST':
            name = request.form['name']
            # check if  new name in database
            oldcategory = session.query(Category).filter_by(name=name).first()
            if oldcategory is None or category.name == name:
                category.name = name
                session.add(category)
                session.commit()
                return redirect(url_for('main'))
            else:
                return render_template('EditCategory.html',
                                       category=category,
                                       error='the name is already existing')
        else:
            return render_template('EditCategory.html', category=category)

    else:
        return render_template('EditCategory.html', notexisting='no category with that name ')


@app.route('/category/<string:category_name>/delete', methods=['POST', "GET"])
def deleteCategory(category_name):
    if 'username' not in login_session:
        return redirect(url_for('login'))
    category = session.query(Category).filter_by(name=category_name).first()
    # if the category in database
    if category is not None:
        # if user is the owner of the category
        if category.user_id != login_session['user_id']:
            return render_template('deleteCategory.html',
                                   notexisting='you are not the owner of the category ')
        if request.method == 'POST':
            items = session.query(Item).filter_by(category_id=category.id).all()
            # DELETE all item in the category
            for item in items:
                session.delete(item)
            session.delete(category)
            session.commit()
            return redirect(url_for('main'))
        else:
            return render_template('deleteCategory.html', category=category)
    else:
        return render_template('deleteCategory.html', notexisting='no category with that name ')


@app.route('/category/<string:category_name>/')
@app.route('/category/<string:category_name>/items')
def ShowCategoryItems(category_name):
    category = session.query(Category).filter_by(name=category_name).first()
    categories = session.query(Category).all()

    if category is not None:
        creator =getUserInfo(category.user_id)
        items = session.query(Item).filter_by(category_id=category.id).all()
        if 'username' not in login_session or creator.id != login_session['user_id']:
            #return pubilc template
             return render_template('ShowCategoryItems.html',
                                    items=items, categories=categories,
                                    category=category)
        else:
            #return private template
            return render_template('ShowCategoryItemslogin.html',
                                   items=items, categories=categories,
                                   category=category)
    else:
        return render_template('ShowCategoryItems.html',
                                categories=categories,
                               category=category,
                               notexisting='no category with that name')


@app.route('/category/<string:category_name>/items/new', methods=['POST', 'GET'])
def NewItem(category_name):
    # check login
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    category = session.query(Category).filter_by(name=category_name).first()
    if request.method == 'POST':
        if category is not None:
            if category.user_id != login_session['user_id']:
                return render_template('NewItem.html',
                                       error='you are not the  owner of the category '
                                       , category=category)
            if request.form['name'] and request.form['description']:
                name = request.form['name']
                description = request.form['description']
                item = Item(name=name, description=description, category_id=category.id,
                            user_id=login_session['user_id'])
                session.add(item)
                session.commit()
                return redirect(url_for('ShowCategoryItems', category_name=category.name))
            else:
                return render_template('NewItem.html', empty='write valid name or description'
                                       , category=category)

        else:
            return render_template('NewItem.html',
                                   error='no category with that name %s' % category_name)
    else:
        return render_template('NewItem.html', category=category)


@app.route('/category/<string:category_name>/items/<string:item_name>')
def ShowItem(category_name, item_name):
    category = session.query(Category).filter_by(name=category_name).first()
    if category is not None:
        item = session.query(Item).filter_by(name=item_name, category_id=category.id).first()
        if item is not None:
            if 'username' not in login_session or item.user_id != login_session['user_id']:
                return render_template('ShowItem.html', item=item, category=category
                                       ,notexisting='you are not the owner of th category')
            else:
                return render_template('ShowItemlogin.html', item=item, category=category)
        else:
            return render_template('ShowItem.html',
                                   notexisting='no item with that name %s in that category %s'
                                         % (item_name, category_name))
    else:
        return render_template('ShowItem.html',
                               notexisting='no category with that name %s '
                                     % category_name)


@app.route('/category/<string:category_name>/items/<string:item_name>/edit', methods=['POST', 'GET'])
def EditItem(category_name, item_name):
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    category = session.query(Category).filter_by(name=category_name).first()
    if category is not None:
        # check the owner of the category
        if category.user_id != login_session['user_id']:
            return render_template('EditItem.html',
                                   category=category,
                                   notexisting='you are not the owner of the category')
        item = session.query(Item).filter_by(name=item_name, category_id=category.id).first()
        if item is not None:
            if request.method == 'POST':
                if request.form['name'] and request.form.get('name', '') != item.name:
                    requestName = request.form['name']
                    ifitem = session.query(Item).filter_by(name=requestName,
                                                           category_id=category.id).first()
                    if ifitem is None:
                        item.name = requestName
                    else:
                        return render_template('EditItem.html',
                                               category=category,
                                               item=item,
                                               error='tha name is already existing')
                if request.form['description']:
                    item.description = request.form['description']
                session.add(item)
                session.commit()
                return redirect(url_for('ShowItem',
                                        category_name=category_name,
                                        item_name=item.name))
            else:
                return render_template('EditItem.html', item=item, category=category)
        else:
            return render_template('EditItem.html',
                                   notexisting='no item with that name %s in that category %s'
                                         % (item_name, category_name))
    else:
        return render_template('EditItem.html',
                               notexisting='no category with that name %s '
                                     % category_name)


@app.route('/category/<string:category_name>/items/<string:item_name>/delete', methods=['POST', 'GET'])
def deleteItem(category_name, item_name):
    if 'username' not in login_session:
        return redirect(url_for('showLogin'))
    category = session.query(Category).filter_by(name=category_name).first()
    if category is not None:
        if category.user_id != login_session['user_id']:
            return render_template('deleteItem.html',
                                   error='you are not the owner of the category ')
        item = session.query(Item).filter_by(name=item_name, category_id=category.id).first()
        if item is not None:
            if request.method == 'POST':
                session.delete(item)
                session.commit()
                return redirect(url_for('ShowCategoryItems', category_name=category.name))
            else:
                return render_template('deleteItem.html',
                                       item=item,
                                       category=category)
        else:
            return render_template('deleteItem.html',
                                   error='no item with that name %s in that category %s'
                                         % (item_name, category_name))
    else:
        return render_template('deleteItem.html',
                               error='no category with that name %s '
                                     % category_name)


if __name__ == '__main__':
    app.debug = True
    app.secret_key = 'super_secret_key'
    port = int(os.environ.get('PORT', 8000))   # Use PORT if it's there.
    app.run(host='0.0.0.0', port=port)
