## aiohttp 版本
3.8.5可以正常运行， 3.9.1提示错误

```bash
Error handling request
Traceback (most recent call last):
  File "/var/www/python-awesome-web/venv/lib/python3.9/site-packages/aiohttp/web_protocol.py", line 452, in _handle_request
    resp = await request_handler(request)
  File "/var/www/python-awesome-web/venv/lib/python3.9/site-packages/aiohttp/web_app.py", line 543, in _handle
    resp = await handler(request)
  File "/var/www/python-awesome-web/venv/lib/python3.9/site-packages/aiohttp/web_middlewares.py", line 114, in impl
    return await handler(request)
  File "/var/www/python-awesome-web/www/app.py", line 47, in inner_logger
    return await handler(request)
  File "/var/www/python-awesome-web/www/app.py", line 77, in auth
    return await handler(request)
  File "/var/www/python-awesome-web/www/app.py", line 85, in response
    r = await handler(request)
  File "/var/www/python-awesome-web/venv/lib/python3.9/site-packages/aiohttp/web_urldispatcher.py", line 201, in handler_wrapper
    assert isinstance(result, StreamResponse)
AssertionError
```