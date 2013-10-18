# Reloader

> Reloader can accelerate web development by automatically refreshing your pages (in multiple browsers) when a file is locally modified. If a css file is modified, only stylsheets are reloaded.

### Deps:

``` sh
$ pip install twisted
$ pip install pyinotify
```

- the rest should already be installed

### Usage:

Start the server

``` sh
$ python reloader.py --path /var/www/projectdir/ --strict
```
Add this tag to your html:

``` html
<script type="text/javascript" src="http://127.0.0.1:8181/js"></script>
```

### Tested Browsers:

* firefox 4
* chrome 11
* internet explorer 7
* safari 3
* opera 11

### Note:

I wrote this several years ago and better alternatives now exist.
