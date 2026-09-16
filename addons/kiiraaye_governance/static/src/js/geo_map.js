/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const W = 1100, H = 520;

function xy(point) {
    const lon = Number(point[0]), lat = Number(point[1]);
    return [
        ((lon + 180) / 360) * W,
        ((90 - lat) / 180) * H,
    ];
}
function path(ring) {
    if (!ring || !ring.length) return "";
    return ring.map((p,i) => {
        const [x,y]=xy(p);
        return `${i ? "L":"M"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    }).join(" ")+" Z";
}
function paths(geo) {
    if (!geo) return [];
    if (geo.type==="Polygon") return geo.coordinates.map(path);
    if (geo.type==="MultiPolygon") return geo.coordinates.flatMap(p=>p.map(path));
    return [];
}

export class KiiraayeGeoMap extends Component {
    static template="kiiraaye_governance.GeoMap";
    setup(){
        this.orm=useService("orm"); this.action=useService("action");
        this.state=useState({level:"pays",loading:true,items:[]});
        onWillStart(()=>this.load());
    }
    async load(){
        const domain=this.state.level==="all"?[]:[["type_niveau","=",this.state.level]];
        this.state.items=await this.orm.searchRead(
            "kiiraaye.territoire",domain,
            ["name","complete_name","geojson","country_id","type_niveau"],
            {limit:1200,order:"name"}
        );
        this.state.loading=false;
    }
    async change(ev){this.state.level=ev.target.value;this.state.loading=true;await this.load();}
    open(id){this.action.doAction({type:"ir.actions.act_window",res_model:"kiiraaye.territoire",views:[[false,"form"]],res_id:id});}
    paths(item){try{return paths(JSON.parse(item.geojson));}catch{return [];}}
}
registry.category("actions").add("kiiraaye_geo_map",KiiraayeGeoMap);
