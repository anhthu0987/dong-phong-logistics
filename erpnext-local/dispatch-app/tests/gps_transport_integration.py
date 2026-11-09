"""Run using bench Python from sites/. Business fixtures roll back; Redis is isolated."""
import json
import runpy
import uuid
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.utils import now_datetime, add_to_date


def run():
    from dp_dispatch import completion, tracking
    from dp_dispatch.dp_tracking_and_pod import realtime
    from dp_dispatch.dp_dispatch.api import gps, gps_redis
    acceptance = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'acceptance_transport.py'))
    checks = []
    original_start = completion.start_trip
    original_approve = completion.approve_completion
    original_key = gps_redis._k
    tag = 'integration-' + uuid.uuid4().hex
    key = lambda name: original_key(tag + ':' + name)
    tested = False

    def deny(label, call):
        try:
            call()
        except (frappe.PermissionError, frappe.ValidationError, frappe.DuplicateEntryError):
            checks.append(label)
        else:
            raise AssertionError(label)

    def start(trip):
        nonlocal tested
        result = original_start(trip)
        if tested:
            return result
        tested = True
        actor = frappe.session.user
        doc = frappe.get_doc('Delivery Trip', trip)
        frappe.db.savepoint('gps_checks')
        try:
            # Two trips share one vehicle; GPS must never leak across them.
            foreign = frappe.get_doc(dict(doctype='Delivery Trip', name=tag+'-foreign', vehicle=doc.vehicle,
                driver=None, docstatus=1, status='In Transit', departure_time=now_datetime()))
            foreign.db_insert()
            draft = frappe.get_doc(dict(doctype='Delivery Trip', name=tag+'-draft', vehicle=doc.vehicle,
                driver=doc.driver, docstatus=0, status='Draft', departure_time=add_to_date(now_datetime(),days=1)))
            draft.db_insert()
            def send(target, event, minute=0, lat=10.8):
                frappe.local.form_dict=frappe._dict(vehicle=doc.vehicle, delivery_trip=target,
                    recorded_at=str(add_to_date(now_datetime(),minutes=minute)), latitude=lat,longitude=106.6,
                    source_event_id=tag+event,source_type='Simulated')
                return gps.log_location()
            with patch.object(gps_redis,'_k',key):
                frappe.set_user('Administrator')
                frappe.db.set_value('Delivery Trip',foreign.name,'status','Scheduled')
                with patch.object(gps_redis,'enqueue',return_value='queued') as queued:
                    send(None,'-inferred')
                    assert queued.call_args.args[0]['delivery_trip']==trip
                    send(None,'-old-unassigned',minute=-60)
                    assert queued.call_args.args[0]['delivery_trip'] is None
                frappe.db.set_value('Delivery Trip',foreign.name,'status','In Transit')
                deny('Ambiguous active vehicle trips rejected',lambda:send(None,'-ambiguous'))
                checks.append('Vehicle-only GPS binds current trip but not pre-trip delayed positions')
                manager=frappe.get_doc(dict(doctype='User',email=tag+'@example.invalid',first_name='Điều phối vận tải',enabled=1,send_welcome_email=0,user_type='System User',roles=[{'role':'Fleet Manager'}])).insert()
                assert realtime.can_watch(doc,manager.name)
                assert not frappe.has_permission('Delivery Trip',doc=doc,user=actor,ptype='write')
                checks.append('Frappe v16 manager read and driver write restrictions enforced')
                frappe.set_user(actor)
                realtime.watch_trip(trip)
                deny('Foreign trip realtime subscription denied',lambda:realtime.watch_trip(foreign.name))
                with patch.object(frappe,'publish_realtime') as publish:
                    send(trip,'-a')
                    assert publish.call_count == 1
                    assert publish.call_args.kwargs == {'user':actor,'after_commit':True}
                    assert publish.call_args.args[0] == 'dp_gps_position'
                    assert publish.call_args.args[1]['delivery_trip'] == trip
                checks.append('Realtime position targets only authenticated current trip watcher')
                same=dict(frappe.local.form_dict)
                with patch.object(frappe,'publish_realtime') as publish:
                    assert gps.log_location()['status']=='ignored'
                    publish.assert_not_called()
                frappe.local.form_dict.recorded_at=str(add_to_date(now_datetime(),minutes=-1))
                deny('Conflicting event id cannot change timestamp',gps.log_location)
                deny('Unknown GPS source rejected',lambda:(frappe.local.form_dict.update(source_type='Invalid'),gps.log_location()))
                checks.append('GPS ingest and duplicate idempotency')
                with patch.object(frappe,'publish_realtime') as publish:
                    send(trip,'-older',minute=-5,lat=10.7)
                    publish.assert_not_called()
                checks.append('Duplicate and delayed points do not push a stale position')
                assert gps_redis.latest_for_trip(trip,doc.vehicle)['latitude']==10.8
                deny('Driver cannot send GPS to another trip',lambda:send(foreign.name,'-bad'))
                deny('Driver cannot send GPS to draft trip',lambda:send(draft.name,'-draft'))
                deny('Legacy GPS stop endpoint cannot complete trip',lambda:gps.complete_delivery_stop(doc.delivery_stops[0].name))
                assert frappe.db.get_value('Delivery Trip',trip,'status')=='In Transit'
                frappe.set_user('Administrator')
                send(foreign.name,'-foreign',lat=11.1)
                with patch.object(frappe.db,'commit',lambda:None):
                    assert gps_redis.flush()==3
                # Durable deduplication still rejects conflicting replays after Redis TTL.
                gps_redis._r().delete(key('evt:'+tag+'-a'))
                frappe.local.form_dict=frappe._dict(same)
                assert gps.log_location()['status']=='ignored'
                frappe.local.form_dict.latitude=9
                deny('Persisted GPS event prevents conflicting replay',gps.log_location)
                frappe.set_user(actor)
                rows=gps.get_gps_history(delivery_trip=trip)
                assert len(rows)==2 and rows[-1].latitude==10.8
                assert len(gps.get_gps_history(delivery_trip=trip,limit=1))==1
                assert gps.get_gps_history(delivery_trip=trip,limit=1)[0].latitude==10.8
                deny('Foreign trip history denied',lambda:gps.get_gps_history(delivery_trip=foreign.name))
                deny('Foreign trip map denied',lambda:tracking.get_trip_tracking(foreign.name))
                deny('Draft trip map denied',lambda:tracking.get_trip_tracking(draft.name))
                live=gps_redis.get_live_positions(delivery_trip=trip)
                assert len(live)==1 and live[0]['lat']==10.8
                assert all(p['delivery_trip']!=foreign.name for p in gps_redis.get_live_positions())
                checks.append('Live GPS remains scoped to assigned trip even with same vehicle')
                schedule=gps.get_driver_schedule()
                assert schedule['trip']['name']==trip
                assert [s['operation'] for s in schedule['stops']]==['Pickup','Delivery']
                assert all(t.name!=draft.name for t in schedule['trips'])
                checks.append('Driver schedule selects running submitted trip and retains pickup-delivery order')
                logs=frappe.get_list('GPS Log',fields=['name','delivery_trip'],limit_page_length=1000)
                assert all(p.delivery_trip!=foreign.name for p in logs)
                foreign_log=frappe.get_all('GPS Log',filters={'delivery_trip':foreign.name},pluck='name')[0]
                deny('Direct GPS document read denied across drivers',lambda:frappe.get_doc('GPS Log',foreign_log).check_permission('read'))
                checks.append('REST/list GPS permissions scoped by trip')
                # Redis expiry/restart fallback still reads only this trip's DB history.
                gps_redis._r().delete(key('trip:'+trip))
                assert gps_redis.latest_for_trip(trip,doc.vehicle).latitude==10.8
                frappe.set_user('Administrator')
                send(trip,'-late',minute=-20,lat=10.1)
                with patch.object(frappe.db,'commit',lambda:None): gps_redis.flush()
                assert frappe.db.get_value('Vehicle',doc.vehicle,'custom_last_lat')==11.1
                assert gps_redis.latest_for_trip(trip,doc.vehicle)['latitude']==10.8
                checks.append('Delayed GPS cannot rewind persisted vehicle position')
                # An old socket/user room must not keep access after reassignment.
                with patch.object(realtime,'can_watch',return_value=False), patch.object(frappe,'publish_realtime') as publish:
                    send(trip,'-revoked',minute=1)
                    publish.assert_not_called()
                assert not gps_redis._r().zscore(key('watch:'+trip),actor)
                frappe.set_user(actor)
                realtime.watch_trip(trip)
                gps_redis._r().zadd(key('watch:'+trip),{actor:0})
                with patch.object(frappe,'publish_realtime') as publish:
                    send(trip,'-expired',minute=2)
                    publish.assert_not_called()
                checks.append('Revoked and expired watches receive no GPS push')
                frappe.set_user('Guest')
                deny('Guest tracking denied',lambda:tracking.list_trips())
                deny('Guest realtime subscription denied',lambda:realtime.watch_trip(trip))
                deny('Guest live positions denied',lambda:gps_redis.get_live_positions())
        finally:
            frappe.set_user(actor)
            frappe.db.rollback(save_point='gps_checks')
            redis=gps_redis._r()
            keys=list(redis.scan_iter(match=key('*')))
            if keys: redis.delete(*keys)
            frappe.clear_messages()
        return result

    def approve(trip, note=None):
        result=original_approve(trip,note)
        doc=frappe.get_doc('Delivery Trip',trip)
        assert doc.status=='Completed' and doc.custom_completion_status=='Approved'
        frappe.local.form_dict=frappe._dict(vehicle=doc.vehicle,delivery_trip=trip,recorded_at=str(now_datetime()),
            latitude=10.8,longitude=106.6,source_event_id=tag+'-closed',source_type='Simulated')
        deny('Completed trip rejects further trip GPS',gps.log_location)
        deny('Legacy stop API cannot mutate completed trip',lambda:gps.complete_delivery_stop(doc.delivery_stops[0].name))
        assert not any(t.name==trip for t in tracking.list_trips(active_only=1))
        return result

    with patch.object(completion,'start_trip',start), patch.object(completion,'approve_completion',approve):
        report=acceptance['run']()
    assert tested and report['retained'] is False
    return {'gps_checks':checks,'transport_checks':report['checks'],'retained':False}


if __name__=='__main__':
    frappe.init(site='logistics-v16.localhost',sites_path='/home/frappe/frappe-bench/sites')
    frappe.connect()
    try:
        print(json.dumps(run(),ensure_ascii=False))
    finally:
        frappe.db.rollback()
        frappe.destroy()
