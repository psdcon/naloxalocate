#!flask/bin/python
###############################################################################
#
# Instructions
#
# Run with the command
# $ python rest-server.py
#
###############################################################################
# Deploying flask resources
# http://flask.pocoo.org/docs/0.11/deploying/mod_wsgi/
# http://www.datasciencebytes.com/bytes/2015/02/24/running-a-flask-app-on-aws-ec2/
# https://www.digitalocean.com/community/tutorials/how-to-deploy-a-flask-application-on-an-ubuntu-vps

from __future__ import print_function  # In python 2.7

import os
import random
import sqlite3
from math import radians, cos, sin, asin, sqrt  # for haversine function
from operator import itemgetter  # sorting

from flask import Flask, jsonify, abort, request, make_response, g, url_for
from flask_restful import reqparse

app = Flask(__name__, static_url_path="")
app.config['DEBUG'] = True

###############################################################################
#
# Helper functions/variables
#
###############################################################################

# Used to parse data from PUT method. Returns error: bad data when incorrectly formatted.
putParser = reqparse.RequestParser()
putParser.add_argument('latitude', type=float, required=True, help='latitude required, type float')
putParser.add_argument('longitude', type=float, required=True, help='longitude required, type float')
putParser.add_argument('accuracy', type=float, required=True, help='accuracy required, type float')
putParser.add_argument('last_updated', type=long, required=True, help='last_updated required, type long')

# Used to parse data from GET method
getParser = reqparse.RequestParser()
getParser.add_argument('latitude', type=float, required=True, help='latitude required, type float')
getParser.add_argument('longitude', type=float, required=True, help='longitude required, type float')


def get_user_if_exists(user_id):
    user = query_db('SELECT `randid`, `latitude`, `longitude`, `accuracy`, `last_updated`, `hit_count` FROM users WHERE randid=?', [user_id])
    if not user:
        abort(404, "User {} doesn't exist".format(user_id))
    else:
        return user


###############################################################################
#
# API Calls
#
###############################################################################

@app.route('/')
def hello_world():
    return '''
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>Nalocatlocate</title>
    <link rel="icon" type="image/png" href="'''+url_for('static', filename='app-icon.png')+'''" />
</head>
<body>
    <h1>Welcome to Naloxalocate.</h1>
    <p>
        Here's a quick and dirty link to see the api output: <br>
        <a href="api/v1.0/users">api/v1.0/users</a>
    </p>
</body>
</html>
    '''


@app.route('/api/v1.0/users', methods=['GET'])
def get_users():
    # if no json in request, Select all users from db and return as json
    if len(request.values) > 0 or request.json:
        # Get the args from the request
        args = getParser.parse_args()
        thisLat = args['latitude']
        thisLong = args['longitude']

        # Get the users that have updated their location in the last hour
        # hourAgo = time.time() - 3600
        # users = query_db('SELECT `randid`, `latitude`, `longitude`, `accuracy`, `last_updated`, `hit_count` FROM users WHERE last_updated>=?', [hourAgo], dict=True)

        # Get only required fields of users that have a last_updated time (which assumes they have coordinates too). Return result as dictionary
        users = query_db('SELECT `randid`, `latitude`, `longitude` FROM users WHERE last_updated > 0', dict=True)

        # Create list of nearby users = [id, distance]
        usersNearby = []
        threshold = 50  # radius in km. IGNORED for demonstration purposes
        for user in users:
            dist = haversine(thisLat, thisLong, user['latitude'], user['longitude'])
            # if dist < threshold:
            usersNearby.append([user['randid'], dist])

        # Sort by ascending distance
        usersNearby = sorted(usersNearby, key=itemgetter(1))
        return jsonify(users=usersNearby)
    else:
        # Return all users in db with all columns except the primary key id. Non-sequential randid is used instead
        return jsonify(users=query_db('SELECT `randid`, `latitude`, `longitude`, `accuracy`, `last_updated`, `hit_count` FROM users'))


@app.route('/api/v1.0/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = get_user_if_exists(user_id)
    return jsonify(user=user)


@app.route('/api/v1.0/users', methods=['POST'])
def create_user():
    # Generate random ids until one that's unique has been found
    user = True
    while user:
        randid = random.randint(1, 999)
        user = query_db('SELECT 1 FROM users WHERE randid=? LIMIT 1', [randid])

    query_db('INSERT INTO users (randid) VALUES (?)', [randid])
    return jsonify(user_id=randid), 201  # CREATED


@app.route('/api/v1.0/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    get_user_if_exists(user_id)
    # Validate request data
    args = putParser.parse_args()
    # Update user
    query_db('UPDATE users SET latitude=?, longitude=?, accuracy=?, last_updated=?, hit_count=hit_count+1 WHERE randid=?',
             [args['latitude'], args['longitude'], args['accuracy'], args['last_updated'], user_id])
    # Get updated user
    user = get_user_if_exists(user_id)
    return jsonify(user=user), 201  # CREATED


@app.route('/api/v1.0/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    get_user_if_exists(user_id)
    query_db('DELETE FROM users WHERE randid=?', [user_id])
    return '', 204  # Indicates success but nothing is in the response body, often used for DELETE and PUT operations


###############################################################################
#
# Error Handlers
#
###############################################################################

@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)


@app.errorhandler(404)
def not_found(error):
    if error.description:
        msg = error.description
    else:
        msg = "Not found"
    return make_response(jsonify({'error': msg}), 404)


###############################################################################
#
# Database
#
###############################################################################
# http://flask.pocoo.org/docs/0.11/patterns/sqlite3/

# DB Structure can be found in schema.sql

DATABASE = os.path.join(app.root_path, 'database.sqlite')


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    """Closes the database again at the end of the request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# Provides cleaner interface to database requests
def query_db(query, args=(), one=False, dict=False, getLastId=False):
    db = get_db()
    if dict:  # Return a dictionary
        db.row_factory = sqlite3.Row
    cur = db.execute(query, args)
    if getLastId:
        rv = cur.lastrowid
    else:
        rv = cur.fetchall()
    db.commit()
    cur.close()
    return (rv[0] if rv else None) if one else rv


###############################################################################
#
# Methods used from test script
#
###############################################################################
# https://github.com/pallets/flask/blob/master/examples/flaskr/flaskr/flaskr.py

def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    init_db()
    print('Initialized the database.')


###############################################################################
#
# Misc
#
###############################################################################

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    km = 6367 * c
    return km


if __name__ == '__main__':
    app.run(debug=True)
