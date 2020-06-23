import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash
from datetime import timedelta
import json
import collections

app = Flask(__name__)
app.config.from_object(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(days=0, seconds=1, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0)
# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'db', 'cards.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar('CARDS_SETTINGS', silent=True)


db = sqlite3.connect(app.config['DATABASE'])
# with app.open_resource('data/schema.sql', mode='r') as f:
#     db.cursor().executescript(f.read())
# db.commit()



def connect_db():
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def init_db():
    db = get_db()
    with app.open_resource('data/schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


# -----------------------------------------------------------

# Uncomment and use this to initialize database, then comment it
#   You can rerun it to pave the database and start over
# @app.route('/initdb')
# def initdb():
#     init_db()
#     return 'Initialized the database.'


@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('general'))
    else:
        return redirect(url_for('login'))


@app.route('/cards')
def cards():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    query = '''
        SELECT id, type, front, back, known
        FROM cards
        ORDER BY id DESC
    '''
    cur = db.execute(query)
    cards = cur.fetchall()
    return render_template('cards.html', cards=cards, filter_name="all")


@app.route('/filter_cards/<filter_name>')
def filter_cards(filter_name):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    filters = {
        "all":      "where 1 = 1",
        "general":  "where type = 1",
        "code":     "where type = 2",
        "known":    "where known = 1",
        "unknown":  "where known = 0",
    }

    query = filters.get(filter_name)

    if not query:
        return redirect(url_for('cards'))

    db = get_db()
    fullquery = "SELECT id, type, front, back, known FROM cards " + query + " ORDER BY id DESC"
    cur = db.execute(fullquery)
    cards = cur.fetchall()
    return render_template('cards.html', cards=cards, filter_name=filter_name)


@app.route('/add', methods=['POST'])
def add_card():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    db.execute('INSERT INTO cards (type, front, back) VALUES (?, ?, ?)',
               [request.form['type'],
                request.form['front'],
                request.form['back']
                ])
    db.commit()
    flash('新的抽认卡添加成功.')
    return redirect(url_for('cards'))

@app.route('/ajax_add_card', methods=['POST'])
def ajax_add_card():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    if(request.form['img']!=''):
        db.execute('INSERT INTO cards (type, front, back,img) VALUES (?, ?, ?,?)',
                [request.form['type'],
                    request.form['front'],
                    request.form['back'],
                    request.form['img']
                    ])
        db.commit()
    else:
        db.execute('INSERT INTO cards (type, front, back) VALUES (?, ?, ?)',
                [request.form['type'],
                    request.form['front'],
                    request.form['back']
                    ])
        db.commit()

    return json.dumps(request.form.to_dict());


@app.route('/edit/<card_id>')
def edit(card_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    query = '''
        SELECT id, type, front, back, known
        FROM cards
        WHERE id = ?
    '''
    cur = db.execute(query, [card_id])
    card = cur.fetchone()
    return render_template('edit.html', card=card)


@app.route('/edit_card', methods=['POST'])
def edit_card():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    selected = request.form.getlist('known') 
    known = bool(selected)
    db = get_db()
    if (request.form['img']!=''):
        command = '''
            UPDATE cards
            SET
            type = ?,
            front = ?,
            back = ?,
            known = ?,
            img = ?
            WHERE id = ?
        '''
        db.execute(command,
                [request.form['type'],
                    request.form['front'],
                    'back',
                    known,
                    request.form['img'],
                    request.form['card_id']
                    ])
        db.commit()
    else:
        command = '''
            UPDATE cards
            SET
            type = ?,
            front = ?,
            back = ?,
            known = ?
            WHERE id = ?
        '''
        db.execute(command,
                [request.form['type'],
                    request.form['front'],
                    request.form['back'],
                    known,
                    request.form['card_id']
                    ])
        db.commit()
    # flash('抽认卡保存成功.')
    # message = {'msg':'抽认卡保存成功.'}
    
    message = {
        'msg':'抽认卡删除成功！'
    }
    return json.dumps(message)


@app.route('/delete/<card_id>')
def delete(card_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM cards WHERE id = ?', [card_id])
    db.commit()
    flash('抽认卡删除成功.')
    return redirect(url_for('cards'))


@app.route('/ajax_delete',methods=['POST','GET'])
def ajax_delete():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM cards WHERE id = ?', [request.get_json()['card_id']]) 
    db.commit()
    # flash('抽认卡删除成功.')
    message = {
        'msg':'抽认卡删除成功！'
    }
    return json.dumps(message)

@app.route('/general')
@app.route('/general/<card_id>')
def general(card_id=None):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return memorize("general", card_id)


@app.route('/code')
@app.route('/code/<card_id>')
def code(card_id=None):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return memorize("code", card_id)


def memorize(card_type, card_id):
    if card_type == "general":
        type = 1
    elif card_type == "code":
        type = 2
    else:
        return redirect(url_for('cards'))

    if card_id:
        card = get_card_by_id(card_id)
    else:
        card = get_card(type)
    if not card:
        flash("You've learned all the " + card_type + " cards.")
        return redirect(url_for('cards'))
    short_answer = (len(card['back']) < 75)
    return render_template('memorize.html',
                           card=card,
                           card_type='json_'+card_type,
                           short_answer=short_answer)


@app.route('/json_code')
@app.route('/json_code/<card_id>')
def json_code(card_id=None):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return json_memorize("code", card_id)

@app.route('/json_general')
@app.route('/json_general/<card_id>')
def json_general(card_id=None):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return json_memorize("general", card_id)

def json_memorize(card_type, card_id):
    if card_type == 'general':
        type = 1
    elif card_type == "code":
        type = 2
    else:
        return redirect(url_for('cards'))


    if card_id:
        card = get_card_by_id(card_id)
    else:
        card = get_card(type)
    if not card:
        flash("你已经学完了所有日常卡片张.")
        return redirect(url_for('cards'))
    short_answer = (len(card['back']) < 75)


    d_row = collections.OrderedDict()
    d_row['id'] = card['id']
    d_row['type'] = card['type']
    d_row['front'] = card['front']
    d_row['back'] = card['back']
    d_row['known'] = card['known']
    d_row['img'] = card['img']

    card_json = {
        'card':d_row,
        'card_type':card_type,
        'short_answer':short_answer

    }
    return json.dumps(card_json)

def get_card(type):
    db = get_db()

    query = '''
      SELECT
        id, type, front, back, known, img
      FROM cards
      WHERE
        type = ?
      ORDER BY RANDOM()
      LIMIT 1
    '''

    cur = db.execute(query, [type])
    return cur.fetchone()


def get_card_by_id(card_id):
    db = get_db()

    query = '''
      SELECT
        id, type, front, back, known
      FROM cards
      WHERE
        id = ?
      LIMIT 1
    '''

    cur = db.execute(query, [card_id])
    return cur.fetchone()


@app.route('/mark_known/<card_id>/<card_type>')
def mark_known(card_id, card_type):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    db.execute('UPDATE cards SET known = 1 WHERE id = ?', [card_id])
    db.commit()
    flash('抽认卡被标记为认识.')
    return redirect(url_for(card_type))

@app.route('/ajax_mark_known/<card_id>/<card_type>')
def ajax_mark_known(card_id, card_type):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    db.execute('UPDATE cards SET known = 1 WHERE id = ?', [card_id])
    db.commit()
    # flash('抽认卡被标记为认识.')
    message = {
        'msg':'抽认卡被标记为认识'
    }
    return json.dumps(message)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = '无效用户名或密码！'
        elif request.form['password'] != app.config['PASSWORD']:
            error = '无效用户名或密码!'
        else:
            session['logged_in'] = True
            session.permanent = True  # stay logged in
            return redirect(url_for('cards'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("退出")
    return redirect(url_for('index'))


if __name__ == '__main__':

    app.run(host='0.0.0.0', port=5000)
