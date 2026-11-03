FROM logistics-erpnext:dispatch-v1

COPY --chown=frappe:frappe . /home/frappe/frappe-bench/apps/dp_operations

RUN /home/frappe/frappe-bench/env/bin/pip install flit_core \
    && /home/frappe/frappe-bench/env/bin/pip install \
        --no-deps --no-build-isolation \
        -e /home/frappe/frappe-bench/apps/dp_operations
    