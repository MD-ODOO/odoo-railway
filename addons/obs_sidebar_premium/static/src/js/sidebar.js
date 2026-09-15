/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

function lsGet(k, d) { try { const v = localStorage.getItem(k); return v !== null ? JSON.parse(v) : d; } catch { return d; } }
function lsSet(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} }

function darker(hex, p) {
    const n = parseInt(hex.replace("#",""), 16);
    const r = Math.max(0, (n>>16) - Math.round((n>>16)*p));
    const g = Math.max(0, ((n>>8)&255) - Math.round(((n>>8)&255)*p));
    const b = Math.max(0, (n&255) - Math.round((n&255)*p));
    return "#" + ((r<<16)|(g<<8)|b).toString(16).padStart(6,"0");
}
function lighter(hex) {
    const n = parseInt(hex.replace("#",""), 16);
    const r = Math.min(255, (n>>16) + Math.round((255-(n>>16))*.85));
    const g = Math.min(255, ((n>>8)&255) + Math.round((255-((n>>8)&255))*.85));
    const b = Math.min(255, (n&255) + Math.round((255-(n&255))*.85));
    return "#" + ((r<<16)|(g<<8)|b).toString(16).padStart(6,"0");
}

const K = { bookmarks:"sp_bookmarks", recent:"sp_recent", notes:"sp_notes", font:"sp_font", color:"sp_color", tab:"sp_tab" };

class SidebarPremium extends Component {
    static template = "obs_sidebar_premium.Panel";
    static props = {};

    tabs = [
        { id:"display",   label:"Display",   icon:"fa fa-desktop" },
        { id:"tools",     label:"Tools",     icon:"fa fa-wrench" },
        { id:"bookmarks", label:"Saved",     icon:"fa fa-bookmark" },
        { id:"notes",     label:"Notes",     icon:"fa fa-pencil" },
    ];

    colorPresets = [
        { name:"Teal",        color:"#00897B" },
        { name:"Indigo",      color:"#3949AB" },
        { name:"Purple",      color:"#7B1FA2" },
        { name:"Rose",        color:"#C2185B" },
        { name:"Orange",      color:"#E65100" },
        { name:"Blue",        color:"#1565C0" },
        { name:"Green",       color:"#2E7D32" },
        { name:"Cyan",        color:"#00838F" },
        { name:"Brown",       color:"#4E342E" },
        { name:"Slate",       color:"#37474F" },
        { name:"Amber",       color:"#FF6F00" },
        { name:"Deep Purple", color:"#4527A0" },
    ];

    setup() {
        this.action = useService("action");
        const savedColor = lsGet(K.color, "#00897B");

        this.state = useState({
            open:          false,
            activeTab:     lsGet(K.tab, "display"),
            fullscreen:    !!document.fullscreenElement,
            navbarHidden:  false,
            compactMode:   false,
            fontSize:      lsGet(K.font, 100),
            activeColor:   savedColor,
            clockTime:     "", clockDate: "", clockTz: "",
            calcDisplay:   "0", calcExpr: "",
            calcPrev:      null, calcOp_: null, calcReset: false,
            sessionUser:   "",
            bookmarks:     lsGet(K.bookmarks, []),
            recent:        lsGet(K.recent, []),
            notes:         lsGet(K.notes, ""),
            newBmName:     "",
        });

        onMounted(() => {
            this._applyFont(this.state.fontSize);
            this._applyColor(savedColor);
            this._loadSession();
            this._startClock();
            this._trackNav();
            this._onFsChange = () => { this.state.fullscreen = !!document.fullscreenElement; };
            document.addEventListener("fullscreenchange", this._onFsChange);
        });

        onWillUnmount(() => {
            document.removeEventListener("fullscreenchange", this._onFsChange);
            if (this._clockInterval) clearInterval(this._clockInterval);
            if (this._navObs) this._navObs.disconnect();
        });
    }

    // ── Panel ─────────────────────────────────────────────────────────────────
    toggle()   { this.state.open = !this.state.open; }
    close()    { this.state.open = false; }
    setTab(id) { this.state.activeTab = id; lsSet(K.tab, id); }

    // ── Display ───────────────────────────────────────────────────────────────
    async toggleFullscreen() {
        if (!document.fullscreenElement) {
            await document.documentElement.requestFullscreen().catch(()=>{});
            this.state.fullscreen = true;
        } else {
            await document.exitFullscreen().catch(()=>{});
            this.state.fullscreen = false;
        }
    }
    toggleNavbar() {
        this.state.navbarHidden = !this.state.navbarHidden;
        const el = document.querySelector(".o_main_navbar");
        if (el) el.style.display = this.state.navbarHidden ? "none" : "";
    }
    toggleCompact() {
        this.state.compactMode = !this.state.compactMode;
        document.body.classList.toggle("sp_compact", this.state.compactMode);
    }

    // ── Font ──────────────────────────────────────────────────────────────────
    increaseFont() { const n = Math.min(this.state.fontSize+5, 150); this.state.fontSize=n; this._applyFont(n); }
    decreaseFont() { const n = Math.max(this.state.fontSize-5, 70);  this.state.fontSize=n; this._applyFont(n); }
    resetFont()    { this.state.fontSize=100; this._applyFont(100); }
    _applyFont(p)  { document.documentElement.style.fontSize = p+"%"; lsSet(K.font, p); }

    // ── Color ─────────────────────────────────────────────────────────────────
    applyColor(c)    { this.state.activeColor=c; this._applyColor(c); lsSet(K.color, c); }
    onCustomColor(e) { this.applyColor(e.target.value); }
    _applyColor(c) {
        const r = document.documentElement;
        r.style.setProperty("--sp-primary",    c);
        r.style.setProperty("--sp-primary-dk", darker(c, .18));
        r.style.setProperty("--sp-primary-lt", lighter(c));
        r.style.setProperty("--sp-accent",     lighter(c));
    }

    // ── Clock ─────────────────────────────────────────────────────────────────
    _startClock() {
        const tick = () => {
            const now = new Date();
            this.state.clockTime = now.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit", second:"2-digit"});
            this.state.clockDate = now.toLocaleDateString([], {weekday:"long", year:"numeric", month:"long", day:"numeric"});
            this.state.clockTz   = Intl.DateTimeFormat().resolvedOptions().timeZone;
        };
        tick();
        this._clockInterval = setInterval(tick, 1000);
    }

    // ── Calculator ────────────────────────────────────────────────────────────
    calcNum(n) {
        if (this.state.calcReset) {
            this.state.calcDisplay = n === "." ? "0." : n;
            this.state.calcReset = false;
            return;
        }
        if (n === "." && this.state.calcDisplay.includes(".")) return;
        if (n === "00" && this.state.calcDisplay === "0") return;
        this.state.calcDisplay = (this.state.calcDisplay === "0" && n !== "." && n !== "00")
            ? n : this.state.calcDisplay + n;
    }
    calcOp(op) {
        this.state.calcPrev  = parseFloat(this.state.calcDisplay);
        this.state.calcOp_   = op;
        this.state.calcExpr  = this.state.calcDisplay + " " + op;
        this.state.calcReset = true;
    }
    calcEquals() {
        if (!this.state.calcOp_) return;
        const a = this.state.calcPrev, b = parseFloat(this.state.calcDisplay);
        let res;
        if      (this.state.calcOp_ === "+") res = a + b;
        else if (this.state.calcOp_ === "-") res = a - b;
        else if (this.state.calcOp_ === "*") res = a * b;
        else if (this.state.calcOp_ === "/") res = b !== 0 ? a / b : "Error";
        else res = b;
        this.state.calcExpr    = `${a} ${this.state.calcOp_} ${b} =`;
        this.state.calcDisplay = typeof res === "number" ? String(parseFloat(res.toFixed(10))) : res;
        this.state.calcOp_     = null;
        this.state.calcReset   = true;
    }
    calcClear()      { this.state.calcDisplay="0"; this.state.calcExpr=""; this.state.calcOp_=null; this.state.calcPrev=null; this.state.calcReset=false; }
    calcBackspace()  { const d = this.state.calcDisplay; this.state.calcDisplay = d.length > 1 ? d.slice(0,-1) : "0"; }
    calcToggleSign() { this.state.calcDisplay = this.state.calcDisplay.startsWith("-") ? this.state.calcDisplay.slice(1) : "-"+this.state.calcDisplay; }

    // ── Session ───────────────────────────────────────────────────────────────
    _loadSession() {
        try {
            this.state.sessionUser = session.name || session.username || "";
        } catch { this.state.sessionUser = ""; }
    }

    // ── Bookmarks ─────────────────────────────────────────────────────────────
    addBookmark() {
        const name = (this.state.newBmName || "").trim() || document.title || "Bookmark";
        let model = "";
        try { const m = window.location.pathname.match(/\/odoo\/([^/]+)/); model = m ? m[1] : ""; } catch {}
        const bm = { id:Date.now(), name, url:window.location.href, model };
        this.state.bookmarks = [bm, ...this.state.bookmarks];
        this.state.newBmName = "";
        lsSet(K.bookmarks, this.state.bookmarks);
    }
    deleteBm(id) { this.state.bookmarks = this.state.bookmarks.filter(b=>b.id!==id); lsSet(K.bookmarks, this.state.bookmarks); }

    // ── Recent ────────────────────────────────────────────────────────────────
    _trackNav() {
        this._lastUrl = window.location.href;
        this._addRecent();
        this._navObs = new MutationObserver(() => {
            if (window.location.href !== this._lastUrl) {
                this._lastUrl = window.location.href;
                this._addRecent();
            }
        });
        this._navObs.observe(document.body, { childList:true, subtree:true });
    }
    _addRecent() {
        const url = window.location.href, name = document.title || url;
        let model = "";
        try { const m = window.location.pathname.match(/\/odoo\/([^/]+)/); model = m ? m[1] : ""; } catch {}
        const entry = { id:Date.now(), name, url, model };
        this.state.recent = [entry, ...(this.state.recent||[]).filter(r=>r.url!==url)].slice(0,20);
        lsSet(K.recent, this.state.recent);
    }
    deleteRecent(id) { this.state.recent = this.state.recent.filter(r=>r.id!==id); lsSet(K.recent, this.state.recent); }
    clearRecent()    { this.state.recent = []; lsSet(K.recent, []); }

    // ── Notes ─────────────────────────────────────────────────────────────────
    saveNotes()  { lsSet(K.notes, this.state.notes); }
    clearNotes() { this.state.notes = ""; lsSet(K.notes, ""); }

    // ── Navigation ────────────────────────────────────────────────────────────
    goTo(url) {
        try {
            const u = new URL(url);
            window.history.pushState({}, "", u.pathname + u.search + u.hash);
            window.dispatchEvent(new PopStateEvent("popstate", { state:{} }));
        } catch { window.location.href = url; }
        this.close();
    }
}

registry.category("main_components").add("SidebarPremium", {
    Component: SidebarPremium,
});