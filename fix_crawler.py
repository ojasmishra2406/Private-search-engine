import os
import re

with open("tests/test_crawler.py", "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace("crawler.session", "httpx.AsyncClient")
c = c.replace("patch.object(httpx.AsyncClient, 'get',", "patch('httpx.AsyncClient.get',")

with open("tests/test_crawler.py", "w", encoding="utf-8") as f:
    f.write(c)
