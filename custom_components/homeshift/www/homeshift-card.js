function e(e,t,i,s){var o,n=arguments.length,a=n<3?t:null===s?s=Object.getOwnPropertyDescriptor(t,i):s;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)a=Reflect.decorate(e,t,i,s);else for(var r=e.length-1;r>=0;r--)(o=e[r])&&(a=(n<3?o(a):n>3?o(t,i,a):o(t,i))||a);return n>3&&a&&Object.defineProperty(t,i,a),a}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const t=globalThis,i=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,s=Symbol(),o=new WeakMap;let n=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==s)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(i&&void 0===e){const i=void 0!==t&&1===t.length;i&&(e=o.get(t)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&o.set(t,e))}return e}toString(){return this.cssText}};const a=(e,...t)=>{const i=1===e.length?e[0]:t.reduce((t,i,s)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[s+1],e[0]);return new n(i,e,s)},r=i?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const i of e.cssRules)t+=i.cssText;return(e=>new n("string"==typeof e?e:e+"",void 0,s))(t)})(e):e,{is:c,defineProperty:d,getOwnPropertyDescriptor:l,getOwnPropertyNames:h,getOwnPropertySymbols:p,getPrototypeOf:u}=Object,m=globalThis,f=m.trustedTypes,_=f?f.emptyScript:"",g=m.reactiveElementPolyfillSupport,v=(e,t)=>e,b={toAttribute(e,t){switch(t){case Boolean:e=e?_:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let i=e;switch(t){case Boolean:i=null!==e;break;case Number:i=null===e?null:Number(e);break;case Object:case Array:try{i=JSON.parse(e)}catch(e){i=null}}return i}},y=(e,t)=>!c(e,t),x={attribute:!0,type:String,converter:b,reflect:!1,useDefault:!1,hasChanged:y};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),m.litPropertyMetadata??=new WeakMap;let $=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=x){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const i=Symbol(),s=this.getPropertyDescriptor(e,i,t);void 0!==s&&d(this.prototype,e,s)}}static getPropertyDescriptor(e,t,i){const{get:s,set:o}=l(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:s,set(t){const n=s?.call(this);o?.call(this,t),this.requestUpdate(e,n,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??x}static _$Ei(){if(this.hasOwnProperty(v("elementProperties")))return;const e=u(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(v("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(v("properties"))){const e=this.properties,t=[...h(e),...p(e)];for(const i of t)this.createProperty(i,e[i])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,i]of t)this.elementProperties.set(e,i)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const i=this._$Eu(e,t);void 0!==i&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const i=new Set(e.flat(1/0).reverse());for(const e of i)t.unshift(r(e))}else void 0!==e&&t.push(r(e));return t}static _$Eu(e,t){const i=t.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const i of t.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((e,s)=>{if(i)e.adoptedStyleSheets=s.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const i of s){const s=document.createElement("style"),o=t.litNonce;void 0!==o&&s.setAttribute("nonce",o),s.textContent=i.cssText,e.appendChild(s)}})(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,i){this._$AK(e,i)}_$ET(e,t){const i=this.constructor.elementProperties.get(e),s=this.constructor._$Eu(e,i);if(void 0!==s&&!0===i.reflect){const o=(void 0!==i.converter?.toAttribute?i.converter:b).toAttribute(t,i.type);this._$Em=e,null==o?this.removeAttribute(s):this.setAttribute(s,o),this._$Em=null}}_$AK(e,t){const i=this.constructor,s=i._$Eh.get(e);if(void 0!==s&&this._$Em!==s){const e=i.getPropertyOptions(s),o="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:b;this._$Em=s;const n=o.fromAttribute(t,e.type);this[s]=n??this._$Ej?.get(s)??n,this._$Em=null}}requestUpdate(e,t,i,s=!1,o){if(void 0!==e){const n=this.constructor;if(!1===s&&(o=this[e]),i??=n.getPropertyOptions(e),!((i.hasChanged??y)(o,t)||i.useDefault&&i.reflect&&o===this._$Ej?.get(e)&&!this.hasAttribute(n._$Eu(e,i))))return;this.C(e,t,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:i,reflect:s,wrapped:o},n){i&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,n??t??this[e]),!0!==o||void 0!==n)||(this._$AL.has(e)||(this.hasUpdated||i||(t=void 0),this._$AL.set(e,t)),!0===s&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,i]of e){const{wrapped:e}=i,s=this[t];!0!==e||this._$AL.has(t)||void 0===s||this.C(t,void 0,i,s)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};$.elementStyles=[],$.shadowRootOptions={mode:"open"},$[v("elementProperties")]=new Map,$[v("finalized")]=new Map,g?.({ReactiveElement:$}),(m.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const w=globalThis,k=e=>e,S=w.trustedTypes,E=S?S.createPolicy("lit-html",{createHTML:e=>e}):void 0,A="$lit$",C=`lit$${Math.random().toFixed(9).slice(2)}$`,T="?"+C,P=`<${T}>`,M=document,D=()=>M.createComment(""),O=e=>null===e||"object"!=typeof e&&"function"!=typeof e,z=Array.isArray,N="[ \t\n\f\r]",I=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,R=/-->/g,H=/>/g,j=RegExp(`>|${N}(?:([^\\s"'>=/]+)(${N}*=${N}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),U=/'/g,L=/"/g,B=/^(?:script|style|textarea|title)$/i,q=e=>(t,...i)=>({_$litType$:e,strings:t,values:i}),V=q(1),W=q(2),F=Symbol.for("lit-noChange"),K=Symbol.for("lit-nothing"),Y=new WeakMap,J=M.createTreeWalker(M,129);function X(e,t){if(!z(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==E?E.createHTML(t):t}const Z=(e,t)=>{const i=e.length-1,s=[];let o,n=2===t?"<svg>":3===t?"<math>":"",a=I;for(let t=0;t<i;t++){const i=e[t];let r,c,d=-1,l=0;for(;l<i.length&&(a.lastIndex=l,c=a.exec(i),null!==c);)l=a.lastIndex,a===I?"!--"===c[1]?a=R:void 0!==c[1]?a=H:void 0!==c[2]?(B.test(c[2])&&(o=RegExp("</"+c[2],"g")),a=j):void 0!==c[3]&&(a=j):a===j?">"===c[0]?(a=o??I,d=-1):void 0===c[1]?d=-2:(d=a.lastIndex-c[2].length,r=c[1],a=void 0===c[3]?j:'"'===c[3]?L:U):a===L||a===U?a=j:a===R||a===H?a=I:(a=j,o=void 0);const h=a===j&&e[t+1].startsWith("/>")?" ":"";n+=a===I?i+P:d>=0?(s.push(r),i.slice(0,d)+A+i.slice(d)+C+h):i+C+(-2===d?t:h)}return[X(e,n+(e[i]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),s]};class G{constructor({strings:e,_$litType$:t},i){let s;this.parts=[];let o=0,n=0;const a=e.length-1,r=this.parts,[c,d]=Z(e,t);if(this.el=G.createElement(c,i),J.currentNode=this.el.content,2===t||3===t){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(s=J.nextNode())&&r.length<a;){if(1===s.nodeType){if(s.hasAttributes())for(const e of s.getAttributeNames())if(e.endsWith(A)){const t=d[n++],i=s.getAttribute(e).split(C),a=/([.?@])?(.*)/.exec(t);r.push({type:1,index:o,name:a[2],strings:i,ctor:"."===a[1]?se:"?"===a[1]?oe:"@"===a[1]?ne:ie}),s.removeAttribute(e)}else e.startsWith(C)&&(r.push({type:6,index:o}),s.removeAttribute(e));if(B.test(s.tagName)){const e=s.textContent.split(C),t=e.length-1;if(t>0){s.textContent=S?S.emptyScript:"";for(let i=0;i<t;i++)s.append(e[i],D()),J.nextNode(),r.push({type:2,index:++o});s.append(e[t],D())}}}else if(8===s.nodeType)if(s.data===T)r.push({type:2,index:o});else{let e=-1;for(;-1!==(e=s.data.indexOf(C,e+1));)r.push({type:7,index:o}),e+=C.length-1}o++}}static createElement(e,t){const i=M.createElement("template");return i.innerHTML=e,i}}function Q(e,t,i=e,s){if(t===F)return t;let o=void 0!==s?i._$Co?.[s]:i._$Cl;const n=O(t)?void 0:t._$litDirective$;return o?.constructor!==n&&(o?._$AO?.(!1),void 0===n?o=void 0:(o=new n(e),o._$AT(e,i,s)),void 0!==s?(i._$Co??=[])[s]=o:i._$Cl=o),void 0!==o&&(t=Q(e,o._$AS(e,t.values),o,s)),t}class ee{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:i}=this._$AD,s=(e?.creationScope??M).importNode(t,!0);J.currentNode=s;let o=J.nextNode(),n=0,a=0,r=i[0];for(;void 0!==r;){if(n===r.index){let t;2===r.type?t=new te(o,o.nextSibling,this,e):1===r.type?t=new r.ctor(o,r.name,r.strings,this,e):6===r.type&&(t=new ae(o,this,e)),this._$AV.push(t),r=i[++a]}n!==r?.index&&(o=J.nextNode(),n++)}return J.currentNode=M,s}p(e){let t=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(e,i,t),t+=i.strings.length-2):i._$AI(e[t])),t++}}class te{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,i,s){this.type=2,this._$AH=K,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=i,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=Q(this,e,t),O(e)?e===K||null==e||""===e?(this._$AH!==K&&this._$AR(),this._$AH=K):e!==this._$AH&&e!==F&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>z(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==K&&O(this._$AH)?this._$AA.nextSibling.data=e:this.T(M.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:i}=e,s="number"==typeof i?this._$AC(e):(void 0===i.el&&(i.el=G.createElement(X(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===s)this._$AH.p(t);else{const e=new ee(s,this),i=e.u(this.options);e.p(t),this.T(i),this._$AH=e}}_$AC(e){let t=Y.get(e.strings);return void 0===t&&Y.set(e.strings,t=new G(e)),t}k(e){z(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let i,s=0;for(const o of e)s===t.length?t.push(i=new te(this.O(D()),this.O(D()),this,this.options)):i=t[s],i._$AI(o),s++;s<t.length&&(this._$AR(i&&i._$AB.nextSibling,s),t.length=s)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=k(e).nextSibling;k(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}class ie{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,i,s,o){this.type=1,this._$AH=K,this._$AN=void 0,this.element=e,this.name=t,this._$AM=s,this.options=o,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=K}_$AI(e,t=this,i,s){const o=this.strings;let n=!1;if(void 0===o)e=Q(this,e,t,0),n=!O(e)||e!==this._$AH&&e!==F,n&&(this._$AH=e);else{const s=e;let a,r;for(e=o[0],a=0;a<o.length-1;a++)r=Q(this,s[i+a],t,a),r===F&&(r=this._$AH[a]),n||=!O(r)||r!==this._$AH[a],r===K?e=K:e!==K&&(e+=(r??"")+o[a+1]),this._$AH[a]=r}n&&!s&&this.j(e)}j(e){e===K?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class se extends ie{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===K?void 0:e}}class oe extends ie{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==K)}}class ne extends ie{constructor(e,t,i,s,o){super(e,t,i,s,o),this.type=5}_$AI(e,t=this){if((e=Q(this,e,t,0)??K)===F)return;const i=this._$AH,s=e===K&&i!==K||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,o=e!==K&&(i===K||s);s&&this.element.removeEventListener(this.name,this,i),o&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class ae{constructor(e,t,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){Q(this,e)}}const re=w.litHtmlPolyfillSupport;re?.(G,te),(w.litHtmlVersions??=[]).push("3.3.2");const ce=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class de extends ${constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,i)=>{const s=i?.renderBefore??t;let o=s._$litPart$;if(void 0===o){const e=i?.renderBefore??null;s._$litPart$=o=new te(t.insertBefore(D(),e),e,void 0,i??{})}return o._$AI(e),o})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return F}}de._$litElement$=!0,de.finalized=!0,ce.litElementHydrateSupport?.({LitElement:de});const le=ce.litElementPolyfillSupport;le?.({LitElement:de}),(ce.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const he={attribute:!0,type:String,converter:b,reflect:!1,hasChanged:y},pe=(e=he,t,i)=>{const{kind:s,metadata:o}=i;let n=globalThis.litPropertyMetadata.get(o);if(void 0===n&&globalThis.litPropertyMetadata.set(o,n=new Map),"setter"===s&&((e=Object.create(e)).wrapped=!0),n.set(i.name,e),"accessor"===s){const{name:s}=i;return{set(i){const o=t.get.call(this);t.set.call(this,i),this.requestUpdate(s,o,e,!0,i)},init(t){return void 0!==t&&this.C(s,void 0,e,t),t}}}if("setter"===s){const{name:s}=i;return function(i){const o=this[s];t.call(this,i),this.requestUpdate(s,o,e,!0,i)}}throw Error("Unsupported decorator location: "+s)};function ue(e){return(t,i)=>"object"==typeof i?pe(e,t,i):((e,t,i)=>{const s=t.hasOwnProperty(i);return t.constructor.createProperty(i,e),s?Object.getOwnPropertyDescriptor(t,i):void 0})(e,t,i)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function me(e){return ue({...e,state:!0,attribute:!1})}const fe={en:{card:{entity_not_found:"Entity not found: {entity}",unavailable:"Unavailable",today:"Today",tomorrow:"Tomorrow",heat_protection_active:"Heat protection active",cover_open_time:"Cover opening time",cover_close_time:"Cover closing time",cover_open_action:"Open the covers now (scheduled {time})",cover_close_action:"Close the covers now (scheduled {time})",cover_sending:"Sending…",cover_open_failed:"Could not open the covers: {error}",cover_close_failed:"Could not close the covers: {error}",covers_left_open:"Not closed: {covers}",thermostat_mode:"Thermostat mode",day_mode:"Day mode",next:"Next",covers:"Covers",duration_off:"No",decrease:"Decrease: {setting}",increase:"Increase: {setting}",override_label:"Keep my manual choice",override_none:"A manual change is replaced at the calendar's next pass.",override_effect:"After a change by hand, the calendar waits {duration} — until {time} if you change it now.",early_label:"Start events early",early_none:"{mode} will start at its scheduled time, {time}.",early_effect:"{mode} will start at {time} instead of {scheduled}.",early_no_event:"No event scheduled.",covers_left_open_count:"Not closed: {count} covers",inhibit_label:"Cover automation",inhibit_none:"Auto",inhibited_count:"{count} paused",inhibit_forever:"Until resumed",days_short:"d",inhibit_effect:"Pause for {duration} — until {time} if you start it now.",inhibit_effect_forever:"The cover stays paused until you resume it.",inhibited_until:"Paused until {time}",inhibited_forever:"Paused until resumed",pause:"Pause",resume:"Resume",resume_all:"Resume all",covers_paused:"Paused: {covers}",covers_paused_count:"{count} covers paused",inhibit_failed:"Could not pause or resume the cover: {error}",calendar_unreadable:"Calendar unreadable",calendar_unreadable_detail:"Since {time}. Day mode kept: {mode}.",heat_pumps:"Climate auto start/stop",heat_pump_auto:"Auto",heat_pump_comfort:"Comfort",heat_pump_idle:"—",heat_pump_not_driven:"Not driven in this thermostat mode",heat_pump_thermostat_off:"Thermostat off: left as it is",heat_pump_manual:"Set by hand",heat_pump_failed:"Could not switch the climate's auto start/stop: {error}",heat_pump_not_driven_short:"not driven",heat_pump_runs_from:"Setpoint {setpoint}° · runs from {threshold}°",heat_pump_runs_up_to:"Setpoint {setpoint}° · runs up to {threshold}°",heat_pump_stops_below:"Setpoint {setpoint}° · may stop below {threshold}°",heat_pump_stops_above:"Setpoint {setpoint}° · may stop above {threshold}°"},thermostat:{off:"Off",heating:"Heating",cooling:"Cooling",ventilation:"Ventilation"},schedule:{title:"Schedules",empty:"No schedule for {mode}",on:"On",off:"Off",edit:"Edit schedules",back:"Back to timelines",active_mode:"Current day mode",next_run:"Next run",days:"Days",note_active:"Current day mode: its schedules are applied",note_inactive:"Not the current day mode: its schedules are off"},editor:{name:"Name",entities:"Entities (advanced)",entities_hint:"Detected automatically. Set one only to replace it.",day_mode_entity:"Day Mode Entity",thermostat_mode_entity:"Thermostat Mode Entity",override_duration_entity:"Override Duration Entity",early_switch_entity:"Early Switch Entity",next_mode_entity:"Next Mode Entity",next_mode_at_entity:"Next Mode Time Entity",heat_protection_entity:"Heat Protection Entity",cover_open_time_entity:"Cover Open Time Entity",cover_close_time_entity:"Cover Close Time Entity",open_covers_entity:"Open Covers Button",close_covers_entity:"Close Covers Button",cover_entity:"Cover Entity (legacy, overrides the buttons)",covers_left_open_entity:"Covers Left Open Entity",covers_inhibited_entity:"Paused covers entity",show_schedules:"Schedules panel (Scheduler integration)",schedule_entities:"Schedules panel: only these entities (all when empty)",auto_start_stop_entity:"Climate auto start/stop entity"},preview:{home:"Home",work:"Work",remote:"Remote",away:"Away"}},fr:{card:{entity_not_found:"Entité introuvable: {entity}",unavailable:"Indisponible",today:"Auj.",tomorrow:"Dem.",heat_protection_active:"Protection thermique active",cover_open_time:"Heure d'ouverture des volets",cover_close_time:"Heure de fermeture des volets",cover_open_action:"Ouvrir les volets maintenant (prévu à {time})",cover_close_action:"Fermer les volets maintenant (prévu à {time})",cover_sending:"Envoi…",cover_open_failed:"Impossible d'ouvrir les volets : {error}",cover_close_failed:"Impossible de fermer les volets : {error}",covers_left_open:"Non fermés : {covers}",thermostat_mode:"Mode thermostat",day_mode:"Mode du jour",next:"Prochain",covers:"Volets",duration_off:"Non",decrease:"Diminuer : {setting}",increase:"Augmenter : {setting}",override_label:"Garder mon choix manuel",override_none:"Un changement manuel est remplacé au prochain passage du calendrier.",override_effect:"Après un changement à la main, le calendrier attend {duration} — jusqu'à {time} si tu changes maintenant.",early_label:"Anticiper les événements",early_none:"{mode} commencera à l'heure prévue, {time}.",early_effect:"{mode} commencera à {time} au lieu de {scheduled}.",early_no_event:"Aucun événement prévu.",covers_left_open_count:"Non fermés : {count} volets",inhibit_label:"Pilotage auto des volets",inhibit_none:"Auto",inhibited_count:"{count} en pause",inhibit_forever:"Jusqu'à reprise",days_short:"j",inhibit_effect:"Pause de {duration} — jusqu'à {time} si tu l'actives maintenant.",inhibit_effect_forever:"Le volet reste en pause jusqu'à ce que tu le reprennes.",inhibited_until:"En pause jusqu'à {time}",inhibited_forever:"En pause jusqu'à reprise",pause:"Pause",resume:"Reprendre",resume_all:"Tout reprendre",covers_paused:"En pause : {covers}",covers_paused_count:"{count} volets en pause",inhibit_failed:"Échec de la mise en pause : {error}",calendar_unreadable:"Calendrier illisible",calendar_unreadable_detail:"Depuis {time}. Mode du jour conservé : {mode}.",heat_pumps:"Auto start/stop des équipements",heat_pump_auto:"Auto",heat_pump_comfort:"Confort",heat_pump_idle:"—",heat_pump_not_driven:"Non piloté dans ce mode thermostat",heat_pump_thermostat_off:"Thermostat éteint : laissé tel quel",heat_pump_manual:"Forcé à la main",heat_pump_failed:"Impossible de basculer l'auto start/stop de l'équipement : {error}",heat_pump_not_driven_short:"non piloté",heat_pump_runs_from:"Consigne {setpoint}° · tourne dès {threshold}°",heat_pump_runs_up_to:"Consigne {setpoint}° · tourne jusqu'à {threshold}°",heat_pump_stops_below:"Consigne {setpoint}° · arrêt possible sous {threshold}°",heat_pump_stops_above:"Consigne {setpoint}° · arrêt possible au-dessus de {threshold}°"},thermostat:{off:"Éteint",heating:"Chauffage",cooling:"Climatisation",ventilation:"Ventilation"},schedule:{title:"Plannings",empty:"Aucune planification pour {mode}",on:"Allumé",off:"Éteint",edit:"Modifier les planifications",back:"Retour aux frises",active_mode:"Mode du jour actuel",next_run:"Prochain lancement",days:"Jours",note_active:"Mode du jour actuel : ses plannings sont appliqués",note_inactive:"Mode non actif : ses plannings sont coupés"},editor:{name:"Nom",entities:"Entités (avancé)",entities_hint:"Détectées automatiquement. N'en choisissez une que pour la remplacer.",day_mode_entity:"Entité mode jour",thermostat_mode_entity:"Entité mode thermostat",override_duration_entity:"Entité durée de dérogation",early_switch_entity:"Entité anticipation",next_mode_entity:"Entité prochain mode",next_mode_at_entity:"Entité heure du prochain mode",heat_protection_entity:"Entité protection thermique",cover_open_time_entity:"Entité heure d'ouverture des volets",cover_close_time_entity:"Entité heure de fermeture des volets",open_covers_entity:"Bouton d'ouverture des volets",close_covers_entity:"Bouton de fermeture des volets",cover_entity:"Entité volet (ancienne option, prioritaire sur les boutons)",covers_left_open_entity:"Entité volets non fermés",covers_inhibited_entity:"Entité volets en pause",show_schedules:"Panneau des plannings (intégration Scheduler)",schedule_entities:"Panneau des plannings : seulement ces entités (toutes si vide)",auto_start_stop_entity:"Entité auto start/stop des équipements"},preview:{home:"Maison",work:"Travail",remote:"Télétravail",away:"Absence"}}};function _e(e,t){return t.split(".").reduce((e,t)=>e&&null!=e[t]?e[t]:void 0,e)}function ge(e,t,i,s){const o=function(e){const t=e?.locale?.language||e?.language||"en",i=String(t).split("-")[0];return fe[t]?t:fe[i]?i:"en"}(e);let n=_e(fe[o],t)??_e(fe.en,t)??s;return null==n?t:(i&&Object.entries(i).forEach(([e,t])=>n=n.replace(`{${e}}`,t)),n)}const ve=[{key:"day_mode_entity",domains:["select","input_select"],default:"select.homeshift_day_mode"},{key:"thermostat_mode_entity",domains:["select","input_select"],default:"select.homeshift_thermostat_mode"},{key:"override_duration_entity",domains:["number","input_number"],default:"number.homeshift_override_duration"},{key:"early_switch_entity",domains:["number","input_number"],default:"number.homeshift_early_switch"},{key:"next_mode_entity",domains:["sensor"],default:"sensor.homeshift_next_mode"},{key:"next_mode_at_entity",domains:["sensor"],default:"sensor.homeshift_next_mode_at"},{key:"heat_protection_entity",domains:["binary_sensor"],default:"binary_sensor.homeshift_cover_heat_active"},{key:"cover_open_time_entity",domains:["sensor"],default:"sensor.homeshift_cover_open_time"},{key:"cover_close_time_entity",domains:["sensor"],default:"sensor.homeshift_cover_close_time"},{key:"open_covers_entity",domains:["button"],default:"button.homeshift_open_covers"},{key:"close_covers_entity",domains:["button"],default:"button.homeshift_close_covers"},{key:"cover_entity",domains:["cover"],default:""},{key:"covers_left_open_entity",domains:["binary_sensor"],default:"binary_sensor.homeshift_covers_left_open"},{key:"covers_inhibited_entity",domains:["sensor"],default:"sensor.homeshift_covers_inhibited"},{key:"auto_start_stop_entity",domains:["sensor"],default:"sensor.homeshift_auto_start_stop"}];class be extends de{setConfig(e){this._config=e}_onNameChanged(e){if(!this._config||!this.hass)return;const t=e.target.value;if(this._config.name===t)return;const i={...this._config,name:t};this._config=i,this._dispatchConfigChanged(i)}_onEntityChanged(e,t){if(!this._config||!this.hass)return;const i=e.detail.value;if(this._config[t]===i)return;const s={...this._config,[t]:i};this._config=s,this._dispatchConfigChanged(s)}_onScheduleChanged(e,t){if(!this._config||!this.hass)return;const i={...this._config,[t]:e.detail.value};this._config=i,this._dispatchConfigChanged(i)}_dispatchConfigChanged(e){const t=new CustomEvent("config-changed",{detail:{config:e},bubbles:!0,composed:!0});this.dispatchEvent(t)}render(){return this.hass&&this._config?V`
      <div class="card-config">
        <ha-textfield
          label="${ge(this.hass,"editor.name")}"
          .value=${this._config.name||""}
          @input=${this._onNameChanged}
        ></ha-textfield>

        <ha-selector
          .hass=${this.hass}
          .label=${ge(this.hass,"editor.show_schedules")}
          .selector=${{boolean:{}}}
          .value=${!1!==this._config.show_schedules}
          @value-changed=${e=>this._onScheduleChanged(e,"show_schedules")}
        ></ha-selector>
        <ha-selector
          .hass=${this.hass}
          .label=${ge(this.hass,"editor.schedule_entities")}
          .selector=${{entity:{multiple:!0}}}
          .value=${this._config.schedule_entities??[]}
          @value-changed=${e=>this._onScheduleChanged(e,"schedule_entities")}
        ></ha-selector>

        <ha-expansion-panel
          outlined
          .header=${ge(this.hass,"editor.entities")}
        >
          <p class="hint">${ge(this.hass,"editor.entities_hint")}</p>
          ${ve.map(e=>V`<ha-entity-picker
              label="${ge(this.hass,`editor.${e.key}`)}"
              .hass=${this.hass}
              .value=${this._config[e.key]||""}
              .includeDomains=${e.domains}
              @value-changed=${t=>this._onEntityChanged(t,e.key)}
              allow-custom-entity
            ></ha-entity-picker>`)}
        </ha-expansion-panel>
      </div>
    `:V``}}be.styles=a`
    .card-config {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 16px 0;
    }

    ha-textfield,
    ha-entity-picker,
    ha-selector {
      width: 100%;
    }

    ha-expansion-panel ha-entity-picker {
      display: block;
      margin-bottom: 16px;
    }

    .hint {
      margin: 8px 0 16px;
      color: var(--secondary-text-color);
      font-size: 13px;
    }
  `,e([ue({attribute:!1})],be.prototype,"hass",void 0),e([me()],be.prototype,"_config",void 0),customElements.get("homeshift-card-editor")||customElements.define("homeshift-card-editor",be);function ye(e){return e.split(".")[1]?.replace(/^homeshift_/,"")??""}const xe=new Set(["unknown","unavailable",""]);function $e(e){const t="string"==typeof e?e:e?.state;return"string"==typeof t&&!xe.has(t)}function we(e){if(e<60)return`${e} min`;const t=Math.floor(e/60),i=Math.round(e%60);return i>0?`${t}h${String(i).padStart(2,"0")}`:`${t}h`}function ke(e){const t=e?.time_format;return{locale:"system"===t?void 0:e?.language,hour12:"12"===t||"24"!==t&&void 0}}function Se(e,t){const{locale:i,hour12:s}=ke(t);return e.toLocaleTimeString(i,{hour:"2-digit",minute:"2-digit",hour12:s})}const Ee=1440;function Ae(e){const[t,i]=e.split(":").map(Number);return 60*t+(i||0)}function Ce(e){const t=e%Ee;return`${String(Math.floor(t/60)).padStart(2,"0")}:${String(t%60).padStart(2,"0")}`}const Te=e=>e.service.startsWith("climate.");function Pe(e){return e.timeslots.some(e=>e.actions.some(Te))}function Me(e){const t=Pe(e),i=e.timeslots.filter(e=>!t||e.actions.some(Te)).map(e=>({slot:e,start:Ae(e.start)})).sort((e,t)=>e.start-t.start),s=[];return i.forEach(({slot:e,start:t},o)=>{const n=function(e){const t=e.actions?.find(Te)??e.actions?.[0];if(!t)return{kind:"other",label:""};const[,i]=t.service.split("."),s=t.service_data??{},o=t.entity_id,n=s.hvac_mode;if("off"===n)return{kind:"off",entity:o,hvacMode:n,label:n};if("turn_off"===i)return{kind:"off",entity:o,label:"off"};if("number"==typeof s.temperature)return{kind:"cool"===n?"cool":"heat",entity:o,temperature:s.temperature,label:`${s.temperature}°`};if(null!=s.preset_mode){const e=String(s.preset_mode);return{kind:"preset",entity:o,preset:e,label:e}}return n?{kind:"cool"===n?"cool":"heat",entity:o,hvacMode:n,label:n}:"turn_on"===i?{kind:"on",entity:o,label:"on"}:{kind:"other",entity:o,label:i??t.service}}(e);let a;if(null!=e.stop)a=Ae(e.stop),a<=t&&(a+=Ee);else{const e=i[(o+1)%i.length].start;a=e>t?e:e+Ee}a>Ee?(s.push({start:t,end:Ee,value:n}),a-Ee>0&&s.push({start:0,end:a-Ee,value:n})):s.push({start:t,end:a,value:n})}),function(e){const t=[];for(const i of e){const e=t[t.length-1];e&&e.end===i.start&&De(e.value,i.value)?e.end=i.end:t.push({...i})}return t}(s.filter(e=>e.end>e.start).sort((e,t)=>e.start-t.start))}function De(e,t){return e.kind===t.kind&&e.temperature===t.temperature&&e.preset===t.preset&&e.hvacMode===t.hvacMode&&e.label===t.label}function Oe(e,t=!1){const i=t&&Pe(e),s=e.timeslots.flatMap(e=>e.actions.filter(e=>!i||Te(e)).map(e=>e.entity_id).filter(e=>!!e));return[...new Set(s)]}const ze={heat:"mdi:radiator",cool:"mdi:snowflake",preset:"mdi:radiator",on:"mdi:toggle-switch-outline",off:"mdi:toggle-switch-off-outline",other:"mdi:calendar-clock"};function Ne(e){return"cool"===e?"cool":"heat"===e||"preset"===e?"heat":void 0}const Ie={heat:"255, 140, 40",cool:"61, 155, 233"},Re=W`<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 6.2 5 8.5l4.5-5" /></svg>`,He=W`<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3.5 3.5l5 5M8.5 3.5l-5 5" /></svg>`,je=["heat","preset","cool","on","off","other"];function Ue(e){const t=new Set(e.map(e=>e.value.kind));return["cool","heat","preset","on","off"].find(e=>t.has(e))??"other"}class Le extends de{constructor(){super(...arguments),this.schedules=[],this.tag="",this.entities=[]}connectedCallback(){super.connectedCallback(),this._clock=setInterval(()=>this.requestUpdate(),6e4)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this._clock)}render(){if(!this.hass)return K;const e=function(e,t,i){return e.filter(e=>e.tags?.includes(t)).filter(e=>!i.length||Oe(e).some(e=>i.includes(e))).sort((e,t)=>e.name.localeCompare(t.name))}(this.schedules,this.tag,this.entities);if(!e.length)return V`<div class="empty">
        ${ge(this.hass,"schedule.empty",{mode:this.tag})}
      </div>`;const t=new Date,i=60*t.getHours()+t.getMinutes();return V`
      ${this._rooms(e).map(e=>this._renderRoom(e,i))}
      <div class="axis" aria-hidden="true">
        ${[0,6,12,18,24].map(e=>V`<span style="left: ${e/24*100}%">${e}h</span>`)}
      </div>
    `}_rooms(e){const t=new Map;for(const i of e){const e=Oe(i,!0),s=1===e.length?e[0]:void 0,o=s??i.entity_id;if(!t.has(o)){const e=s?this.hass.states[s]?.attributes?.friendly_name??s:i.name;t.set(o,{name:e,entity:s,schedules:[]})}t.get(o).schedules.push(i)}for(const e of t.values())e.schedules.sort((e,t)=>je.indexOf(Ue(Me(e)))-je.indexOf(Ue(Me(t))));return[...t.values()]}_renderRoom(e,t){const i=e.entity?.startsWith("climate.")?this.hass.states[e.entity]?.attributes?.current_temperature:void 0,s=e.schedules.every(e=>!this._enabled(e));return V`
      <div class="room">
        <div class="room-head">
          <span class="room-name ${s?"disabled":""}">${e.name}</span>
          ${"number"==typeof i?V`<span class="measured">${this._number(i)}°</span>`:K}
        </div>
        ${e.schedules.map(i=>this._renderRow(i,e,t))}
      </div>
    `}_enabled(e){const t=this.hass.states[e.entity_id];return t?"off"!==t.state:e.enabled}_renderRow(e,t,i){const s=Me(e),o=Ue(s),n=this._enabled(e),a=Ne(o);return V`
      <div class="row ${n?"":"disabled"}" title=${e.name}>
        <ha-icon class="kind ${o}" icon=${ze[o]}></ha-icon>
        <div class="bar">
          ${s.map(e=>this._renderSegment(e))}
          <div class="now" style="left: ${i/Ee*100}%"></div>
        </div>
        <button
          class="switch ${n?"on":""}"
          role="switch"
          style=${a?`--c: ${Ie[a]}`:""}
          aria-checked=${n?"true":"false"}
          aria-label=${e.name}
          @click=${()=>this._toggle(e,t,n)}
        >
          <span class="knob">${n?Re:He}</span>
        </button>
      </div>
    `}_renderSegment(e){const{background:t,color:i}=function(e){switch(e.kind){case"cool":return{background:"#378ADD",color:"#fff"};case"off":return{background:"#353B43",color:"#C3C8D0"};case"on":return{background:"#1D9E75",color:"#fff"};case"other":return{background:"#888780",color:"#fff"};case"preset":return function(e){const t=e.toLowerCase();return/frost|hors|away|absen|vacation/.test(t)?{background:"#85B7EB",color:"#042C53"}:/eco|sleep|night|nuit/.test(t)?{background:"#FAC775",color:"#412402"}:/boost/.test(t)?{background:"#A32D2D",color:"#fff"}:/comfort|confort|home|activity/.test(t)?{background:"#EF9F27",color:"#412402"}:{background:"#B4B2A9",color:"#2C2C2A"}}(e.preset??"")}const t=e.temperature??19;return t<15?{background:"#85B7EB",color:"#042C53"}:t<17.5?{background:"#FAC775",color:"#412402"}:t<19.5?{background:"#EF9F27",color:"#412402"}:t<21?{background:"#D85A30",color:"#fff"}:{background:"#A32D2D",color:"#fff"}}(e.value),s=(e.end-e.start)/Ee*100,o=`${Ce(e.start)} – ${Ce(e.end)}`,n=this._label(e.value),a=s>=Math.max(10,2.2*n.length);return V`<div
      class="segment"
      style="left: ${e.start/Ee*100}%; width: ${s}%; background-color: ${t}; color: ${i}"
      title="${o} · ${n}"
    >
      ${a?n:K}
    </div>`}_number(e){const t=this.hass.locale?.language??this.hass.language??"en";return e.toLocaleString(t,{maximumFractionDigits:1})}_label(e){const t=e.entity?this.hass.states[e.entity]:void 0;return null!=e.temperature?`${this._number(e.temperature)}°`:null!=e.preset?t&&this.hass.formatEntityAttributeValue?this.hass.formatEntityAttributeValue(t,"preset_mode",e.preset):e.preset:null!=e.hvacMode?t&&this.hass.formatEntityState?this.hass.formatEntityState(t,e.hvacMode):e.hvacMode:"on"===e.kind||"off"===e.kind?ge(this.hass,`schedule.${e.kind}`):e.label}async _toggle(e,t,i){if(i)return void await this.hass.callService("switch","turn_off",{entity_id:e.entity_id});const s=Ne(Ue(Me(e))),o=s?t.schedules.filter(t=>{const i=Ne(Ue(Me(t)));return t!==e&&i&&i!==s&&this._enabled(t)}):[];o.length&&await this.hass.callService("switch","turn_off",{entity_id:o.map(e=>e.entity_id)}),await this.hass.callService("switch","turn_on",{entity_id:e.entity_id})}}Le.styles=a`
    :host {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .room {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .room-head {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
    }
    .room-name {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-weight: 500;
    }
    .room-name.disabled {
      color: var(--secondary-text-color);
    }
    .row {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .row .bar {
      flex: 1;
    }
    /* A disabled schedule keeps its colours, hatched and dimmed, so it stays
       readable but clearly does not run. */
    .row.disabled .bar {
      opacity: 0.62;
      filter: saturate(0.7);
    }
    .row.disabled .segment {
      background-image: repeating-linear-gradient(
        135deg,
        rgba(0, 0, 0, 0.45) 0 5px,
        transparent 5px 10px
      );
    }
    .kind {
      flex: none;
      display: flex;
      justify-content: center;
      width: 20px;
      --mdc-icon-size: 18px;
      color: var(--secondary-text-color);
      transition: color 0.3s;
    }
    .kind.heat,
    .kind.preset {
      color: #ffa63d;
    }
    .kind.cool {
      color: #6fb4ff;
    }
    .row.disabled .kind {
      color: rgba(220, 235, 240, 0.35);
    }
    .measured {
      flex: none;
      display: flex;
      align-items: center;
      height: 22px;
      padding: 0 9px;
      border-radius: 11px;
      background: rgba(255, 255, 255, 0.07);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
      font-size: 12px;
      font-variant-numeric: tabular-nums;
    }
    /* 44 x 24 track, 18 px knob centred by flexbox, 3 px from every edge:
       outlined and crossed when off, filled and ticked when on. */
    .switch {
      flex: none;
      box-sizing: border-box;
      display: flex;
      align-items: center;
      width: 44px;
      height: 24px;
      margin: 0;
      padding: 0 3px;
      border: none;
      border-radius: 12px;
      background: transparent;
      box-shadow: inset 0 0 0 1.5px rgba(220, 235, 240, 0.3);
      cursor: pointer;
      transition:
        background 0.25s,
        box-shadow 0.25s;
      --c: var(--m, 3, 169, 244);
    }
    .knob {
      flex: none;
      box-sizing: border-box;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 18px;
      height: 18px;
      margin-left: 0;
      border-radius: 50%;
      background: rgba(220, 235, 240, 0.4);
      color: #141c26;
      transition:
        margin-left 0.25s,
        background 0.25s,
        color 0.25s;
    }
    .knob svg {
      display: block;
      width: 10px;
      height: 10px;
      fill: none;
      stroke: currentColor;
      stroke-width: 3;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .switch.on {
      background: rgb(var(--c));
      box-shadow: none;
    }
    .switch.on .knob {
      margin-left: 20px;
      background: #fff;
      color: rgb(var(--c));
    }
    .switch:focus-visible {
      outline: 2px solid #fff;
      outline-offset: 2px;
    }
    .bar {
      position: relative;
      height: 28px;
      border-radius: 9px;
      background: rgba(0, 0, 0, 0.3);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.05);
      overflow: hidden;
      transition:
        opacity 0.3s,
        filter 0.3s;
    }
    .segment {
      position: absolute;
      top: 0;
      bottom: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11.5px;
      font-weight: 600;
      overflow: hidden;
      white-space: nowrap;
      box-shadow: inset -2px 0 0 #121a24;
    }
    .now {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 2px;
      margin-left: -1px;
      border-radius: 1px;
      background: #fff;
      box-shadow: 0 0 6px rgba(255, 255, 255, 0.8);
    }
    .axis {
      position: relative;
      height: 14px;
      /* Under the bars only: past the kind icon (20 + 8 px) and before the switch (44 + 8 px). */
      margin: -6px 52px 0 28px;
      font-size: 11px;
      font-variant-numeric: tabular-nums;
      color: var(--secondary-text-color);
    }
    .axis span {
      position: absolute;
      transform: translateX(-50%);
    }
    .axis span:first-child {
      transform: none;
    }
    .axis span:last-child {
      transform: translateX(-100%);
    }
    .empty {
      padding: 16px 0;
      text-align: center;
      font-size: 13px;
      color: var(--secondary-text-color);
    }
    @media (prefers-reduced-motion: reduce) {
      .switch,
      .knob,
      .bar {
        transition: none;
      }
    }
  `,e([ue({attribute:!1})],Le.prototype,"hass",void 0),e([ue({attribute:!1})],Le.prototype,"schedules",void 0),e([ue()],Le.prototype,"tag",void 0),e([ue({attribute:!1})],Le.prototype,"entities",void 0),customElements.get("homeshift-schedule-timeline")||customElements.define("homeshift-schedule-timeline",Le);class Be extends de{constructor(){super(...arguments),this.schedules=[],this.modes=[],this.activeMode="",this.entities=[],this._editing=!1,this._cardsVersion=0,this._cards=new Map,this._building=new Set}willUpdate(e){e.has("activeMode")&&this.modes.includes(this.activeMode)?this._selected=this.activeMode:this._selected&&this.modes.includes(this._selected)||(this._selected=this.modes[0]),e.has("entities")&&void 0!==e.get("entities")&&(this._cards=new Map,this._building.clear())}updated(){const e=this._selected?this._cards.get(this._selected):void 0;e&&e.hass!==this.hass&&(e.hass=this.hass)}_schedulerConfig(e){return{type:"custom:scheduler-card",title:!1,discover_existing:!1,show_header_toggle:!1,time_step:5,sort_by:["title"],display_options:{primary_info:["{name}"],secondary_info:[`<b>${ge(this.hass,"schedule.next_run")}</b> {relative-time}`,`<b>${ge(this.hass,"schedule.days")}</b> {days}`,"additional-tasks"],icon:"entity"},tags:[e],...this.entities.length?{include:this.entities}:{}}}_card(e){const t=this._cards.get(e);if(t)return t;this._building.has(e)||(this._building.add(e),this._buildCard(e).finally(()=>this._building.delete(e)))}async _buildCard(e){const t=this._schedulerConfig(e),i=this._cards;this._helpers??(this._helpers=window.loadCardHelpers?.()??Promise.resolve(void 0));const s=await this._helpers;let o;s?o=s.createCardElement(t):(await customElements.whenDefined("scheduler-card"),o=document.createElement("scheduler-card"),o.setConfig(t)),i===this._cards&&(o.addEventListener("ll-rebuild",t=>{t.stopPropagation(),this._cards.delete(e),this._cardsVersion++}),o.hass=this.hass,this._cards.set(e,o),this._cardsVersion++)}_select(e){this._selected=e}_onTabKeydown(e){const t={ArrowRight:1,ArrowLeft:-1}[e.key];if(!t)return;const i=this.modes.indexOf(this._selected??""),s=this.modes[(i+t+this.modes.length)%this.modes.length];this._select(s),e.preventDefault(),this.updateComplete.then(()=>this.shadowRoot?.querySelector('[aria-selected="true"]')?.focus())}render(){if(!this.hass||!this._selected)return K;const e=this._selected,t=ge(this.hass,this._editing?"schedule.back":"schedule.edit");return V`
      <div class="header">
        <div class="tabs" role="tablist" @keydown=${this._onTabKeydown}>
          ${this.modes.map(t=>{const i=t===e;return V`<button
              class="tab ${i?"selected":""}"
              role="tab"
              aria-selected=${i?"true":"false"}
              tabindex=${i?0:-1}
              @click=${()=>this._select(t)}
            >
              <span class="label">${t}</span>
              ${t===this.activeMode?V`<span
                    class="active-dot"
                    title=${ge(this.hass,"schedule.active_mode")}
                    aria-label=${ge(this.hass,"schedule.active_mode")}
                  ></span>`:K}
            </button>`})}
        </div>
        <button
          class="edit"
          title=${t}
          aria-label=${t}
          aria-pressed=${this._editing?"true":"false"}
          @click=${()=>this._editing=!this._editing}
        >
          <ha-icon
            icon=${this._editing?"mdi:chart-timeline":"mdi:pencil"}
          ></ha-icon>
        </button>
      </div>
      ${this._editing?K:V`<p class="note ${e===this.activeMode?"active":""}">
            <ha-icon
              icon=${e===this.activeMode?"mdi:circle-medium":"mdi:information-outline"}
            ></ha-icon>
            ${ge(this.hass,e===this.activeMode?"schedule.note_active":"schedule.note_inactive")}
          </p>`}
      <div class="content" role="tabpanel">
        ${this._editing?this._card(e)??K:V`<homeshift-schedule-timeline
              .hass=${this.hass}
              .schedules=${this.schedules}
              .tag=${e}
              .entities=${this.entities}
            ></homeshift-schedule-timeline>`}
      </div>
    `}}Be.styles=a`
    :host {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .header {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    /* Segmented control, as the thermostat modes: the shown mode filled
       with the card's colour (--m, inherited from the card). */
    .tabs {
      flex: 1;
      min-width: 0;
      display: flex;
      gap: 4px;
      padding: 3px;
      border-radius: 14px;
      background: rgba(0, 0, 0, 0.28);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.06);
      overflow-x: auto;
      scrollbar-width: none;
    }
    .tab {
      flex: 1 0 auto;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      height: 36px;
      padding: 0 10px;
      border: none;
      border-radius: 11px;
      background: none;
      cursor: pointer;
      font: inherit;
      font-size: 12.5px;
      font-weight: 500;
      white-space: nowrap;
      color: var(--secondary-text-color);
      transition:
        background 0.3s,
        color 0.3s,
        box-shadow 0.3s;
    }
    .tab:hover:not(.selected) {
      background: rgba(255, 255, 255, 0.06);
      color: var(--primary-text-color);
    }
    .tab:focus-visible,
    .edit:focus-visible {
      outline: 2px solid #fff;
      outline-offset: 2px;
    }
    .tab.selected {
      color: #fff;
      background: linear-gradient(
        180deg,
        rgba(var(--m, 3, 169, 244), 0.95),
        rgba(var(--m, 3, 169, 244), 0.7)
      );
      box-shadow: 0 3px 12px -2px rgba(var(--m, 3, 169, 244), 0.6);
    }
    .active-dot {
      flex: none;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #ffd24d;
      box-shadow: 0 0 6px #ffd24d;
    }
    .edit {
      flex: none;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 38px;
      height: 38px;
      padding: 0;
      border: none;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.07);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
      color: rgb(var(--m, 3, 169, 244));
      cursor: pointer;
      --mdc-icon-size: 18px;
    }
    .edit:hover {
      background: rgba(255, 255, 255, 0.12);
    }
    .edit[aria-pressed="true"] {
      background: rgba(var(--m, 3, 169, 244), 0.85);
      color: #fff;
    }
    /* Whether the shown mode is the one whose schedules run. */
    .note {
      display: flex;
      align-items: center;
      gap: 6px;
      margin: -4px 0 0;
      font-size: 11.5px;
      color: var(--secondary-text-color);
      --mdc-icon-size: 15px;
    }
    .note.active ha-icon {
      color: #ffd24d;
    }
    /* The scheduler card blends into the panel. */
    .content {
      --ha-card-border-width: 0;
      --ha-card-box-shadow: none;
      --ha-card-background: transparent;
    }
  `,e([ue({attribute:!1})],Be.prototype,"hass",void 0),e([ue({attribute:!1})],Be.prototype,"schedules",void 0),e([ue({attribute:!1})],Be.prototype,"modes",void 0),e([ue()],Be.prototype,"activeMode",void 0),e([ue({attribute:!1})],Be.prototype,"entities",void 0),e([me()],Be.prototype,"_selected",void 0),e([me()],Be.prototype,"_editing",void 0),e([me()],Be.prototype,"_cardsVersion",void 0),customElements.get("homeshift-schedule-panel")||customElements.define("homeshift-schedule-panel",Be);const qe={off:{rgb:"148, 163, 184",icon:"mdi:power"},heating:{rgb:"255, 122, 42",icon:"mdi:fire"},cooling:{rgb:"56, 160, 240",icon:"mdi:snowflake"},ventilation:{rgb:"45, 212, 160",icon:"mdi:fan"}},Ve={rgb:"148, 163, 184",icon:"mdi:thermostat"},We={home:"mdi:home",work:"mdi:briefcase",remote:"mdi:laptop",away:"mdi:airplane"},Fe=[[6,4.2,0,-8,30],[17,5.1,1.6,12,72],[28,3.6,3.1,-14,48],[39,4.8,.7,6,86],[50,3.9,2.4,-4,22],[61,5.4,3.6,16,58],[72,4.4,1.1,-10,40],[83,3.7,2.9,8,78],[91,5,.4,-16,64],[45,4.6,3.9,10,92]],Ke=e=>W`<svg
  class="cover-icon"
  viewBox="0 0 24 24"
  aria-hidden="true"
>
  <rect class="solid" x="3" y="3" width="18" height="4" rx="1.5" />
  <path class="rails" d="M5 7v14M19 7v14" />
  ${"open"===e?W`<path class="fill" d="M5 7h14v6H5z" />
        <path d="M5 10h14M5 13h14" />
        <path d="M12 20v-4M9.8 18.2 12 16l2.2 2.2" />`:W`<path class="fill" d="M5 7h14v14H5z" />
        <path d="M5 10h14M5 13h14M5 16h14M5 19h14" />`}
</svg>`;class Ye extends de{constructor(){super(...arguments),this.preview=!1,this._written={},this._openSetting=null,this._inhibitIndex=Ye.INHIBIT_DEFAULT_INDEX,this._coversExpanded=!1,this._day=0,this._schedulesOpen=!1,this._dayOpen=!1,this._dayActive=0,this._heatPumpsOpen=!1}connectedCallback(){super.connectedCallback(),this._scheduleMidnightRefresh()}disconnectedCallback(){super.disconnectedCallback(),clearTimeout(this._midnightTimer),clearTimeout(this._settingTimeout)}_scheduleMidnightRefresh(){clearTimeout(this._midnightTimer);const e=new Date,t=new Date(e);t.setHours(24,0,1,0),this._midnightTimer=setTimeout(()=>{this._day++,this._scheduleMidnightRefresh()},t.getTime()-e.getTime())}static getStubConfig(){return{name:"Thermostat"}}static getConfigElement(){return document.createElement("homeshift-card-editor")}setConfig(e){if(!e)throw new Error("Missing configuration");this._written=e;const t={name:e.name??"Thermostat"};for(const i of ve)t[i.key]=e[i.key]??i.default;t.show_schedules=!1!==e.show_schedules,t.schedule_entities=Array.isArray(e.schedule_entities)?e.schedule_entities:[],this._config=t}_detectEntities(){if(!this._config||!this.hass)return!1;const e=function(e){const t={},i=Object.values(e?.entities??{});for(const e of ve){const s=ye(e.default);if(!s)continue;const o=i.find(e=>"homeshift"===e.platform&&e.translation_key===s);o&&(t[e.key]=o.entity_id)}return t}(this.hass),t={...this._config};let i=!1;for(const s of ve){const o=this._written[s.key]??e[s.key]??s.default;t[s.key]!==o&&(t[s.key]=o,i=!0)}return i&&(this._config=t),i}getCardSize(){return 4}shouldUpdate(e){if(e.has("hass")&&(this._refreshSchedules(),this._detectEntities()))return!0;if(e.has("_config")||e.has("preview"))return!0;if(e.has("_day")||e.has("_openSetting")||e.has("_inhibitIndex")||e.has("_coversExpanded")||e.has("_coverPending")||e.has("_schedules")||e.has("_schedulesOpen")||e.has("_dayOpen")||e.has("_heatPumpsOpen")||e.has("_dayActive"))return!0;if(e.has("hass")){const t=e.get("hass");if(!t)return!0;if(this._schedulesOpen)return!0;return ve.map(e=>this._config?.[e.key]).filter(Boolean).some(e=>t.states[e]!==this.hass.states[e])}return!1}_presetClass(e,t){const i=e=>e.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"").replace(/[^a-z0-9]+/g,"-");if(["off","heating","cooling","ventilation"].includes(i(e)))return i(e);return{eteint:"off",arret:"off",off:"off",chauffage:"heating",heat:"heating",heating:"heating",climatisation:"cooling",clim:"cooling",cool:"cooling",cooling:"cooling",ventilation:"ventilation",ventilateur:"ventilation",fan:"ventilation"}[i(t)]??i(e)}getEntityState(e){if(e)return this.hass?.states?.[e]}getCoversLeftOpen(){const e=this.getEntityState(this._config?.covers_left_open_entity)?.attributes?.covers;return Array.isArray(e)?e.map(e=>this.hass?.states?.[e]?.attributes?.friendly_name??e):[]}_friendlyName(e){return this.hass?.states?.[e]?.attributes?.friendly_name??e}getCoverInhibitions(){const e=this.getEntityState(this._config?.covers_inhibited_entity)?.attributes??{},t=Array.isArray(e.managed_covers)?e.managed_covers:[],i=new Map,s=Date.now();for(const[t,o]of Object.entries(e.covers??{}))"string"==typeof o&&new Date(o).getTime()<=s||i.set(t,"string"==typeof o?o:null);return{managed:t,inhibited:i}}getHeatPumps(){const e=this.getEntityState(this._config?.auto_start_stop_entity)?.attributes?.climates;return Array.isArray(e)?e:[]}async _toggleHeatPump(e){try{await this.hass.callService("switch","toggle",{entity_id:e.switch})}catch(e){this.dispatchEvent(new CustomEvent("hass-notification",{detail:{message:ge(this.hass,"card.heat_pump_failed",{error:e?.message??String(e)})},bubbles:!0,composed:!0}))}}_heatPumpsSummary(e){const t=[[ge(this.hass,"card.heat_pump_comfort"),e=>e.driven&&!!e.comfort],[ge(this.hass,"card.heat_pump_auto"),e=>e.driven&&!e.comfort],[ge(this.hass,"card.heat_pump_not_driven_short"),e=>!e.driven]],i=t.map(([t,i])=>[t,e.filter(i).length]).filter(([,e])=>e>0);return 1===e.length?i[0]?.[0]??"":i.map(([e,t])=>`${t} ${e}`).join(" · ")}_renderHeatPumps(e,t){const i=this._heatPumpsOpen,s=e.some(e=>e.manual);return V`<div class="heat-pumps ${i?"open":""}">
      <button
        type="button"
        class="heat-pumps-head"
        aria-expanded=${i?"true":"false"}
        aria-controls="heat-pump-list"
        @click=${()=>this._heatPumpsOpen=!i}
      >
        <ha-icon icon="mdi:hvac"></ha-icon>
        <span class="heat-pumps-title">${ge(this.hass,"card.heat_pumps")}</span>
        <span class="heat-pumps-summary">${this._heatPumpsSummary(e)}</span>
        ${s?V`<ha-icon
              class="manual"
              icon="mdi:hand-back-left"
              title=${ge(this.hass,"card.heat_pump_manual")}
              aria-label=${ge(this.hass,"card.heat_pump_manual")}
              role="img"
            ></ha-icon>`:K}
        <ha-icon class="chevron" icon="mdi:chevron-down"></ha-icon>
      </button>
      ${i?V`<div id="heat-pump-list" class="heat-pump-list">
            ${e.map(e=>{const i=e.driven?e.comfort?"comfort":"auto":"idle";let s;if(e.driven){const t="below"===e.comfort_when,i=e.comfort?t?"card.heat_pump_runs_up_to":"card.heat_pump_runs_from":t?"card.heat_pump_stops_above":"card.heat_pump_stops_below";s=ge(this.hass,i,{setpoint:String(e.setpoint??"—"),threshold:String(e.threshold??"—")})}else s=ge(this.hass,t?"card.heat_pump_thermostat_off":"card.heat_pump_not_driven");const o=ge(this.hass,{idle:"card.heat_pump_idle",comfort:"card.heat_pump_comfort",auto:"card.heat_pump_auto"}[i]);return V`<button
          type="button"
          class="heat-pump ${i}"
          aria-label="${e.name} — ${o}. ${s}"
          ?disabled=${!e.driven||null===e.auto_start_stop}
          @click=${()=>this._toggleHeatPump(e)}
        >
          <span class="heat-pump-icon">
            <ha-icon icon=${"auto"===i?"mdi:leaf":"mdi:hvac"}></ha-icon>
          </span>
          <span class="heat-pump-text">
            <span class="heat-pump-name">${e.name}</span>
            <span class="heat-pump-status"
              >${e.manual?V`<span class="heat-pump-manual"
                      >${ge(this.hass,"card.heat_pump_manual")}</span
                    >
                    · `:K}${s}</span
            >
          </span>
          <span class="heat-pump-tag">
            ${"idle"===i?K:V`<ha-icon icon=${"auto"===i?"mdi:leaf":"mdi:fire"}></ha-icon>`}
            ${o}
          </span>
        </button>`})}
          </div>`:K}
    </div>`}async _callInhibitService(e,t){this._armSettingTimeout();try{await this.hass.callService("homeshift",e,t)}catch(e){this.dispatchEvent(new CustomEvent("hass-notification",{detail:{message:ge(this.hass,"card.inhibit_failed",{error:e?.message??String(e)})},bubbles:!0,composed:!0}))}}_inhibitCover(e){const t=Ye.INHIBIT_PRESETS[this._inhibitIndex];this._callInhibitService("inhibit_covers",{entity_id:[e],...t?{duration:{minutes:t}}:{}})}_resumeCovers(e){this._callInhibitService("resume_covers",e?{entity_id:e}:{})}_stepInhibit(e){const t=Ye.INHIBIT_PRESETS.length-1;this._inhibitIndex=Math.min(t,Math.max(0,this._inhibitIndex+e)),this._armSettingTimeout()}_inhibitLabel(e){return e?e<1440?we(e):`${e/1440} ${ge(this.hass,"card.days_short")}`:ge(this.hass,"card.inhibit_forever")}_inhibitEnd(e){return e?ge(this.hass,"card.inhibited_until",{time:this._formatAbsoluteTime(e)}):ge(this.hass,"card.inhibited_forever")}_renderCoverInhibition({managed:e,inhibited:t}){const i="covers"===this._openSetting,s=Ye.INHIBIT_PRESETS,o=s[this._inhibitIndex],n=ge(this.hass,"card.inhibit_label"),a=o?ge(this.hass,"card.inhibit_effect",{duration:this._inhibitLabel(o),time:this._formatAbsoluteTime(new Date(Date.now()+6e4*o).toISOString())}):ge(this.hass,"card.inhibit_effect_forever");return V`<div class="setting ${i?"open":""}">
      <button
        class="setting-head"
        aria-expanded=${i?"true":"false"}
        @click=${()=>this._toggleSetting("covers")}
      >
        <ha-icon icon="mdi:window-shutter-cog"></ha-icon>
        <span class="setting-label">${n}</span>
        <span class="setting-value ${t.size?"set":""}"
          >${t.size?ge(this.hass,"card.inhibited_count",{count:String(t.size)}):ge(this.hass,"card.inhibit_none")}</span
        >
        <ha-icon class="chevron" icon="mdi:chevron-down"></ha-icon>
      </button>
      ${i?V`<div class="setting-body">
            <div class="stepper">
              <button
                aria-label=${ge(this.hass,"card.decrease",{setting:n})}
                ?disabled=${this._inhibitIndex<=0}
                @click=${()=>this._stepInhibit(-1)}
              >
                −
              </button>
              <span class="stepper-value" aria-live="polite"
                >${this._inhibitLabel(o)}</span
              >
              <button
                aria-label=${ge(this.hass,"card.increase",{setting:n})}
                ?disabled=${this._inhibitIndex>=s.length-1}
                @click=${()=>this._stepInhibit(1)}
              >
                +
              </button>
            </div>
            <p class="setting-effect">${a}</p>
            <ul class="cover-list">
              ${e.map(e=>{const i=t.has(e),s=this._friendlyName(e),o=ge(this.hass,i?"card.resume":"card.pause");return V`<li class="cover-item ${i?"paused":""}">
                  <span class="cover-name">
                    ${s}
                    <span class="cover-status"
                      >${i?this._inhibitEnd(t.get(e)??null):ge(this.hass,"card.inhibit_none")}</span
                    >
                  </span>
                  <button
                    type="button"
                    class="cover-toggle"
                    aria-label="${o} — ${s}"
                    @click=${()=>i?this._resumeCovers([e]):this._inhibitCover(e)}
                  >
                    <ha-icon icon=${i?"mdi:play":"mdi:pause"}></ha-icon>
                    ${o}
                  </button>
                </li>`})}
            </ul>
            ${t.size>1?V`<button
                  type="button"
                  class="resume-all"
                  @click=${()=>this._resumeCovers()}
                >
                  ${ge(this.hass,"card.resume_all")}
                </button>`:K}
          </div>`:K}
    </div>`}_refreshSchedules(){if(!this._config?.show_schedules||this.preview||!this.hass?.callWS)return;const e=Object.values(this.hass.states??{}).filter(e=>e.entity_id.startsWith("switch.schedule")).map(e=>`${e.entity_id}:${e.last_updated}`).join("|");e!==this._schedulesKey&&(this._schedulesKey=e,this.hass.callWS({type:"scheduler"}).then(e=>{this._schedules=Array.isArray(e)?e:void 0}).catch(()=>{this._schedules=void 0}))}_hasDaySchedules(e){return(this._schedules??[]).some(t=>t.tags?.some(t=>e.includes(t)))}_toggleSchedules(e){this._schedulesOpen=e,this.updateComplete.then(()=>this.shadowRoot?.querySelector(e?".schedules-close":".schedules-open")?.focus())}_renderSchedules(e,t){const i=ge(this.hass,"schedule.title"),s=t=>V`<button
      type="button"
      class="schedules-bar ${t?"schedules-close":"schedules-open"}"
      aria-expanded=${t?"true":"false"}
      aria-controls="schedules-panel"
      @click=${()=>this._toggleSchedules(!t)}
    >
      <ha-icon icon="mdi:calendar-clock"></ha-icon>
      <span class="schedules-title">${i}</span>
      <span class="schedules-mode">${e}</span>
      <ha-icon
        class="chevron"
        icon=${t?"mdi:chevron-down":"mdi:chevron-up"}
      ></ha-icon>
    </button>`;return V`${s(!1)}
      ${this._schedulesOpen?V`<div
            id="schedules-panel"
            class="schedules-panel"
            role="region"
            aria-label=${i}
            @keydown=${e=>{"Escape"===e.key&&(e.stopPropagation(),this._toggleSchedules(!1))}}
          >
            ${s(!0)}
            <div class="schedules-body">
              <homeshift-schedule-panel
                .hass=${this.hass}
                .schedules=${this._schedules??[]}
                .modes=${t}
                .activeMode=${e}
                .entities=${this._config.schedule_entities??[]}
              ></homeshift-schedule-panel>
            </div>
          </div>`:K}`}_pickDay(e,t){this._closeDayList(),this.hass.callService("select","select_option",{entity_id:e,option:t})}_openDayList(e,t){this._dayActive=Math.max(0,e.findIndex(([,e])=>e===t)),this._dayOpen=!0}_closeDayList(){this._dayOpen=!1}_onDayKeydown(e,t,i,s){if("ArrowDown"===e.key||"ArrowUp"===e.key){if(e.preventDefault(),!this._dayOpen)return void this._openDayList(i,s);const t="ArrowDown"===e.key?1:i.length-1;this._dayActive=(this._dayActive+t)%i.length}else"Enter"===e.key||" "===e.key?(e.preventDefault(),this._dayOpen?this._pickDay(t,i[this._dayActive][1]):this._openDayList(i,s)):"Escape"===e.key&&this._dayOpen&&(e.stopPropagation(),this._closeDayList())}_renderDayMode(e,t){const i=ge(this.hass,"card.day_mode"),s=$e(e),o=t.find(([,t])=>t===e.state)?.[0],n=e=>e&&We[e]||"mdi:calendar-today";return V`<div
      class="tile day-mode"
      @focusout=${e=>{const t=e.relatedTarget;t&&e.currentTarget.contains(t)||this._closeDayList()}}
    >
      <button
        type="button"
        class="day-mode-button"
        role="combobox"
        aria-label=${i}
        aria-haspopup="listbox"
        aria-controls="day-mode-list"
        aria-expanded=${this._dayOpen?"true":"false"}
        aria-activedescendant=${this._dayOpen?`day-mode-${this._dayActive}`:K}
        ?disabled=${!s}
        @click=${()=>this._dayOpen?this._closeDayList():this._openDayList(t,e.state)}
        @keydown=${i=>this._onDayKeydown(i,e.entity_id,t,e.state)}
      >
        <span class="tile-key">${i}</span>
        <span class="tile-value">
          <ha-icon class="day-icon" icon=${n(o)}></ha-icon>
          <span class="tile-text">${s?e.state:ge(this.hass,"card.unavailable")}</span>
          <ha-icon class="chevron" icon="mdi:chevron-down"></ha-icon>
        </span>
      </button>
      ${this._dayOpen?V`<ul id="day-mode-list" class="day-mode-list" role="listbox" aria-label=${i}>
            ${t.map(([t,i],s)=>{const o=i===e.state;return V`<li
                id="day-mode-${s}"
                class="day-mode-option ${s===this._dayActive?"active":""}"
                role="option"
                aria-selected=${o?"true":"false"}
                @mousedown=${e=>e.preventDefault()}
                @mousemove=${()=>this._dayActive=s}
                @click=${()=>this._pickDay(e.entity_id,i)}
              >
                <ha-icon icon=${n(t)}></ha-icon>
                <span class="option-text">${i}</span>
                <ha-icon class="check" icon="mdi:check"></ha-icon>
              </li>`})}
          </ul>`:K}
    </div>`}onThermostatSelect(e,t){this.hass.callService("select","select_option",{entity_id:e,option:t})}_coverCall(e){const t=this._config.cover_entity;if(t)return $e(this.getEntityState(t))?{domain:"cover",service:`${e}_cover`,entity_id:t}:void 0;const i="open"===e?this._config.open_covers_entity:this._config.close_covers_entity,s=this.getEntityState(i);return s&&"unavailable"!==s.state?{domain:"button",service:"press",entity_id:i}:void 0}async onCoverAction(e){const t=this._coverCall(e);if(t&&!this._coverPending){this._coverPending=e;try{await Promise.all([this.hass.callService(t.domain,t.service,{entity_id:t.entity_id}),new Promise(e=>setTimeout(e,Ye.COVER_FEEDBACK_MS))])}catch(t){this.dispatchEvent(new CustomEvent("hass-notification",{detail:{message:ge(this.hass,`card.cover_${e}_failed`,{error:t?.message??String(t)})},bubbles:!0,composed:!0}))}finally{this._coverPending=void 0}}}_renderCoverTime(e,t){if(!this._coverCall(e))return V`<span
        class="cover-time ${e}"
        title=${ge(this.hass,`card.cover_${e}_time`)}
      >
        ${Ke(e)}${t}
      </span>`;const i=this._coverPending===e,s=ge(this.hass,`card.cover_${e}_action`,{time:t});return V`<button
      type="button"
      class="cover-time ${e} actionable ${i?"pending":""}"
      title=${s}
      aria-label=${s}
      aria-busy=${i?"true":"false"}
      ?disabled=${void 0!==this._coverPending}
      @click=${()=>this.onCoverAction(e)}
    >
      ${Ke(e)}${i?ge(this.hass,"card.cover_sending"):t}
    </button>`}_formatAbsoluteTime(e){if(!e)return"";const t=new Date(e);if(isNaN(t.getTime()))return"";const i=new Date,s=new Date(i);s.setDate(s.getDate()+1);const o=Se(t,this.hass?.locale);return t.toDateString()===i.toDateString()?`${ge(this.hass,"card.today")} ${o}`:t.toDateString()===s.toDateString()?`${ge(this.hass,"card.tomorrow")} ${o}`:`${function(e,t){const{locale:i}=ke(t);return e.toLocaleDateString(i,{month:"short",day:"numeric"})}(t,this.hass?.locale)} ${o}`}_settingLabel(e){return void 0===e?ge(this.hass,"card.unavailable"):e?we(e):ge(this.hass,"card.duration_off")}_clockIn(e){return Se(new Date(Date.now()+6e4*e),this.hass?.locale)}_clockAt(e,t=0){return Se(new Date(new Date(e).getTime()+6e4*t),this.hass?.locale)}_toggleSetting(e){this._openSetting=this._openSetting===e?null:e,this._armSettingTimeout()}_armSettingTimeout(){if(clearTimeout(this._settingTimeout),!this._openSetting)return;const e="covers"===this._openSetting?2e4:6e3;this._settingTimeout=setTimeout(()=>{this._openSetting=null},e)}_stepSetting(e,t,i,s){const o="override"===e?this._config.override_duration_entity:this._config.early_switch_entity;if(!o)return;const n=s>0?t.find(e=>e>i):[...t].reverse().find(e=>e<i);void 0!==n&&(this._armSettingTimeout(),this.hass.callService("number","set_value",{entity_id:o,value:n}))}_renderSetting(e,t,i,s,o,n){const a=void 0!==n&&this._openSetting===e;return V`<div class="setting ${a?"open":""}">
      <button
        class="setting-head"
        aria-expanded=${a?"true":"false"}
        ?disabled=${void 0===n}
        @click=${()=>this._toggleSetting(e)}
      >
        <ha-icon icon="${t}"></ha-icon>
        <span class="setting-label">${i}</span>
        <span class="setting-value ${n?"set":""}"
          >${this._settingLabel(n)}</span
        >
        <ha-icon class="chevron" icon="mdi:chevron-down"></ha-icon>
      </button>
      ${a?V`<div class="setting-body">
            <div class="stepper">
              <button
                aria-label=${ge(this.hass,"card.decrease",{setting:i})}
                ?disabled=${n<=o[0]}
                @click=${()=>this._stepSetting(e,o,n,-1)}
              >
                −
              </button>
              <span class="stepper-value" aria-live="polite"
                >${this._settingLabel(n)}</span
              >
              <button
                aria-label=${ge(this.hass,"card.increase",{setting:i})}
                ?disabled=${n>=o[o.length-1]}
                @click=${()=>this._stepSetting(e,o,n,1)}
              >
                +
              </button>
            </div>
            <p class="setting-effect">${s}</p>
          </div>`:K}
    </div>`}_minutes(e){if(!e)return null;const t=this.getEntityState(e);return t?function(e){if(!$e(e))return;const t=Number(e.state);return Number.isFinite(t)?t:void 0}(t):this.preview?0:null}_entries(e){const t=e.attributes?.option_map??{};return Object.keys(t).length>0?Object.entries(t):(e.attributes?.options??[]).map(e=>[e,e])}_activeThermo(e){if(!$e(e))return;const t=e.attributes?.current_key;return this._entries(e).find(([i,s])=>t?i===t:s===e.state)}_renderMain(e,t,i,s,o,n,a){const r=this._entries(t),c=this._entries(e),d=this.getEntityState(this._config.next_mode_entity),l=this.getEntityState(this._config.next_mode_at_entity),h=this._minutes(this._config.early_switch_entity),p=this._minutes(this._config.override_duration_entity),u=$e(d),m=u?d.state:"",f=$e(l)?this._formatAbsoluteTime(l.state):"",_=""!==f,g=p?ge(this.hass,"card.override_effect",{duration:this._settingLabel(p),time:this._clockIn(p)}):ge(this.hass,"card.override_none"),v=_?h?ge(this.hass,"card.early_effect",{mode:m,time:this._clockAt(l.state),scheduled:this._clockAt(l.state,h)}):ge(this.hass,"card.early_none",{mode:m,time:this._clockAt(l.state)}):ge(this.hass,"card.early_no_event"),b=$e(n),y=$e(a),x=ge(this.hass,"card.covers_left_open",{covers:s.join(", ")}),$=s.length>3,w=$?ge(this.hass,"card.covers_left_open_count",{count:String(s.length)}):x,k=[...o.inhibited.keys()].map(e=>this._friendlyName(e)),S=k.length>2?ge(this.hass,"card.covers_paused_count",{count:String(k.length)}):ge(this.hass,"card.covers_paused",{covers:k.join(", ")}),E=[...o.inhibited.entries()].map(([e,t])=>`${this._friendlyName(e)} — ${this._inhibitEnd(t)}`).join("\n"),A=this._activeThermo(e),C=$e(e),T=this.getHeatPumps();return V`
      <div class="rows">
        <div
          class="presets"
          role="group"
          aria-label=${ge(this.hass,"card.thermostat_mode")}
        >
          ${c.map(([t,i])=>{const s=A?.[0]===t,o=this._presetClass(t,i),n=qe[o]??Ve;return V`<button
              class="preset preset--${o} ${s?"on":""}"
              style="--c: ${n.rgb}"
              aria-pressed=${s?"true":"false"}
              ?disabled=${!C}
              @click=${()=>this.onThermostatSelect(e.entity_id,i)}
            >
              <ha-icon icon=${n.icon}></ha-icon>
              <span class="preset-label"
                >${ge(this.hass,`thermostat.${t}`,void 0,i)}</span
              >
            </button>`})}
        </div>

        <div class="tiles">
          ${this._renderDayMode(t,r)}
          ${u||_?V`<div class="tile next-row">
                <span class="tile-key">${ge(this.hass,"card.next")}</span>
                <span class="tile-value">
                  <span class="tile-text">${m}</span>
                  <span class="next-at">${f}</span>
                </span>
              </div>`:K}
        </div>

        ${null!==p?this._renderSetting("override","mdi:hand-back-left",ge(this.hass,"card.override_label"),g,Ye.OVERRIDE_PRESETS,p):K}
        ${null!==h?this._renderSetting("early","mdi:clock-fast",ge(this.hass,"card.early_label"),v,Ye.EARLY_SWITCH_PRESETS,h):K}

        ${b||y?V`<div class="row covers-row">
              <span class="row-key">${ge(this.hass,"card.covers")}</span>
              <span class="cover-times">
                ${b?this._renderCoverTime("open",n):K}
                ${y?this._renderCoverTime("close",a):K}
              </span>
            </div>`:K}

        ${o.managed.length>0?this._renderCoverInhibition(o):K}

        ${T.length>0?this._renderHeatPumps(T,"off"===A?.[0]):K}

        ${i||s.length>0||k.length>0?V`<div class="alerts">
              ${i?V`<span class="chip chip--heat">
                    <ha-icon icon="mdi:white-balance-sunny"></ha-icon>
                    ${ge(this.hass,"card.heat_protection_active")}
                  </span>`:K}
              ${s.length>0&&!$?V`<span class="chip chip--covers">
                    <ha-icon icon="mdi:window-shutter-alert"></ha-icon>
                    ${w}
                  </span>`:K}
              ${$?V`<button
                    type="button"
                    class="chip chip--covers"
                    title=${x}
                    aria-label=${x}
                    aria-expanded=${this._coversExpanded?"true":"false"}
                    @click=${()=>this._coversExpanded=!this._coversExpanded}
                  >
                    <ha-icon icon="mdi:window-shutter-alert"></ha-icon>
                    ${w}
                  </button>`:K}
              ${k.length>0?V`<button
                    type="button"
                    class="chip chip--paused"
                    title=${E}
                    @click=${()=>{this._openSetting="covers",this._armSettingTimeout()}}
                  >
                    <ha-icon icon="mdi:window-shutter-cog"></ha-icon>
                    ${S}
                  </button>`:K}
            </div>
            ${$&&this._coversExpanded?V`<p class="covers-detail">${x}</p>`:K}`:K}
      </div>
    `}render(){if(!this.hass||!this._config)return K;const e=this.getEntityState(this._config.day_mode_entity),t=this.getEntityState(this._config.thermostat_mode_entity);if(!this.preview){const i=[[this._config.day_mode_entity,e],[this._config.thermostat_mode_entity,t]].filter(([,e])=>!e).map(([e])=>e||"?");if(i.length>0)return V`
          <ha-card>
            ${i.map(e=>V`<div class="error">
                  ${ge(this.hass,"card.entity_not_found",{entity:e})}
                </div>`)}
          </ha-card>
        `}const i=e??{entity_id:this._config.day_mode_entity,state:ge(this.hass,"preview.work"),attributes:{option_map:Object.fromEntries(["home","work","remote","away"].map(e=>[e,ge(this.hass,`preview.${e}`)]))}},s=t??{entity_id:this._config.thermostat_mode_entity,state:ge(this.hass,"thermostat.heating"),attributes:{option_map:Object.fromEntries(["off","heating","cooling","ventilation"].map(e=>[e,ge(this.hass,`thermostat.${e}`)])),current_key:"heating"}},o="on"===this.getEntityState(this._config.heat_protection_entity)?.state,n=this.getEntityState(this._config.cover_open_time_entity)?.state,a=this.getEntityState(this._config.cover_close_time_entity)?.state,r=i.attributes?.options??[],c=$e(i)&&this._hasDaySchedules(r),d=this._activeThermo(s),l=d?this._presetClass(d[0],d[1]):"none",h=qe[l]??Ve,p=d?ge(this.hass,`thermostat.${d[0]}`,void 0,d[1]):ge(this.hass,"card.unavailable"),u=["heating","cooling","ventilation"].includes(l);return V`
      <ha-card data-mode=${l} style="--m: ${h.rgb}">
        <div class="glow" aria-hidden="true"></div>
        ${u?V`<div class="particles" aria-hidden="true">
              ${Fe.map(([e,t,i,s,o])=>V`<span
                    class="particle"
                    style="left: ${e}%; --y: ${o}%; --d: ${t}s; --dl: ${i}s; --dx: ${s}px"
                  ></span>`)}
            </div>`:K}
        <div class="container" ?inert=${c&&this._schedulesOpen}>
          <div class="header">
            <span class="badge"><ha-icon icon=${h.icon}></ha-icon></span>
            <span class="heading">
              <span class="name">${this._config.name}</span>
              <span class="status">
                <span class="dot"></span>${p} · ${$e(i)?i.state:ge(this.hass,"card.unavailable")}
              </span>
            </span>
          </div>
          ${this._renderCalendarError(i)}
          ${this._renderMain(s,i,o,this.getCoversLeftOpen(),this.getCoverInhibitions(),n,a)}
        </div>
        ${c?this._renderSchedules(i.state,r):K}
      </ha-card>
    `}_renderCalendarError(e){const t=e?.attributes?.calendar_error;if(!t)return K;const i=new Date(t.since),s=Number.isNaN(i.getTime())?"":Se(i,this.hass?.locale);return V`<div class="calendar-error" role="alert">
      <ha-icon icon="mdi:calendar-remove"></ha-icon>
      <span>
        <strong>${ge(this.hass,"card.calendar_unreadable")}</strong>
        <span>${ge(this.hass,"card.calendar_unreadable_detail",{time:s,mode:e?.state??""})}</span>
      </span>
    </div>`}}Ye.COVER_FEEDBACK_MS=600,Ye.OVERRIDE_PRESETS=[0,15,30,60,120,240,480,720],Ye.EARLY_SWITCH_PRESETS=[0,15,30,45,60,90,120,180,240],Ye.INHIBIT_PRESETS=[240,1440,2880,4320,10080,0],Ye.INHIBIT_DEFAULT_INDEX=1,Ye.styles=a`
    .calendar-error {
      display: flex;
      gap: 10px;
      align-items: flex-start;
      margin: 0 0 10px;
      padding: 9px 11px;
      border-radius: 10px;
      border: 1px solid rgba(255, 170, 40, 0.45);
      background: rgba(255, 170, 40, 0.13);
      color: #ffd98f;
      font-size: 13px;
      line-height: 1.4;
    }
    .calendar-error ha-icon {
      --mdc-icon-size: 18px;
      flex: none;
      margin-top: 1px;
    }
    .calendar-error strong {
      display: block;
      font-weight: 500;
    }
    .calendar-error span span {
      font-size: 12px;
      color: #e9c486;
    }
    /* Dark glass card: its colour (--m, "r, g, b") follows the thermostat mode. */
    ha-card {
      --m: 148, 163, 184;
      --hs-text: #e6f2f5;
      --hs-text-2: rgba(220, 235, 240, 0.62);
      --hs-surface: rgba(255, 255, 255, 0.06);
      --hs-ring: rgba(255, 255, 255, 0.07);
      /* What the panel and the scheduler card read from the theme follows
         the dark card instead. */
      --primary-text-color: var(--hs-text);
      --secondary-text-color: var(--hs-text-2);
      --divider-color: rgba(255, 255, 255, 0.08);
      --card-background-color: #121a24;
      --ha-card-background: #121a24;
      position: relative;
      /* Clips the glow, the particles and the schedules panel. */
      overflow: hidden;
      padding: 0;
      border-radius: var(--ha-card-border-radius, 20px);
      border: 1px solid rgba(var(--m), 0.25);
      background: linear-gradient(
        160deg,
        rgba(20, 28, 38, 0.96),
        rgba(10, 15, 22, 0.98)
      );
      box-shadow:
        0 8px 26px rgba(0, 0, 0, 0.35),
        0 0 22px -6px rgba(var(--m), 0.45),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
      color: var(--hs-text);
      transition:
        border-color 0.6s,
        box-shadow 0.6s;
    }

    button {
      font-family: inherit;
    }

    button:focus-visible {
      outline: 2px solid #fff;
      outline-offset: 2px;
    }

    /* Ambience: a glow where the heat rises, the cold falls or the air blows. */
    .glow {
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: radial-gradient(
        110% 70% at 50% 50%,
        rgba(var(--m), 0.22),
        transparent 75%
      );
      animation: breathe 5s ease-in-out infinite;
    }

    ha-card[data-mode="heating"] .glow {
      background: radial-gradient(
        130% 75% at 50% 110%,
        rgba(255, 110, 30, 0.45),
        rgba(255, 80, 20, 0.12) 55%,
        transparent 78%
      );
    }

    ha-card[data-mode="cooling"] .glow {
      background: radial-gradient(
        120% 70% at 50% -10%,
        rgba(80, 190, 255, 0.4),
        rgba(60, 140, 255, 0.1) 55%,
        transparent 75%
      );
    }

    ha-card[data-mode="ventilation"] .glow {
      background: radial-gradient(
        120% 80% at 0% 50%,
        rgba(45, 212, 160, 0.35),
        rgba(45, 212, 160, 0.09) 55%,
        transparent 78%
      );
    }

    ha-card[data-mode="off"] .glow {
      background: radial-gradient(
        110% 70% at 50% 50%,
        rgba(148, 163, 184, 0.18),
        rgba(71, 85, 105, 0.1) 60%,
        transparent 80%
      );
      animation-duration: 9s;
    }

    .particles {
      position: absolute;
      inset: 0;
      overflow: hidden;
      pointer-events: none;
    }

    .particle {
      position: absolute;
      opacity: 0;
    }

    ha-card[data-mode="heating"] .particle {
      bottom: 0;
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: radial-gradient(circle, #ffe0a0, #ff7a2a 60%, transparent 70%);
      box-shadow: 0 0 6px 1px rgba(255, 120, 40, 0.7);
      animation: rise var(--d) ease-in var(--dl) infinite;
    }

    ha-card[data-mode="cooling"] .particle {
      top: 0;
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: radial-gradient(circle, #fff, #bfe9ff 55%, transparent 72%);
      animation: fall calc(var(--d) * 1.5) linear var(--dl) infinite;
    }

    ha-card[data-mode="ventilation"] .particle {
      top: var(--y);
      width: 34px;
      height: 2px;
      border-radius: 2px;
      background: linear-gradient(
        90deg,
        transparent,
        rgba(170, 255, 225, 0.75),
        transparent
      );
      animation: breeze var(--d) linear var(--dl) infinite;
    }

    @keyframes breathe {
      50% {
        opacity: 0.6;
      }
    }

    @keyframes rise {
      from {
        transform: translate(0, 0) scale(1);
        opacity: 0.9;
      }
      to {
        transform: translate(var(--dx), -260px) scale(0.3);
        opacity: 0;
      }
    }

    @keyframes fall {
      from {
        transform: translate(0, -10px);
        opacity: 0.9;
      }
      to {
        transform: translate(var(--dx), 320px);
        opacity: 0;
      }
    }

    @keyframes breeze {
      from {
        left: -40px;
        opacity: 0;
      }
      20% {
        opacity: 0.8;
      }
      to {
        left: 100%;
        opacity: 0;
      }
    }

    @keyframes spin {
      to {
        transform: rotate(360deg);
      }
    }

    .container {
      position: relative;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 14px;
    }

    .rows {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .header {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .badge {
      flex: none;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 38px;
      height: 38px;
      border-radius: 12px;
      background: rgba(var(--m), 0.16);
      box-shadow: inset 0 0 0 1px rgba(var(--m), 0.25);
      color: rgb(var(--m));
      --mdc-icon-size: 21px;
      transition:
        background 0.4s,
        color 0.4s;
    }

    ha-card[data-mode="ventilation"] .badge ha-icon {
      animation: spin 1.6s linear infinite;
    }

    .heading {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 15px;
      font-weight: 600;
      line-height: 1.2;
    }

    .status {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-top: 2px;
      font-size: 12px;
      color: var(--hs-text-2);
    }

    .dot {
      flex: none;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: rgb(var(--m));
      box-shadow: 0 0 6px rgb(var(--m));
    }

    /* Thermostat modes: one segmented control, one colour (--c) per mode. */
    .presets {
      display: flex;
      gap: 4px;
      padding: 3px;
      border-radius: 14px;
      background: rgba(0, 0, 0, 0.28);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.06);
    }

    .preset {
      flex: 1 1 0;
      min-width: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 2px;
      height: 48px;
      padding: 0 2px;
      border: 0;
      border-radius: 11px;
      background: transparent;
      color: var(--hs-text-2);
      font-size: 11.5px;
      font-weight: 500;
      cursor: pointer;
      --mdc-icon-size: 19px;
      transition:
        background 0.3s,
        color 0.3s,
        box-shadow 0.3s;
    }

    .preset-label {
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .preset:hover:not(:disabled):not(.on) {
      background: rgba(255, 255, 255, 0.06);
      color: rgb(var(--c));
    }

    .preset.on {
      color: #fff;
      background: linear-gradient(
        180deg,
        rgba(var(--c), 0.95),
        rgba(var(--c), 0.7)
      );
      box-shadow: 0 3px 12px -2px rgba(var(--c), 0.6);
    }

    .preset:disabled {
      cursor: default;
      opacity: 0.5;
    }

    /* Day mode and next mode, side by side. */
    .tiles {
      position: relative;
      /* The day mode list opens over the rows below. */
      z-index: 2;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
      gap: 6px;
    }

    .tile {
      position: relative;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 3px;
      padding: 8px 10px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.05);
      box-shadow: inset 0 0 0 1px var(--hs-ring);
    }

    .tile.day-mode {
      padding: 0;
      background: none;
      box-shadow: none;
    }

    .day-mode-button {
      all: unset;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      gap: 3px;
      width: 100%;
      padding: 8px 10px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.05);
      box-shadow: inset 0 0 0 1px var(--hs-ring);
      cursor: pointer;
      transition:
        background 0.2s,
        box-shadow 0.2s;
    }

    .day-mode-button:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.09);
    }

    .day-mode-button[aria-expanded="true"] {
      background: rgba(var(--m), 0.12);
      box-shadow: inset 0 0 0 1px rgba(var(--m), 0.5);
    }

    .day-mode-button:disabled {
      cursor: default;
      opacity: 0.6;
    }

    .tile-key,
    .row-key {
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--hs-text-2);
    }

    .tile-value {
      display: flex;
      align-items: center;
      gap: 6px;
      min-width: 0;
      font-size: 13px;
      font-weight: 500;
    }

    .tile-text {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .day-icon {
      flex: none;
      --mdc-icon-size: 16px;
      color: rgb(var(--m));
    }

    .tile-value .chevron {
      flex: none;
      --mdc-icon-size: 18px;
      color: var(--hs-text-2);
      transition: transform 0.2s;
    }

    .day-mode-button[aria-expanded="true"] .chevron {
      transform: rotate(180deg);
      color: rgb(var(--m));
    }

    .next-at {
      flex: none;
      font-size: 12px;
      font-weight: 400;
      color: var(--hs-text-2);
    }

    .day-mode-list {
      position: absolute;
      left: 0;
      right: 0;
      top: calc(100% + 6px);
      margin: 0;
      padding: 4px;
      list-style: none;
      border-radius: 12px;
      background: rgba(18, 26, 36, 0.98);
      box-shadow:
        inset 0 0 0 1px rgba(255, 255, 255, 0.08),
        0 12px 30px rgba(0, 0, 0, 0.5);
      animation: pop 0.15s ease-out;
    }

    .day-mode-option {
      display: flex;
      align-items: center;
      gap: 8px;
      height: 34px;
      padding: 0 10px;
      border-radius: 9px;
      font-size: 13px;
      cursor: pointer;
      --mdc-icon-size: 16px;
    }

    .day-mode-option ha-icon {
      flex: none;
      color: var(--hs-text-2);
    }

    .option-text {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .day-mode-option .check {
      visibility: hidden;
    }

    .day-mode-option.active {
      background: rgba(255, 255, 255, 0.07);
    }

    .day-mode-option[aria-selected="true"] {
      background: rgba(var(--m), 0.18);
    }

    .day-mode-option[aria-selected="true"].active {
      background: rgba(var(--m), 0.26);
    }

    .day-mode-option[aria-selected="true"] ha-icon {
      visibility: visible;
      color: rgb(var(--m));
    }

    @keyframes pop {
      from {
        opacity: 0;
        transform: translateY(-4px);
      }
    }

    /* Collapsed by default: the value is readable without opening anything. */
    .setting {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .setting-head {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      height: 36px;
      padding: 0 10px;
      border: 0;
      border-radius: 11px;
      background: var(--hs-surface);
      box-shadow: inset 0 0 0 1px var(--hs-ring);
      color: var(--hs-text);
      font-size: 12.5px;
      font-weight: 500;
      text-align: left;
      cursor: pointer;
    }

    .setting-head:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.09);
    }

    .setting-head:disabled {
      cursor: default;
    }

    .setting-head:disabled .chevron {
      visibility: hidden;
    }

    .setting-head ha-icon {
      flex-shrink: 0;
      --mdc-icon-size: 17px;
      color: var(--hs-text-2);
    }

    .setting-label {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .setting-value {
      color: var(--hs-text-2);
    }

    .setting-value.set {
      color: rgb(var(--m));
    }

    .setting .chevron {
      transition: transform 0.15s ease;
    }

    .setting.open .chevron {
      transform: rotate(180deg);
    }

    .setting-body {
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 10px;
      border-radius: 11px;
      background: rgba(0, 0, 0, 0.22);
      animation: fadeIn 0.15s ease;
    }

    .stepper {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 14px;
    }

    .stepper button {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 34px;
      height: 34px;
      border: 0;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.07);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
      color: var(--hs-text);
      font-size: 18px;
      line-height: 1;
      cursor: pointer;
    }

    .stepper button:active:not(:disabled) {
      transform: scale(0.9);
      background: rgba(var(--m), 0.3);
    }

    .stepper button:disabled {
      opacity: 0.35;
      cursor: default;
    }

    .stepper-value {
      min-width: 70px;
      text-align: center;
      font-size: 20px;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }

    .setting-effect {
      margin: 0;
      font-size: 12px;
      line-height: 1.4;
      text-align: center;
      color: var(--hs-text-2);
    }

    .row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }

    .covers-row {
      display: grid;
      grid-template-columns: auto 1fr;
    }

    .cover-times {
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: 1fr;
      gap: 6px;
    }

    .cover-time {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      height: 40px;
      padding: 0 8px;
      border: 0;
      border-radius: 11px;
      background: var(--hs-surface);
      box-shadow: inset 0 0 0 1px var(--hs-ring);
      color: var(--hs-text);
      font-size: 14px;
      font-weight: 500;
      font-variant-numeric: tabular-nums;
    }

    /* Roller shutter: amber when it opens, blue when it closes. */
    .cover-icon {
      flex: none;
      width: 24px;
      height: 24px;
      fill: none;
      stroke: currentColor;
      stroke-width: 1.6;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    .cover-time.open .cover-icon {
      color: #ffa63d;
    }

    .cover-time.close .cover-icon {
      color: #7ea2ff;
    }

    .cover-icon .solid {
      fill: currentColor;
      fill-opacity: 0.55;
    }

    .cover-icon .fill {
      fill: currentColor;
      fill-opacity: 0.3;
      stroke: none;
    }

    .cover-icon .rails {
      stroke-width: 1.2;
      stroke-opacity: 0.5;
    }

    .cover-time.actionable {
      cursor: pointer;
    }

    .cover-time.actionable:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.1);
    }

    .cover-time.actionable:disabled {
      cursor: progress;
    }

    .cover-time.pending {
      animation: cover-pending 0.8s ease-in-out infinite alternate;
    }

    @keyframes cover-pending {
      from {
        opacity: 1;
      }
      to {
        opacity: 0.5;
      }
    }

    .error {
      position: relative;
      padding: 14px;
      color: #ff8a80;
    }

    /* Climate auto start/stop: green when VTherm may stop it, the mode's
       colour while a comfort range keeps it running, grey when not driven. */
    .heat-pumps {
      display: flex;
      flex-direction: column;
      gap: 6px;
      border-radius: 11px;
      background: rgba(255, 255, 255, 0.035);
      box-shadow: inset 0 0 0 1px var(--hs-ring);
    }

    .heat-pumps-head {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      height: 36px;
      padding: 0 10px;
      border: 0;
      border-radius: 11px;
      background: var(--hs-surface);
      color: var(--hs-text);
      font-size: 12.5px;
      font-weight: 500;
      text-align: left;
      cursor: pointer;
    }

    .heat-pumps-head:hover {
      background: rgba(255, 255, 255, 0.09);
    }

    .heat-pumps-head ha-icon {
      flex-shrink: 0;
      --mdc-icon-size: 17px;
      color: var(--hs-text-2);
    }

    /* The summary is what changes, so it keeps its width; a long title is the
       part cut short. */
    .heat-pumps-title {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .heat-pumps-summary {
      flex: none;
      white-space: nowrap;
      color: var(--hs-text-2);
    }

    .heat-pumps-head ha-icon.manual {
      --mdc-icon-size: 15px;
      color: #ffc24d;
    }

    .heat-pumps-head .chevron {
      transition: transform 0.15s ease;
    }

    .heat-pumps.open .heat-pumps-head .chevron {
      transform: rotate(180deg);
    }

    .heat-pump-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding: 0 8px 8px;
      animation: fadeIn 0.15s ease;
    }

    .heat-pump {
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
      padding: 8px 10px;
      border: 0;
      border-radius: 11px;
      background: rgba(255, 255, 255, 0.05);
      box-shadow: inset 0 0 0 1px var(--hs-ring);
      color: var(--hs-text);
      text-align: left;
      cursor: pointer;
      transition: background 0.2s;
    }

    .heat-pump:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.09);
    }

    .heat-pump:disabled {
      cursor: default;
    }

    .heat-pump-icon {
      flex: none;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 30px;
      height: 30px;
      border-radius: 9px;
      --mdc-icon-size: 17px;
    }

    .heat-pump-text {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
    }

    .heat-pump-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 13px;
      font-weight: 500;
    }

    .heat-pump-status {
      margin-top: 1px;
      font-size: 11.5px;
      color: var(--hs-text-2);
    }

    .heat-pump-manual {
      color: #ffc24d;
    }

    .heat-pump-tag {
      flex: none;
      display: flex;
      align-items: center;
      gap: 5px;
      height: 22px;
      padding: 0 9px;
      border-radius: 11px;
      font-size: 11.5px;
      font-weight: 500;
      --mdc-icon-size: 13px;
    }

    .heat-pump.auto .heat-pump-icon,
    .heat-pump.auto .heat-pump-tag {
      background: rgba(62, 201, 122, 0.15);
      color: #7fe0aa;
    }

    .heat-pump.auto .heat-pump-tag {
      box-shadow: inset 0 0 0 1px rgba(62, 201, 122, 0.3);
    }

    .heat-pump.comfort .heat-pump-icon,
    .heat-pump.comfort .heat-pump-tag {
      background: rgba(var(--m), 0.16);
      color: rgb(var(--m));
    }

    .heat-pump.comfort .heat-pump-tag {
      box-shadow: inset 0 0 0 1px rgba(var(--m), 0.35);
    }

    .heat-pump.idle .heat-pump-icon,
    .heat-pump.idle .heat-pump-tag {
      background: var(--hs-surface);
      color: var(--hs-text-2);
    }

    /* Alerts only exist while something is wrong; nothing is shown otherwise. */
    .alerts {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      height: 28px;
      padding: 0 11px;
      border: 0;
      border-radius: 14px;
      font-size: 12px;
      font-weight: 500;
      animation: fadeIn 0.3s ease;
    }

    .chip ha-icon {
      --mdc-icon-size: 15px;
    }

    button.chip {
      cursor: pointer;
    }

    .covers-detail {
      margin: 0;
      font-size: 12px;
      line-height: 1.4;
      color: var(--hs-text);
    }

    .chip--heat {
      background: rgba(239, 83, 80, 0.18);
      box-shadow: inset 0 0 0 1px rgba(239, 83, 80, 0.3);
      color: #ffb4b2;
      animation:
        fadeIn 0.3s ease,
        heat-pulse 2.4s ease-in-out infinite;
    }

    @keyframes heat-pulse {
      50% {
        box-shadow:
          inset 0 0 0 1px rgba(239, 83, 80, 0.5),
          0 0 10px rgba(239, 83, 80, 0.4);
      }
    }

    /* A paused cover is a choice, not a fault: calm colour, no animation. */
    .chip--paused {
      background: var(--hs-surface);
      box-shadow: inset 0 0 0 1px var(--hs-ring);
      color: var(--hs-text);
    }

    .chip--paused ha-icon {
      color: var(--hs-text-2);
    }

    /* Pulses: a cover left up is something to act on tonight, not a steady
       status. */
    .chip--covers {
      background: rgba(255, 184, 64, 0.18);
      box-shadow: inset 0 0 0 1px rgba(255, 184, 64, 0.35);
      color: #ffc24d;
      animation:
        fadeIn 0.3s ease,
        covers-left-open-blink 1.2s ease-in-out infinite;
    }

    @keyframes covers-left-open-blink {
      50% {
        opacity: 0.55;
      }
    }

    .cover-list {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .cover-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 8px 10px;
      border-radius: 11px;
      background: rgba(255, 255, 255, 0.05);
      box-shadow: inset 0 0 0 1px var(--hs-ring);
      font-size: 13px;
      font-weight: 500;
    }

    .cover-name {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .cover-status {
      margin-top: 1px;
      font-size: 11.5px;
      font-weight: 400;
      color: var(--hs-text-2);
    }

    .cover-item.paused .cover-status {
      color: #ffc24d;
    }

    .cover-toggle,
    .resume-all {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      flex-shrink: 0;
      height: 30px;
      padding: 0 11px;
      border: 0;
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.07);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
      color: var(--hs-text);
      font-size: 12.5px;
      font-weight: 500;
      cursor: pointer;
    }

    .cover-toggle ha-icon {
      --mdc-icon-size: 15px;
    }

    .cover-toggle:hover,
    .resume-all:hover {
      background: rgba(255, 255, 255, 0.12);
    }

    .cover-item.paused .cover-toggle {
      background: rgba(255, 184, 64, 0.18);
      box-shadow: inset 0 0 0 1px rgba(255, 184, 64, 0.35);
      color: #ffc24d;
    }

    .resume-all {
      align-self: center;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(3px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    /* Schedules: a bar at the foot of the card, and the panel it slides up. */
    .schedules-bar {
      position: relative;
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      margin: 0;
      padding: 12px 14px;
      border: 0;
      border-top: 1px solid rgba(255, 255, 255, 0.07);
      background: transparent;
      color: var(--hs-text-2);
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      text-align: left;
      cursor: pointer;
    }

    .schedules-bar:hover {
      background: rgba(255, 255, 255, 0.04);
    }

    .schedules-bar:focus-visible {
      outline-offset: -2px;
    }

    .schedules-bar ha-icon {
      flex-shrink: 0;
      --mdc-icon-size: 17px;
    }

    .schedules-title {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .schedules-mode {
      font-size: 12.5px;
      color: var(--hs-text);
      text-transform: none;
      letter-spacing: normal;
    }

    /* Anchored to the foot of the card and as tall as its content: the top
       of the card stays in sight while the schedules are shorter than it;
       longer ones scroll inside the panel. */
    .schedules-panel {
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      max-height: calc(100% - 24px);
      z-index: 3;
      display: flex;
      flex-direction: column;
      border-top: 1px solid rgba(var(--m), 0.3);
      border-radius: 18px 18px 0 0;
      background: linear-gradient(
        180deg,
        rgba(18, 26, 36, 0.99),
        rgba(10, 15, 22, 0.99)
      );
      box-shadow: 0 -10px 30px rgba(0, 0, 0, 0.4);
      animation: schedules-slide-up 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
    }

    .schedules-panel .schedules-bar {
      border-top: 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.07);
    }

    .schedules-body {
      flex: 1 1 auto;
      min-height: 0;
      overflow-y: auto;
      overscroll-behavior: contain;
      padding: 12px 14px 14px;
    }

    @keyframes schedules-slide-up {
      from {
        transform: translateY(100%);
      }
      to {
        transform: translateY(0);
      }
    }

    /* The colours alone still tell the mode, the warning and the state. */
    @media (prefers-reduced-motion: reduce) {
      .glow,
      .badge ha-icon,
      .chip--heat,
      .chip--covers,
      .cover-time.pending,
      .schedules-panel,
      .day-mode-list {
        animation: none !important;
      }
      .particles {
        display: none;
      }
    }
  `,e([ue({attribute:!1})],Ye.prototype,"hass",void 0),e([ue({type:Boolean})],Ye.prototype,"preview",void 0),e([me()],Ye.prototype,"_config",void 0),e([me()],Ye.prototype,"_openSetting",void 0),e([me()],Ye.prototype,"_inhibitIndex",void 0),e([me()],Ye.prototype,"_coverPending",void 0),e([me()],Ye.prototype,"_coversExpanded",void 0),e([me()],Ye.prototype,"_day",void 0),e([me()],Ye.prototype,"_schedules",void 0),e([me()],Ye.prototype,"_schedulesOpen",void 0),e([me()],Ye.prototype,"_dayOpen",void 0),e([me()],Ye.prototype,"_dayActive",void 0),e([me()],Ye.prototype,"_heatPumpsOpen",void 0),customElements.get("homeshift-card")||customElements.define("homeshift-card",Ye),window.customCards=window.customCards||[],window.customCards.push({type:"homeshift-card",name:"HomeShift Card",description:"Card to manage day mode and thermostat mode via the HomeShift integration.",preview:!0});
