/** @odoo-module **/
import { Component, onWillStart, useState } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
export class KiiraayeTerritoryDashboard extends Component {
 static template='kiiraaye_governance.KiiraayeTerritoryDashboard';
 setup(){this.orm=useService('orm');this.action=useService('action');this.state=useState({loading:true,territory:null,children:[],stats:{}});onWillStart(()=>this.load());}
 async load(){
  const u=await this.orm.searchRead('res.users',[['id','=',this.env.services.user.userId]],['kiiraaye_territoire_id'],{limit:1});
  const id=u?.[0]?.kiiraaye_territoire_id?.[0]; if(!id){this.state.loading=false;return;}
  const [t,s,b,m,a,f,ch]=await Promise.all([
   this.orm.read('kiiraaye.territoire',[id],['name','complete_name','type_niveau','latitude','longitude']),
   this.orm.searchRead('kiiraaye.section',[['territoire_id','child_of',id]],['state'],{limit:5000}),
   this.orm.searchRead('kiiraaye.bureau',[['territoire_id','child_of',id]],['poste_ids'],{limit:5000}),
   this.orm.searchCount('kiiraaye.partisan',[['territoire_id','child_of',id],['active','=',true]]),
   this.orm.searchCount('kiiraaye.activite',[['territoire_id','child_of',id]]),
   this.orm.searchCount('kiiraaye.formation',[['territoire_id','child_of',id]]),
   this.orm.searchRead('kiiraaye.territoire',[['parent_id','=',id]],['name','type_niveau','partisan_count','section_count'],{order:'name'})
  ]);
  const complete=b.filter(x=>(x.poste_ids||[]).length>=5).length;
  this.state.territory=t[0];this.state.children=ch;this.state.stats={m,s:s.length,open:s.filter(x=>x.state==='ouverte').length,b:b.length,complete,a,f};this.state.loading=false;
 }
 go(x){this.action.doAction(x)}
}
registry.category('actions').add('kiiraaye_territory_dashboard',KiiraayeTerritoryDashboard);
