import base64, zipfile, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from io import BytesIO
from odoo import fields, models, _
from odoo.exceptions import UserError

OFFICIAL_HEADERS = ["N° d'ordre","Prénom(s) et nom","N° carte d'électeur","N.I.N","Date d'expiration CNI"]

def _cell_value(cell, shared):
    ns="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    value=cell.find(ns+"v")
    if value is None: return ""
    raw=value.text or ""
    if cell.attrib.get("t")=="s" and raw.isdigit():
        return shared[int(raw)] if int(raw)<len(shared) else raw
    return raw

def _xlsx_rows(data):
    ns="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    relns="{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    with zipfile.ZipFile(BytesIO(data)) as z:
        shared=[]
        if "xl/sharedStrings.xml" in z.namelist():
            root=ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall(ns+"si"):
                shared.append("".join(t.text or "" for t in si.iter(ns+"t")))
        wb=ET.fromstring(z.read("xl/workbook.xml"))
        rel=ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        relmap={r.attrib["Id"]:r.attrib["Target"] for r in rel}
        sheet=wb.find(ns+"sheets")[0]
        target=relmap[sheet.attrib.get(relns+"id")]
        if not target.startswith("xl/"): target="xl/"+target.lstrip("/")
        root=ET.fromstring(z.read(target))
        return [[_cell_value(c,shared) for c in row.findall(ns+"c")] for row in root.iter(ns+"row")]

def _excel_date(value):
    text=str(value or "").strip()
    for fmt in ("%Y-%m-%d","%d/%m/%Y","%d-%m-%Y","%m/%d/%Y"):
        try: return datetime.strptime(text,fmt).date()
        except ValueError: pass
    try: return (datetime(1899,12,30)+timedelta(days=float(text))).date()
    except Exception: return False

class KiiraayeParrainageImport(models.TransientModel):
    _name="kiiraaye.parrainage.import"
    _description="Import Excel des parrainages"

    election_id=fields.Many2one("kiiraaye.parrainage.election",required=True)
    scope=fields.Selection([("national","National"),("diaspora","Diaspora")],required=True,default="national")
    region_id=fields.Many2one("kiiraaye.geographie",string="Région")
    departement_id=fields.Many2one("kiiraaye.geographie",string="Département")
    commune_id=fields.Many2one("kiiraaye.geographie",string="Commune")
    country_id=fields.Many2one("res.country",string="Pays")
    file=fields.Binary(string="Fichier Excel",required=True)
    filename=fields.Char()

    def action_import(self):
        self.ensure_one()
        if not self.filename or not self.filename.lower().endswith(".xlsx"):
            raise UserError(_("Le fichier doit être un classeur Excel .xlsx."))
        try: rows=_xlsx_rows(base64.b64decode(self.file))
        except Exception as exc: raise UserError(_("Impossible de lire le fichier Excel : %s") % exc)
        if not rows: raise UserError(_("Le fichier Excel est vide."))
        headers=[str(x or "").strip() for x in rows[0][:5]]
        if headers != OFFICIAL_HEADERS:
            raise UserError(_("Schéma Excel non conforme. Colonnes attendues : %s") % " | ".join(OFFICIAL_HEADERS))
        if self.scope=="national" and (not self.region_id or not self.commune_id):
            raise UserError(_("La région et la commune sont obligatoires pour un import national."))
        if self.scope=="diaspora" and not self.country_id:
            raise UserError(_("Le pays est obligatoire pour un import diaspora."))
        vals=[]
        for line_no,row in enumerate(rows[1:],2):
            row=list(row)+[""]*5
            if not any(str(v or "").strip() for v in row): continue
            try: order=int(float(row[0]))
            except Exception: raise UserError(_("Ligne %s : numéro d'ordre invalide.") % line_no)
            name,nin=str(row[1] or "").strip(),str(row[3] or "").strip()
            card=str(row[2] or "").strip()
            if not name or not nin: raise UserError(_("Ligne %s : nom et N.I.N obligatoires.") % line_no)
            if card and len(card)!=9: raise UserError(_("Ligne %s : carte d'électeur = 9 caractères.") % line_no)
            vals.append({"election_id":self.election_id.id,"scope":self.scope,"order_number":order,"full_name":name,"voter_card_number":card,"nin":nin,"cni_expiry_date":_excel_date(row[4]),"country_id":self.country_id.id if self.scope=="diaspora" else False,"region_id":self.region_id.id,"departement_id":self.departement_id.id,"commune_id":self.commune_id.id,"imported":True,"source_file":self.filename})
        try: self.env["kiiraaye.parrainage"].create(vals)
        except Exception as exc: raise UserError(_("Import interrompu : %s") % exc)
        return {"type":"ir.actions.client","tag":"display_notification","params":{"title":_("Import terminé"),"message":_("%s parrainages importés. Renseignez ensuite les dates de naissance pour valider le contrôle des 18 ans.")%len(vals),"type":"success","sticky":False}}
