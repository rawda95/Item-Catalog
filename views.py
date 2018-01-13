from flask import Flask, render_template ,request, redirect ,url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base , Category ,Item ,User

from models import Base

engine = create_engine('sqlite:///itemsCatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__)


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/')
@app.route('/catalog')
def main():
    categories = session.query(Category).all()
    lastItems = session.query(Item).order_by(Item.id.desc()).limit(10).all()
    return render_template('main.html', categories=categories, lastItems=lastItems)


@app.route('/category/new', methods=['POST', 'GET'])
def NewCategory():
    if request.method == 'POST':
        name = request.form['name']
        category = session.query(Category).filter_by(name=name).first()
        if category is None:
            category = Category(name=name)
            session.add(category)
            session.commit()
            return redirect(url_for('main'))
        else:
            return render_template('NewCategory.html', error='the name is already existing')
    else:
        return render_template('NewCategory.html')


@app.route('/category/<string:category_name>/edit', methods=['POST', 'GET'])
def EditCategory(category_name):
    category = session.query(Category).filter_by(name=category_name).first()
    if category is not None:
        if request.method == 'POST':
            name = request.form['name']
            ifcategory = session.query(Category).filter_by(name=name).first()
            if ifcategory is None:
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
    category = session.query(Category).filter_by(name=category_name).first()
    if category is not None:
        if request.method == 'POST':
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
    if category is not None:
        items = session.query(Item).filter_by(category_id=category.id).all()
        return render_template('ShowCategoryItems.html', items=items, category=category)
    else:
        return render_template('ShowCategoryItems.html', notexisting='no category with that name')


@app.route('/category/<string:category_name>/items/new',methods=['POST','GET'])
def NewItem(category_name):
    category = session.query(Category).filter_by(name=category_name).first()
    if request.method == 'POST':
        if category is not None:
            name = request.form['name']
            description = request.form['description']
            item = Item(name=name, description=description,category_id= category.id)
            session.add(item)
            session.commit()
            return redirect(url_for('ShowCategoryItems', category_name=category.name))
        else:
            return render_template('NewItem.html', error='no category with that name %s'%category_name)
    else:
        return render_template('NewItem.html', category=category)


@app.route('/category/<string:category_name>/items/<string:item_name>')
def ShowItem(category_name, item_name):
    category = session.query(Category).filter_by(name=category_name).first()
    if category is not None:
        item = session.query(Item).filter_by(name=item_name, category_id=category.id).first()
        if item is not None:
            return render_template('ShowItem.html', item=item, category=category)
        else:
            return render_template('ShowItem.html',
                                   error='no item with that name %s in that category %s'
                                         % (item_name, category_name))
    else:
            return render_template('ShowItem.html',
                                   error='no category with that name %s '
                                         % category_name)



@app.route('/category/<string:category_name>/items/<string:item_name>/edit',methods=['POST','GET'])
def EditItem(category_name, item_name):
    category = session.query(Category).filter_by(name=category_name).first()
    if category is not None:
        item = session.query(Item).filter_by(name=item_name, category_id=category.id).first()
        if item is not None:
            if request.method == 'POST':
                if request.form['name'] and request.form.get('name','') != item.name :
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
                                   error='no item with that name %s in that category %s'
                                         % (item_name, category_name))
    else:
        return render_template('EditItem.html',
                                   error='no category with that name %s '
                                         % category_name)


@app.route('/category/<string:category_name>/items/<string:item_name>/delete',methods=['POST','GET'])
def deleteItem(category_name, item_name):
    category = session.query(Category).filter_by(name=category_name).first()
    if category is not None:
        item = session.query(Item).filter_by(name=item_name, category_id=category.id).first()
        if item is not None:
            if request.method == 'POST':
                session.delete(item)
                session.commit()
                return redirect(url_for('ShowCategoryItems',category_name =category.name))
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
    app.run(host='0.0.0.0', port=8000)
