"""Preserve browser Origin so Frappe can enforce its same-origin check."""
from pathlib import Path

path = Path('/templates/nginx/frappe.conf.template')
source = path.read_text()
old = 'proxy_set_header Origin $proxy_x_forwarded_proto://${FRAPPE_SITE_NAME_HEADER};'
assert old in source, 'Upstream Nginx template changed; review the socket proxy configuration.'
path.write_text(source.replace(old, 'proxy_set_header Origin $http_origin;'))
