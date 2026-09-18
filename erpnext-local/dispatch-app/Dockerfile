FROM logistics-erpnext:v15
COPY --chown=frappe:frappe . /home/frappe/frappe-bench/apps/dp_dispatch
RUN /home/frappe/frappe-bench/env/bin/pip install --no-deps --no-build-isolation -e /home/frappe/frappe-bench/apps/dp_dispatch
