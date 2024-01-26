from uvicorn.workers import UvicornWorker

class MyUvicornWorker(UvicornWorker):
    # doing this to try and fix style.css being http rather than https
    # not sure if this was necessary, or fixing the nginx conf
    CONFIG_KWARGS = {"proxy_headers": True, "forwarded_allow_ips": '*'}
