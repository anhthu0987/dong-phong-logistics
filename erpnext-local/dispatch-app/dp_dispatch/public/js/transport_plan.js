frappe.ui.form.on('Transport Plan', {
    refresh(frm) {
        const saved=!frm.is_new(), state=frm.doc.status;
        const act=async(method,args={})=>{
            await frappe.call({method:`dp_dispatch.planning.${method}`,args:{name:frm.doc.name,...args},freeze:true});
            await frm.reload_doc();
        };
        if(saved && ['Draft','Failed','Infeasible'].includes(state)) frm.add_custom_button(__('Tính phương án'),async()=>{if(state==='Draft')await frm.save();await act('request_plan');});
        if(saved && state==='Ready') {
            frm.add_custom_button(__('Duyệt và phát hành chuyến'),()=>frappe.confirm(__('Duyệt phương án và phát hành các chuyến?'),()=>act('approve_plan')));
            frm.add_custom_button(__('Từ chối'),()=>frappe.prompt([{fieldname:'note',label:__('Lý do'),fieldtype:'Small Text',reqd:1}],values=>act('reject_plan',values)));
        }
        if(saved && !['Draft','Released'].includes(state))frm.add_custom_button(__('Mở lại để chỉnh / tính lại'),()=>act('reset_plan'));
        ['company','departure','end_time','orders','vehicles'].forEach(f=>frm.set_df_property(f,'read_only',state!=='Draft'));
        frm.set_intro(__('OSRM + OpenStreetMap; thời gian theo tốc độ đường, chưa có giao thông trực tiếp. Tuyến chưa bảo đảm mọi hạn chế riêng cho xe tải; điều phối viên cần kiểm tra trước khi duyệt.'),'blue');
        if(state==='Released') {
            let trips=[];try{trips=JSON.parse(frm.doc.published_trips||'[]');}catch(e){}
            for(const trip of trips)frm.add_custom_button(trip,()=>frappe.set_route('Form','Delivery Trip',trip),__('Chuyến đã phát hành'));
        }
        const esc=frappe.utils.escape_html;
        let result;try{result=JSON.parse(frm.doc.proposal||'null');}catch(e){}
        let html=`<p>${esc(frm.doc.error_message||'')}</p>`;
        if(result?.routes) for(const r of result.routes){
            html+=`<h4>${esc(r.vehicle)} — ${(r.distance_m/1000).toFixed(1)} km</h4><table class="table table-bordered"><thead><tr><th>Đơn</th><th>Điểm</th><th>Đến dự kiến</th><th>Tải sau điểm (kg)</th></tr></thead><tbody>`;
            for(const s of r.stops){
                const arrival=moment(frm.doc.departure).add(s.arrival,'seconds').format('DD/MM/YYYY HH:mm');
                html+=`<tr><td>${esc(s.order)}</td><td>${s.kind==='pickup'?'Lấy hàng':'Giao hàng'}</td><td>${esc(arrival)}</td><td>${s.load/1000}</td></tr>`;
            }
            html+='</tbody></table><p>Về điểm xuất phát: '+esc(moment(frm.doc.departure).add(r.end,'seconds').format('DD/MM/YYYY HH:mm'))+'</p>';
        }
        if (result?.routes?.length) {
            const lines=result.routes.flatMap(r=>(r.segments||[]).map(s=>s.geometry.coordinates));
            const coords=lines.flat();
            if(coords.length) {
                const bounds=coords.reduce((b,[x,y])=>[Math.min(b[0],x),Math.min(b[1],y),Math.max(b[2],x),Math.max(b[3],y)],[Infinity,Infinity,-Infinity,-Infinity]);
                const [x0,y0]=bounds,dx=bounds[2]-x0||.001,dy=bounds[3]-y0||.001;
                html+='<h4>Hình dạng tuyến OSRM (không có nền bản đồ)</h4><svg viewBox="0 0 800 400" style="width:100%;max-height:400px;background:#f8fafc">';
                for(const line of lines)html+=`<polyline fill="none" stroke="#7c3aed" stroke-width="2" points="${line.map(([x,y])=>`${20+(x-x0)/dx*760},${380-(y-y0)/dy*360}`).join(' ')}"/>`;
                html+='</svg>';
            }
        }
        html+='<p>Dữ liệu đường: © OpenStreetMap contributors — ODbL. Routing: OSRM.</p>';
        frm.get_field('proposal_view').$wrapper.html(html);
    },
});
