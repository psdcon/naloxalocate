import json
import os
import re
import rest_server
import tempfile
import unittest


# Based on https://github.com/pallets/flask/blob/master/examples/flaskr/tests/test_flaskr.py

class FlaskrTestCase(unittest.TestCase):
    def setUp(self):
        # Create a new temp database every test with a random temporary name
        self.db_fd, rest_server.app.DATABASE = tempfile.mkstemp()
        rest_server.app.config['TESTING'] = True
        rest_server.app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
        self.app = rest_server.app.test_client()
        with rest_server.app.app_context():
            rest_server.init_db()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(rest_server.app.DATABASE)

    #
    # Tests
    #

    # test basic api functions such as post, get multiple users, delete
    def test_post_get_delete_users(self):
        # Create user 1
        rv = self.app.post('/api/v1.0/users')
        user1 = parseInt(rv.data)
        assert '{"user_id":' + user1 + '}' in rv.data

        # Create user 2
        rv = self.app.post('/api/v1.0/users')
        user2 = parseInt(rv.data)
        assert '{"user_id":' + user2 + '}' in rv.data

        # Get all users
        rv = self.app.get('/api/v1.0/users')
        assert '{"users":[[' + user1 + ',0.0,0.0,0.0,0,0],[' + user2 + ',0.0,0.0,0.0,0,0]]}' in rv.data

        # Get user 2 only
        rv = self.app.get('/api/v1.0/users/' + user2)
        assert '{"user":[[' + user2 + ',0.0,0.0,0.0,0,0]]}' in rv.data

        # Delete non existing user
        rv = self.app.delete('/api/v1.0/users/0')
        assert '{"error":"User 0 doesn\'t exist"}' in rv.data

        # Delete user 2
        rv = self.app.delete('/api/v1.0/users/' + user2)
        assert '' in rv.data

        # Get all users. Only user 1 should be left
        rv = self.app.get('/api/v1.0/users')
        assert '{"users":[[' + user1 + ',0.0,0.0,0.0,0,0]]}' in rv.data

        # Delete user 1
        rv = self.app.delete('/api/v1.0/users/' + user1)
        assert '' in rv.data

        # Get all users. Result should be empty
        rv = self.app.get('/api/v1.0/users')
        assert '{"users":[]}' in rv.data

    #   test that empty database returns empty json array, as expected by the app client
    def test_empty_database(self):
        rv = self.app.get('/api/v1.0/users')
        assert '{"users":[]}' in rv.data

    #   test that an error message is returned if a non valid ID is entered
    def test_get_NonValidID(self):
        # Create a user
        rv = self.app.post('/api/v1.0/users')
        user1 = parseInt(rv.data)

        # Get data with no user_id specific i.e. 'users/__'
        rv = self.app.get('/api/v1.0/users/')
        assert '{"error":"The requested URL was not found on the server.  If you entered the URL manually please check your spelling and try again."}' in rv.data

        # Get data of user that doesn't exist
        rv = self.app.get('/api/v1.0/users/0')
        assert '{"error":"User 0 doesn\'t exist"}' in rv.data


        #  test that error message is returned if required fields have invalid data

    def test_null_values(self):
        # Create a user
        rv = self.app.post('/api/v1.0/users')
        user1 = parseInt(rv.data)

        # Put latitude as 'null'
        data = {"latitude": 'null', "longitude": -6.219635, "accuracy": 443.3, "last_updated": 1482429033525}
        rv = self.app.put('/api/v1.0/users/' + user1, data=json.dumps(data), content_type='application/json')
        assert '{"error":"Bad request"}' in rv.data

        # Put longitude as 'null'
        data = {"latitude": 53.302543, "longitude": 'null', "accuracy": 443.3, "last_updated": 1482429033525}
        rv = self.app.put('/api/v1.0/users/' + user1, data=json.dumps(data), content_type='application/json')
        assert '{"error":"Bad request"}' in rv.data

        # Put accuracy as 'null'
        data = {"latitude": 53.302543, "longitude": -6.219635, "accuracy": 'null', "last_updated": 1482429033525}
        rv = self.app.put('/api/v1.0/users/' + user1, data=json.dumps(data), content_type='application/json')
        assert '{"error":"Bad request"}' in rv.data

        # Put last update as 'null'
        data = {"latitude": 53.302543, "longitude": -6.219635, "accuracy": 443.3, "last_updated": 'null'}
        rv = self.app.put('/api/v1.0/users/' + user1, data=json.dumps(data), content_type='application/json')
        assert '{"error":"Bad request"}' in rv.data

    #   test that the hit_count increases after each successful PUT
    def test_hit_count(self):
        # Create user 1
        rv = self.app.post('/api/v1.0/users')
        user1 = parseInt(rv.data)

        # Put data 1st time & Check Hit_Count increased
        data = {"latitude": 53.302543, "longitude": -6.219635, "accuracy": 400.0, "last_updated": 1482429033525}
        rv = self.app.put('/api/v1.0/users/' + user1, data=json.dumps(data), content_type='application/json')
        assert '{"user":[[' + user1 + ',53.302543,-6.219635,400.0,1482429033525,1]]}' in rv.data

        # Put data 2nd time & Check Hit_Count increased again
        data = {"latitude": 53.302543, "longitude": -6.219635, "accuracy": 500.0, "last_updated": 1482429033550}
        rv = self.app.put('/api/v1.0/users/' + user1, data=json.dumps(data), content_type='application/json')
        assert '{"user":[[' + user1 + ',53.302543,-6.219635,500.0,1482429033550,2]]}' in rv.data

        # Put fails
        data = {"latitude": 'null', "longitude": -6.219635, "accuracy": 500.0, "last_updated": 1482429033550}
        rv = self.app.put('/api/v1.0/users/' + user1, data=json.dumps(data), content_type='application/json')
        assert '{"error":"Bad request"}' in rv.data

        # Put data 3rd time & Check Hit_Count increased again to 3 and not 4
        data = {"latitude": 53.302543, "longitude": -6.219635, "accuracy": 400.0, "last_updated": 1482429033570}
        rv = self.app.put('/api/v1.0/users/' + user1, data=json.dumps(data), content_type='application/json')
        assert '{"user":[[' + user1 + ',53.302543,-6.219635,400.0,1482429033570,3]]}' in rv.data

    # test what happens when different data types are given for each member variable
    def test_data_type(self):
        # Create a user
        rv = self.app.post('/api/v1.0/users')
        user1 = parseInt(rv.data)

        # Put latitude as integer
        data = {"latitude": 53, "longitude": -6.219635, "accuracy": 443.3, "last_updated": 1482429033525}
        rv = self.app.put('/api/v1.0/users/' + user1, data=json.dumps(data), content_type='application/json')
        assert '{"user":[[' + user1 + ',53.0,-6.219635,443.3,1482429033525,1]]}' in rv.data

        # Put latitude as string
        data = {"latitude": "TEST", "longitude": -6.219635, "accuracy": 443.3, "last_updated": 1482429033525}
        rv = self.app.put('/api/v1.0/users/' + user1, data=json.dumps(data), content_type='application/json')
        assert '{"error":"Bad request"}' in rv.data

        # Put longitude as string
        data = {"latitude": 53.302543, "longitude": "TEST", "accuracy": 443.3, "last_updated": 1482429033525}
        rv = self.app.put('/api/v1.0/users/' + user1, data=json.dumps(data), content_type='application/json')
        assert '{"error":"Bad request"}' in rv.data

        # Put accuracy as string
        data = {"latitude": 53.302543, "longitude": -6.219635, "accuracy": "TEST", "last_updated": 1482429033525}
        rv = self.app.put('/api/v1.0/users/' + user1, data=json.dumps(data), content_type='application/json')
        assert '{"error":"Bad request"}' in rv.data

        # Put last_updated as string
        data = {"latitude": 53.302543, "longitude": -6.219635, "accuracy": 443.3, "last_updated": "TEST"}
        rv = self.app.put('/api/v1.0/users/' + user1, data=json.dumps(data), content_type='application/json')
        assert '{"error":"Bad request"}' in rv.data

        # Put latitude as Numbered string
        data = {"latitude": "53.302543", "longitude": -6.219635, "accuracy": 443.3, "last_updated": 1482429033525}
        rv = self.app.put('/api/v1.0/users/' + user1, data=json.dumps(data), content_type='application/json')
        assert '{"user":[[' + user1 + ',53.302543,-6.219635,443.3,1482429033525,2]]}' in rv.data

    # Test that nearby users are returned as expected
    def test_get_with_location(self):
        # Create a user
        rv = self.app.post('/api/v1.0/users')
        user1 = parseInt(rv.data)
        rv = self.app.get('/api/v1.0/users?latitude=53.302543&longitude=-6.219635')
        assert '{"users":[]}' in rv.data  # no one in db with coordinates yet

        # Give user some data
        data = {"latitude": 53.302543, "longitude": -6.219635, "accuracy": 443.3, "last_updated": 1482429033525}
        self.app.put('/api/v1.0/users/' + user1, data=json.dumps(data), content_type='application/json')

        # Test if nearby user shows up
        rv = self.app.get('/api/v1.0/users?latitude=53.302543&longitude=-6.219635')
        assert '{"users":[[' + user1 + ',0.0]]}' in rv.data  # coordinates are the same


def parseInt(str):
    ints = re.findall(r'\d+', str)
    return ints[0]


if __name__ == '__main__':
    unittest.main()
