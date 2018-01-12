from flask import Flask ,request , url_for , jsonify , render_template ,redirect
from models import Base , Categorie , Item
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


engine = create_engine('sqlite:///itemsCatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


app = Flask(__name__)

@app.route('/login')
def login():
    return 'login '


@app.route('/')
@app.route('/catalog')
def main():

    return 'main page'


@app.route('/category/new', methods=['POST', 'GET'])
def NewCategorie():
    return 'new category'


@app.route('/category/<string:category_name>/edit', methods=['POST', 'GET'])
def EditCategory(category_name):
    return 'edit category id=%s' % category_name


@app.route('/category/<string:category_name>/delete', methods=['POST', "GET"])
def delteCatalog(category_name):
    return 'delete catalog id=%s' % category_name


@app.route('/category/<string:catalog_name>/')
@app.route('/catalog/<string:catalog_name>/items')
def ShowCatalogItem(catalog_name):
    return 'show catalog item  %s' % catalog_name


@app.route('/catalog/<string:catalog_name>/items/new')
def NewItem(catalog_name):
    return 'making new item in catalog %s' % catalog_name

@app.route('/catalog/<string:catalog_name>/items/<string:item_name>')
def ShowItem(catalog_name, item_name):
    return 'show item %s in catalog %s' % item_name, catalog_name

@app.route('/catalog/<string:catalog_name>/items/<string:item_name>/edit')
def EditItem(catalog_name,item_name):
    return 'edit item id =%s in catalog %s'% item_name,catalog_name


@app.route('/catalog/<string:catalog_name>/items/<string:item_namr>/delete')
def deleteItem(catalog_name ,item_name):
    return 'delete item id =%s in catalog %s' %item_name , catalog_name



if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=8000)