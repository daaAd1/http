# Asyncy HTTP Gateway

API gateway server for executing Stories via HTTP.

```coffee
when http server listen method: 'get' path: '/' as req
    log info msg: req.body
    log info msg: req.headers
    log info msg: req.headers['Host']
    req write data: 'Hello World'
    req status code: 200
    req finish
```

```sh
curl https://foobar.asyncyapp.com
>>> Hello World
```


## Development

Setup virtual environment and install dependencies
```
virtualenv -p python3.6 venv
source venv/bin/activate
pip install -r requirements.txt
```

Run locally by calling

```
python -m app.main --logging=debug --debug
```

### Register an endpoint

```shell
curl --data '{"endpoint": "http://localhost:9000/story/foo", "data":{"path":"/ping", "method": "post"}}' \ 
     -H "Content-Type: application/json" \ 
     localhost:8889/register
```

Now access that endpoint

```shell
curl -X POST -d 'foobar' http://localhost:8888/world
```


### Unregister an endpoint

```shell
curl --data '{"endpoint": "http://localhost:9000/story/foo", "data":{"path":"/ping", "method": "post"}}' \ 
     -H "Content-Type: application/json" \ 
     localhost:8889/unregister
```